"""Bounded one-way UDP distribution. Dispatch counters are not acknowledgements."""
import asyncio
from collections import OrderedDict
from copy import deepcopy
import hashlib
import ipaddress
import json
import os
from pathlib import Path
from types import SimpleNamespace
import socket
import sqlite3
import struct
import time
import threading
from .protocol import read_header, PacketError
from .qso_model import completed_fields, enriched_completed, observed_identity, adif_text, QsoError
from .forwarding_config import PACKET_TYPES


def encode_logged_adif(packet, fields):
    """WSJT-X schema 2/3 header and UTF-8 QByteArray, never a naked ADIF datagram."""
    if packet.schema not in (2, 3): raise ValueError('Unsupported schema for enriched encoding')
    header = 'WSJT-X Dashboard\n<ADIF_VER:5>3.1.0<PROGRAMID:16>WSJT-X Dashboard<EOH>\n'
    rig, body = packet.rig_id.encode('utf-8'), (header + adif_text(fields)).encode('utf-8')
    data = struct.pack('!IIII', 0xADBCCBDA, packet.schema, 12, len(rig)) + rig + struct.pack('!I', len(body)) + body
    if len(data) > 65507: raise ValueError('Enriched datagram exceeds UDP size limit')
    return data


def validate_target(address, port, receiver):
    ip = ipaddress.IPv4Address(address)
    if ip.is_multicast or ip.is_unspecified or ip.is_reserved or address.endswith('.255'):
        raise ValueError('Only unicast destinations are supported')
    local = ip.is_loopback or address in (receiver.interface, receiver.listen)
    if not local:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.bind((address, 0)); local = True
        except OSError: pass
        finally: probe.close()
    if port == receiver.port and local: raise ValueError('Destination would feed the Dashboard receiving socket')


async def resolve_target(destination, receiver):
    loop = asyncio.get_running_loop()
    answers = await asyncio.wait_for(loop.getaddrinfo(destination['host'], destination['port'], family=socket.AF_INET, type=socket.SOCK_DGRAM), timeout=3)
    addresses = sorted({answer[4][0] for answer in answers})
    if not addresses: raise ValueError('No IPv4 destination address')
    # Reject a hostname if any returned address would loop, not only the selected one.
    for address in addresses: validate_target(address, destination['port'], receiver)
    return addresses[0], destination['port']


