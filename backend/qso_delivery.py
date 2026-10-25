"""Persistent outbox and independent ADIF/Wavelog destinations. No UDP forwarding."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Protocol
import sqlite3
import stat
import threading
import time
from .qso_model import parse_completed, enrich_qso, identity, adif_text, adif_records, QsoError
from .wavelog import WavelogClient, WavelogError
import requests


class DeliveryError(QsoError): pass
class UncertainDelivery(DeliveryError): pass


class LoggingDestination(Protocol):
    def prepare(self, fields: dict, uncertain: bool = False) -> str | None: ...
    def write(self, key: str, fields: dict) -> str: ...


class DeliveryQueue:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path, check_same_thread=False)
        os.chmod(path, 0o600)
        self.lock = threading.RLock()
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0,1): self.db.close(); raise ValueError('Unsupported delivery queue version')
        self.db.execute('PRAGMA user_version=1')
        self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS qso_outbox (
          id TEXT PRIMARY KEY, rig TEXT NOT NULL, original TEXT NOT NULL, normalized TEXT,
          sources TEXT, profile TEXT NOT NULL, status TEXT NOT NULL, message TEXT NOT NULL DEFAULT '', created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS qso_delivery (
          id TEXT NOT NULL, destination TEXT NOT NULL, target TEXT NOT NULL, status TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0, message TEXT NOT NULL DEFAULT '', remote_id TEXT,
          PRIMARY KEY(id,destination));
          CREATE TABLE IF NOT EXISTS qso_file_journal (
          id TEXT PRIMARY KEY, path TEXT NOT NULL, offset INTEGER NOT NULL, prefix_hash TEXT NOT NULL, payload BLOB NOT NULL);
        ''')
        self.db.execute('CREATE INDEX IF NOT EXISTS delivery_due ON qso_delivery(destination,status,next_attempt)')
        self.db.execute('CREATE INDEX IF NOT EXISTS outbox_pending ON qso_outbox(status,created)')
        self.db.execute("UPDATE qso_delivery SET status='uncertain' WHERE destination='wavelog' AND status='inflight'")
        self.db.execute("UPDATE qso_delivery SET status='pending' WHERE destination='adif' AND status='inflight'")
        self.db.commit()

    def execute(self, sql, args=()):
        with self.lock, self.db:
            cursor = self.db.execute(sql, args)
            return cursor.fetchall()

    def capture(self, rig, original, profile, targets):
        key = hashlib.sha256((rig + ':' + identity(original)).encode()).hexdigest()
        with self.lock, self.db:
            exists = self.db.execute('SELECT 1 FROM qso_outbox WHERE id=?', (key,)).fetchone()
            if exists: return key
            self.db.execute('INSERT INTO qso_outbox(id,rig,original,profile,status,created) VALUES(?,?,?,?,?,?)', (key, rig, json.dumps(original), json.dumps(profile), 'pending', time.time()))
            for name, target in targets.items(): self.db.execute('INSERT INTO qso_delivery(id,destination,target,status) VALUES(?,?,?,?)', (key,name,json.dumps(target),'pending'))
        return key

    def delivered(self, key, name, remote):
        with self.lock, self.db:
            self.db.execute("UPDATE qso_delivery SET status='delivered',attempts=attempts+1,message='',remote_id=? WHERE id=? AND destination=?", (str(remote),key,name))
            if name == 'adif': self.db.execute('DELETE FROM qso_file_journal WHERE id=?', (key,))
            if not self.db.execute("SELECT 1 FROM qso_delivery WHERE id=? AND status!='delivered'",(key,)).fetchone():
                # Keep a dedupe receipt, not a second permanent contact log.
                self.db.execute("UPDATE qso_outbox SET status='delivered',original='{}',normalized=NULL,sources=NULL,message='' WHERE id=?",(key,))

    def summary(self):
        jobs = dict(self.execute('SELECT status,COUNT(*) FROM qso_outbox GROUP BY status'))
        destinations = self.execute('SELECT destination,status,COUNT(*) FROM qso_delivery GROUP BY destination,status')
        recent = self.execute('SELECT id,rig,status,message,created FROM qso_outbox ORDER BY created DESC LIMIT 30')
        details = self.execute('SELECT id,destination,status,attempts,message,remote_id FROM qso_delivery WHERE id IN (SELECT id FROM qso_outbox ORDER BY created DESC LIMIT 30)')
        return dict(jobs=jobs, destinations=[dict(destination=d,status=s,count=n) for d,s,n in destinations], recent=[dict(id=i,rig=r,status=s,message=m,created=t,deliveries=[dict(destination=d,status=ds,attempts=a,message=dm,remoteId=remote) for qi,d,ds,a,dm,remote in details if qi==i]) for i,r,s,m,t in recent])

    def close(self):
        with self.lock: self.db.close()


class ADIFLogWriter:
    def __init__(self, path, queue): self.path, self.queue = Path(path), queue

    def prepare(self, fields, uncertain=False): return None

    @staticmethod
    def hash_prefix(stream, length):
        stream.seek(0); digest = hashlib.sha256()
        while length:
            part = stream.read(min(length, 65536))
            if not part: raise DeliveryError('ADIF changed during recovery; operator review required')
            digest.update(part); length -= len(part)
        return digest.hexdigest()

    def write(self, key, fields):
        if self.path.is_symlink() or not self.path.parent.is_dir() or (self.path.exists() and not self.path.is_file()): raise DeliveryError('ADIF destination must be a regular file in an existing directory')
        # O_NOFOLLOW avoids following a replaced target on supported POSIX hosts.
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd); raise DeliveryError('ADIF destination is not a regular file')
        with os.fdopen(fd, 'r+b') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            journal = self.queue.execute('SELECT path,offset,prefix_hash,payload FROM qso_file_journal WHERE id=?', (key,))
            if journal:
                path, offset, prefix_hash, payload = journal[0]
                if path != str(self.path) or self.hash_prefix(stream, offset) != prefix_hash: raise DeliveryError('ADIF recovery found a changed file; operator review required')
                stream.seek(offset); tail = stream.read(len(payload))
                if tail == payload: return 'ADIF append recovered'
                if not payload.startswith(tail): raise DeliveryError('ADIF recovery found an unexpected tail; operator review required')
                # Only our exact, journaled partial append may be truncated.
                stream.truncate(offset); stream.seek(offset); stream.write(payload); stream.flush(); os.fsync(stream.fileno())
                return 'ADIF partial append recovered'
            stream.seek(0)
            # A retry after a committed append is recognized independently of the outbox state.
            wrapper = io.TextIOWrapper(stream, encoding='utf-8-sig', newline='')
            duplicate = False
            try:
                for record in adif_records(wrapper):
                    if record.get('APP_WSJT_DASHBOARD_ID') == key or identity(record) == identity(fields): duplicate = True
            except (QsoError, UnicodeError): raise DeliveryError('ADIF destination has an invalid tail; repair it before appending') from None
            finally: wrapper.detach()
            if duplicate: return 'Existing ADIF contact verified'
            stream.seek(0, os.SEEK_END); offset = stream.tell()
            payload = (('WSJT-X Dashboard\n<ADIF_VER:5>3.1.0<PROGRAMID:16>WSJT-X Dashboard<EOH>\n' if offset == 0 else '\n') + adif_text(fields | {'APP_WSJT_DASHBOARD_ID': key})).encode('utf-8')
            prefix_hash = self.hash_prefix(stream, offset)
            self.queue.execute('INSERT INTO qso_file_journal VALUES(?,?,?,?,?)', (key,str(self.path),offset,prefix_hash,payload))
            stream.seek(offset); stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            # Persist the directory entry when the destination was newly created.
            directory = os.open(self.path.parent, os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
            return 'ADIF contact appended'


class WavelogLogWriter:
    def __init__(self, settings, station_id, station_call):
        self.settings = replace(settings, enabled=True, scope_mode='stations', station_ids=[station_id])
        self.station_id, self.station_call = station_id, station_call
        self.client = WavelogClient(self.settings)

    def matches(self, fields):
        result = self.client.lookup(fields['CALL'])
        if not result.get('complete'): raise DeliveryError('Wavelog reconciliation could not read complete history')
        date = datetime.strptime(fields['QSO_DATE'] + fields['TIME_ON'], '%Y%m%d%H%M%S')
        rows = [r for r in result['records'] if r.get('stationId') == self.station_id and r['date'][:19] == date.isoformat() and r['band'].lower() == fields['BAND'].lower() and r['mode'].upper() == fields.get('SUBMODE', fields['MODE']).upper()]
        if fields.get('FREQ'):
            frequency = Decimal(fields['FREQ']) * 1_000_000
            if any(not row.get('details', {}).get('freq') for row in rows): raise UncertainDelivery('Matching Wavelog contact lacks frequency; operator review required')
            try: rows = [row for row in rows if Decimal(row['details']['freq']) == frequency]
            except Exception: raise UncertainDelivery('Matching Wavelog frequency could not be verified') from None
        if len(rows) > 1: raise UncertainDelivery('Multiple matching Wavelog contacts; review duplicates in Wavelog')
        return rows[0]['id'] if rows else None

    def prepare(self, fields, uncertain=False):
        self.client.begin(); connection = self.client.connect()
        if 'qso:write' not in connection['scopes']: raise DeliveryError('Wavelog token needs qso:read, station:read and qso:write')
        station = self.client.station_by_id(self.station_id)
        if not fields.get('STATION_CALLSIGN') or station['callsign'].upper() != fields['STATION_CALLSIGN'].upper() or (self.station_call and self.station_call != fields['STATION_CALLSIGN']):
            raise DeliveryError('QSO station callsign does not match its mapped Wavelog location')
        existing = self.matches(fields)
        if existing: return existing
        if uncertain: raise UncertainDelivery('Previous Wavelog outcome is unknown; no matching contact yet. Reconciliation only; automatic resubmission is held.')
        return None

    def write(self, key, fields):
        payload = {k.lower(): v for k,v in fields.items() if not k.startswith('APP_')}
        payload.update(station_profile_id=self.station_id, qso_date=fields['QSO_DATE'][:4]+'-'+fields['QSO_DATE'][4:6]+'-'+fields['QSO_DATE'][6:], mode=fields.get('SUBMODE', fields['MODE']))
        for key in ('freq','freq_rx'):
            if key in payload: payload[key] = int(Decimal(payload[key])*1_000_000)
        try:
            with requests.post(self.settings.url + '/api/v2/qso', json=payload, headers={'Authorization': 'Bearer '+self.settings.token, 'Accept':'application/json'}, timeout=(5,self.settings.timeout_seconds), allow_redirects=False, stream=True) as response:
                # Rejections before creation are retryable after operator/config repair.
                if response.status_code in (400,401,403,404,405,422,429): raise DeliveryError('Wavelog rejected QSO submission; check permissions, mapping, fields or rate limit')
                if response.status_code != 201: raise UncertainDelivery('Wavelog submission outcome is uncertain; reconciliation required')
                data = b''
                for chunk in response.iter_content(65536):
                    data += chunk
                    if len(data)>1_000_000: raise UncertainDelivery('Wavelog response exceeded its limit; reconciliation required')
                body = json.loads(data).get('data', {})
                if type(body.get('id')) is not int or body['id'] < 1: raise UncertainDelivery('Wavelog did not return a valid QSO ID; reconciliation required')
                return str(body['id'])
        except DeliveryError: raise
        except Exception: raise UncertainDelivery('Wavelog response was lost or unreadable; reconciliation required') from None


class QsoDeliveryService:
    def __init__(self, state, settings, wavelog, enrichment, path, history):
        self.state, self.settings, self.wavelog, self.enrichment, self.history = state, settings, wavelog, enrichment, history
        self.queue = DeliveryQueue(path)
        self.tasks = []
        self.last_error = ''
        self.accepting = True
        self.stopping = False

    def snapshot(self):
        configured = bool(self.settings.adif_path or self.settings.log_to_wavelog)
        if any(task.done() and not task.cancelled() and task.exception() for task in self.tasks):
            self.last_error = 'A delivery worker stopped. Pending QSOs are retained; repair storage/configuration and restart this dashboard.'
        try: summary = self.queue.summary()
        except sqlite3.Error: summary = dict(jobs={},destinations=[],recent=[]); self.last_error = 'Delivery queue cannot be read. Check disk space and data-directory permissions.'
        return dict(config=self.settings.public(), enabled=self.settings.logging_enabled,
            warning=('No historical source or logging destination is configured.' if not self.settings.adif_path and not self.wavelog.settings.enabled else '') if not self.settings.logging_enabled else ('No logging destinations configured; completed QSOs will not be persisted.' if not configured else ''),
            error=self.last_error, queue=summary)

    def capture(self, packet):
        if not self.accepting or not self.settings.logging_enabled or packet.kind != 12: return
        if not self.settings.adif_path and not self.settings.log_to_wavelog: return
        try:
            original = parse_completed(packet.fields['adif'])
            profile = next((deepcopy(r) for r in self.settings.rigs if r['id']==packet.rig_id), {})
            targets = {}
            if self.settings.adif_path: targets['adif'] = {'path': self.settings.adif_path}
            if self.settings.log_to_wavelog: targets['wavelog'] = {'url': self.wavelog.settings.url, 'station_id': profile.get('wavelog_station_id',0)}
            self.queue.capture(packet.rig_id, original, profile, targets)
            self.last_error = ''
        except (QsoError, OSError, sqlite3.Error, KeyError):
            self.last_error = 'Completed QSO could not be validated or durably queued. Check packet diagnostics, disk space and configuration.'
        self.state.flush()

    def retry(self):
        self.queue.execute("UPDATE qso_outbox SET status='pending' WHERE status='blocked'")
        self.queue.execute("UPDATE qso_delivery SET next_attempt=0 WHERE status IN ('pending','error','uncertain')")

    async def start(self):
        if self.settings.adif_path and self.settings.logging_enabled:
            path = Path(self.settings.adif_path)
            if path.is_symlink() or not path.parent.is_dir() or (path.exists() and (not path.is_file() or not os.access(path,os.W_OK))) or (not path.exists() and not os.access(path.parent,os.W_OK)): self.last_error = 'ADIF destination path is unavailable; deliveries will remain queued.'
        self.tasks = [asyncio.create_task(self.prepare_worker())] + [asyncio.create_task(self.deliver_worker(name)) for name in ('adif','wavelog')]

    async def prepare_worker(self):
        while not self.stopping:
            await asyncio.sleep(.1)
            if self.stopping or not self.settings.logging_enabled: continue
            rows = self.queue.execute("SELECT id,rig,original,profile FROM qso_outbox WHERE status='pending' ORDER BY created LIMIT 1")
            if not rows: continue
            key, rig, raw, mapping = rows[0]; original, profile = json.loads(raw), json.loads(mapping)
            profile = profile or next((deepcopy(r) for r in self.settings.rigs if r['id']==rig), {})
            try:
                result = {}
                if self.enrichment.settings.enabled:
                    try:
                        async with self.enrichment.lock:
                            result = await asyncio.to_thread(self.enrichment.providers.enrich, {'call':original['CALL'], 'dxGrid':original.get('GRIDSQUARE',''), 'deGrid':original.get('MY_GRIDSQUARE','')})
                    except Exception: result = {}
                fields, sources = enrich_qso(original, profile, result)
                fields.setdefault('APP_WSJT_DASHBOARD_RIG', rig)
                sources.setdefault('APP_WSJT_DASHBOARD_RIG', 'WSJT-X network ID')
                if not fields.get('STATION_CALLSIGN'): raise QsoError('Set a station identity for this WSJT-X network ID, then retry')
                self.queue.execute("UPDATE qso_outbox SET normalized=?,sources=?,profile=?,status='ready',message='' WHERE id=?", (json.dumps(fields),json.dumps(sources),json.dumps(profile),key))
                if profile.get('wavelog_station_id'):
                    targets = self.queue.execute("SELECT target FROM qso_delivery WHERE id=? AND destination='wavelog'", (key,))
                    if targets:
                        target = json.loads(targets[0][0]); target['station_id'] = target['station_id'] or profile['wavelog_station_id']
                        self.queue.execute('UPDATE qso_delivery SET target=? WHERE id=? AND destination=?', (json.dumps(target),key,'wavelog'))
            except QsoError:
                self.queue.execute("UPDATE qso_outbox SET status='blocked',message='Station identity is missing; configure the originating rig and retry.' WHERE id=?",(key,))
            self.state.flush()

    async def deliver_worker(self, name):
        while not self.stopping:
            await asyncio.sleep(.1)
            if self.stopping or not self.settings.logging_enabled: continue
            rows = self.queue.execute("""SELECT d.id,d.target,d.status,d.attempts,q.normalized,q.profile FROM qso_delivery d JOIN qso_outbox q ON q.id=d.id
                WHERE d.destination=? AND q.status='ready' AND d.status IN ('pending','error','uncertain') AND d.next_attempt<=? ORDER BY q.created LIMIT 1""",(name,time.time()))
            if not rows: continue
            key, raw_target, status, attempts, raw_fields, raw_profile = rows[0]
            target, fields, profile = json.loads(raw_target), json.loads(raw_fields), json.loads(raw_profile)
            try:
                if name=='adif':
                    if target['path'] != self.settings.adif_path: raise DeliveryError('Queued ADIF destination differs from current configuration; delivery is held')
                    writer = ADIFLogWriter(target['path'],self.queue)
                else:
                    if not self.settings.log_to_wavelog or target['url'] != self.wavelog.settings.url or not target['station_id']: raise DeliveryError('Queued Wavelog destination/mapping is disabled or differs from current configuration')
                    writer = WavelogLogWriter(self.wavelog.settings,target['station_id'],profile.get('station_callsign',''))
                remote = await asyncio.to_thread(writer.prepare,fields,status=='uncertain')
                if not remote:
                    if self.stopping or not self.settings.logging_enabled: raise DeliveryError('Delivery paused; QSO remains queued')
                    if name=='wavelog' and (not self.settings.log_to_wavelog or target['url'] != self.wavelog.settings.url): raise DeliveryError('Wavelog destination changed; delivery is held')
                    if name=='adif' and target['path'] != self.settings.adif_path: raise DeliveryError('ADIF destination changed; delivery is held')
                    self.queue.execute("UPDATE qso_delivery SET status='inflight' WHERE id=? AND destination=?",(key,name))
                    remote = await asyncio.to_thread(writer.write,key,fields)
                self.queue.delivered(key,name,remote)
                self.history.key = None; self.history.event.set()
                if name=='wavelog':
                    self.wavelog.client.cache.pop(fields['CALL'],None)
                    if self.state.call==fields['CALL']: self.wavelog.call=None;self.wavelog.observe()
            except Exception as error:
                # Unknown HTTP outcomes are never blindly retried. Only reconciliation runs.
                uncertain = name=='wavelog' and (status=='uncertain' or isinstance(error,UncertainDelivery))
                message = str(error) if isinstance(error, DeliveryError) else 'Destination unavailable; delivery is retained for retry.'
                self.queue.execute('UPDATE qso_delivery SET status=?,attempts=attempts+1,message=?,next_attempt=? WHERE id=? AND destination=?',('uncertain' if uncertain else 'error',message,time.time()+min(300,2**min(attempts+1,8)),key,name))
            self.state.flush()

    async def stop(self):
        self.accepting = False
        self.stopping = True
        if self.tasks: await asyncio.gather(*self.tasks)
        self.queue.close()