class ForwardingService:
    def __init__(self, state, settings, enrichment, qso_settings, path):
        self.state, self.settings, self.enrichment, self.qso_settings = state, settings, enrichment, qso_settings
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False); os.chmod(path, 0o600)
        self.lock = threading.RLock()
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1): self.db.close(); raise ValueError('Unsupported forwarding receipt version')
        self.db.execute('PRAGMA user_version=1')
        self.db.execute('CREATE TABLE IF NOT EXISTS forwarded_qsos(id TEXT PRIMARY KEY, created REAL NOT NULL)'); self.db.commit()
        self.outputs, self.tasks = {}, []
        self.completed = asyncio.Queue(maxsize=64)
        self.recent = OrderedDict()
        self.origins = OrderedDict()
        self.loop_drops = 0
        self.error = ''
        self.dirty = False

    def snapshot(self):
        if any(task.done() and not task.cancelled() and task.exception() for task in self.tasks):
            self.error = 'A UDP destination worker stopped. Other outputs remain independent; check network resources and save the destination settings again.'
        return dict(config=self.settings.public(), error=self.error, loopDrops=self.loop_drops, destinations=[dict(id=key, enabled=item['config']['enabled'], dispatched=item['dispatched'], filtered=item['filtered'], dropped=item['dropped'], lastSentAt=item['lastSentAt'], lastError=item['lastError'], status=item['status'], queued=item['queue'].qsize()) for key,item in self.outputs.items()], completedQueued=self.completed.qsize())

    async def configure(self, settings):
        # Cancel old queues before saving routes; disabled destinations cannot drain later.
        await self.stop_outputs()
        self.settings = settings
        self.error = ''
        for row in settings.destinations:
            item = dict(config=deepcopy(row), queue=asyncio.Queue(maxsize=256), address=None, status='disabled' if not row['enabled'] else 'resolving', dispatched=0, filtered=0, dropped=0, lastSentAt=None, lastError='')
            self.outputs[row['id']] = item
            if row['enabled']:
                self.tasks.append(asyncio.create_task(self.output_worker(item)))

    async def start(self):
        await self.configure(self.settings)
        self.completed_task = asyncio.create_task(self.completed_worker())

    async def stop_outputs(self):
        for task in self.tasks: task.cancel()
        if self.tasks: await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks = []; self.outputs = {}

    async def validate(self, settings, receiver):
        for row in settings.destinations:
            try: await resolve_target(row, receiver)
            except (OSError, asyncio.TimeoutError):
                # An unavailable host is independently diagnosed, not a global outage.
                continue

    def is_reflection(self, raw, source):
        if not self.recent: return False
        previous = self.recent.get(hashlib.sha256(raw).digest())
        if previous and time.monotonic()-previous[1] <= 3 and source != previous[0]:
            self.loop_drops += 1; self.dirty = True
            return True
        return False

    def route(self, raw, source, packet=None):
        if self.is_reflection(raw, source): return
        try: _reader, schema, kind, rig = read_header(raw)
        except PacketError: return
        if kind not in PACKET_TYPES: return
        if self.outputs: self.dirty = True
        if packet is None and schema in (2, 3): return  # Known-schema malformed payload.
        digest = hashlib.sha256(raw).digest()
        self.origins[digest] = source
        self.origins.move_to_end(digest)
        while len(self.origins)>2048: self.origins.popitem(last=False)
        enriched = []
        for key, item in self.outputs.items():
            row = item['config']
            if not row['enabled']: continue
            if kind not in row['packets'] or (row['rigs'] and rig not in row['rigs']): item['filtered'] += 1; continue
            if row['format'] == 'enriched-adif' and kind == 5:
                item['filtered'] += 1; continue
            if row['format'] == 'enriched-adif' and kind == 12 and packet:
                enriched.append((key, row)); continue
            self.enqueue(item, raw)
        if enriched:
            try:
                fields = completed_fields(packet)
                event = observed_identity(fields, rig)
                if self.completed.full():
                    for key,_row in enriched: self.outputs[key]['dropped'] += 1
                    return
                targets = []
                with self.lock, self.db:
                    for key, row in enriched:
                        receipt = hashlib.sha256((key+':'+event).encode()).hexdigest()
                        if self.db.execute('SELECT 1 FROM forwarded_qsos WHERE id=?', (receipt,)).fetchone():
                            self.outputs[key]['filtered'] += 1; continue
                        self.db.execute('INSERT INTO forwarded_qsos VALUES(?,?)', (receipt,time.time()))
                        targets.append((key,deepcopy(row)))
                    self.db.execute('DELETE FROM forwarded_qsos WHERE created<? OR id NOT IN (SELECT id FROM forwarded_qsos ORDER BY created DESC LIMIT 5000)', (time.time()-30*86400,))
                if targets:
                    profile = next((deepcopy(p) for p in self.qso_settings().rigs if p['id']==rig), {})
                    self.completed.put_nowait((packet,fields,profile,targets))
                    self.error = ''
            except (QsoError, KeyError, sqlite3.Error):
                self.error = 'Completed-QSO forwarding could not be queued; check packet diagnostics and local storage.'
                for key,_row in enriched: self.outputs[key]['dropped'] += 1

    def enqueue(self, item, data):
        try: item['queue'].put_nowait(data)
        except asyncio.QueueFull: item['dropped'] += 1

    async def output_worker(self, item):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setblocking(False)
        next_resolve = 0
        try:
            while True:
                if time.monotonic() >= next_resolve:
                    receiver = self.state.receiver
                    from .receiver import Settings
                    settings = Settings(**{k:receiver[k] for k in ('enabled','group','port','interface','listen','retention')})
                    try:
                        item['address'] = await resolve_target(item['config'], settings)
                        item.update(status='ready', lastError='')
                    except (OSError, ValueError, asyncio.TimeoutError):
                        item.update(address=None, status='error', lastError='Destination unavailable or unsafe; verify host, port and loop prevention.')
                    next_resolve = time.monotonic()+60
                    self.dirty = True
                try: data = await asyncio.wait_for(item['queue'].get(), timeout=1)
                except asyncio.TimeoutError: continue
                address = item['address']
                if not address:
                    item['dropped'] += 1; continue
                # Recheck the current receive settings before every dispatch.
                try:
                    receiver = SimpleNamespace(**self.state.receiver)
                    validate_target(address[0], address[1], receiver)
                    sent = sock.sendto(data, address)
                    if sent != len(data): raise OSError()
                    item['dispatched'] += 1; item['lastSentAt'] = int(time.time()*1000); item['lastError'] = ''
                    digest = hashlib.sha256(data).digest()
                    self.recent[digest] = (self.origins.get(digest), time.monotonic())
                    self.recent.move_to_end(digest)
                    while len(self.recent)>2048: self.recent.popitem(last=False)
                except (OSError, ValueError):
                    item['dropped'] += 1; item['lastError'] = 'UDP dispatch failed or was blocked to prevent a loop; no automatic retry.'
                finally: item['queue'].task_done()
                self.dirty = True
        finally: sock.close()

    async def completed_worker(self):
        while True:
            packet, original, profile, targets = await self.completed.get()
            try:
                fields, _sources = await enriched_completed(original, profile, self.enrichment)
                try: data = encode_logged_adif(packet, fields)
                except ValueError: data = encode_logged_adif(packet, original)
                for key, expected in targets:
                    item = self.outputs.get(key)
                    if item and item['config'] == expected and expected['enabled']:
                        self.enqueue(item, data)
            except Exception:
                self.error = 'Enriched completed-QSO encoding failed; that contact was not dispatched.'
                for key, expected in targets:
                    item = self.outputs.get(key)
                    if item and item['config'] == expected:
                        item['dropped'] += 1; item['lastError'] = self.error
            finally: self.completed.task_done()

    async def stop(self):
        await self.stop_outputs()
        task = getattr(self, 'completed_task', None)
        if task:
            task.cancel(); await asyncio.gather(task, return_exceptions=True)
        self.db.close()
