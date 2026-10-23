"""Persistent operator workspace plus bounded, volatile receiver diagnostics."""
import asyncio
import base64
from collections import deque
from copy import deepcopy
from dataclasses import asdict
import json
import sqlite3
import time
from .foundation import FoundationState
from .state import FocusState
from .protocol import diagnostic_header

PACKET_NAMES = {0: 'Heartbeat', 1: 'Status', 2: 'Decode', 3: 'Clear', 4: 'Reply', 5: 'QSO Logged',
                6: 'Close', 7: 'Replay', 8: 'Halt Tx', 9: 'Free Text', 10: 'WSPR Decode',
                11: 'Location', 12: 'Logged ADIF', 13: 'Highlight', 14: 'Switch Configuration', 15: 'Configure'}


class WorkspaceState(FoundationState):
    def __init__(self, path):
        self.ready = False
        super().__init__(path)
        self.sample_payload = deepcopy(self._saved)
        self.sample = True
        self.diagnostics = deque(maxlen=200)
        self.counters['receiverErrors'] = 0
        self.diagnostic_sequence = 0
        self.diagnostic_generation = 0
        self.storage_error = None
        self.pending_publish = None
        self.last_broadcast = 0
        self.saved_live = None
        self.database.execute('CREATE TABLE IF NOT EXISTS live_workspace (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, payload TEXT NOT NULL)')
        row = self.database.execute('SELECT version, payload FROM live_workspace WHERE id=1').fetchone()
        if row:
            if row[0] != 1:
                raise ValueError('Unsupported radio workspace version')
            self.saved_live = json.loads(row[1])
            self._restore_live(self.saved_live)
        self.ready = True

    def _restore_live(self, data):
        data = deepcopy(data)
        self.sample = False
        self.call, self.source = data['call'], data['source']
        self.history, self.selection_sequence = data['history'], data['sequence']
        self.rigs, self.previous = {}, {}  # Telemetry and baselines never survive restart.

    def enter_radio_workspace(self):
        if self.sample:
            self.sample_payload = deepcopy(self._saved)
            self._restore_live(dict(call='', source='radio', history=[], sequence=0))

    def snapshot(self):
        snapshot = super().snapshot()
        if not self.ready:
            return snapshot
        snapshot.update(sample=self.sample, step=1, storageError=self.storage_error,
                        diagnostics=dict(generation=self.diagnostic_generation, latest=self.diagnostic_sequence,
                                         retained=len(self.diagnostics), limit=self.diagnostics.maxlen))
        return snapshot

    def publish(self):
        if not self.ready:
            return super().publish()
        sample = deepcopy(self.sample_payload) if not self.sample else dict(call=self.call, source=self.source,
            history=self.history, rigs=self.rigs, sequence=self.selection_sequence)
        sample['preferences'] = self.preferences
        live = None if self.sample else dict(call=self.call, source=self.source, history=self.history,
                                             sequence=self.selection_sequence)
        changed = sample != self._saved or live != self.saved_live
        try:
            if changed:
                with self.database:
                    self.database.execute('INSERT OR REPLACE INTO workspace VALUES (1, 1, ?)', (json.dumps(sample),))
                    if live is not None:
                        self.database.execute('INSERT OR REPLACE INTO live_workspace VALUES (1, 1, ?)', (json.dumps(live),))
                self._saved, self.saved_live = deepcopy(sample), deepcopy(live)
            self.storage_error = None
        except sqlite3.Error:
            # Read-only reception must continue even if workspace persistence fails.
            self.storage_error = 'Workspace could not be saved. Check disk space and data directory permissions.'
        # Selections/preferences/browsing push immediately. Telemetry is coalesced
        # at 5 Hz; no database commits are made for ordinary packet traffic.
        if changed or time.monotonic() - self.last_broadcast >= .2:
            self.flush()
        elif self.pending_publish is None:
            try:
                self.pending_publish = asyncio.get_running_loop().call_later(.2, self.flush)
            except RuntimeError:  # Offline synchronous tests.
                self.flush()

    def flush(self):
        if self.pending_publish:
            self.pending_publish.cancel()
            self.pending_publish = None
        self.last_broadcast = time.monotonic()
        FocusState.publish(self)

    def configure_receiver(self, settings):
        self.diagnostics = deque(self.diagnostics, maxlen=settings.retention)
        self.receiver.update(asdict(settings))

    def record_datagram(self, data, source, packet=None, error=None, at=None):
        now = at if at is not None else int(time.time() * 1000)
        self.diagnostic_sequence += 1
        header = dict(instance=packet.rig_id, kind=packet.kind, schema=packet.schema) if packet else diagnostic_header(data)
        self.diagnostics.append(dict(id=self.diagnostic_sequence, at=now, source=f'{source[0]}:{source[1]}',
            instance=header.get('instance'), kind=header.get('kind'),
            name=PACKET_NAMES.get(header['kind'], 'Unknown') if header else 'Parse failure',
            schema=header.get('schema'), size=len(data), error=error,
            fields=packet.fields if packet else {}, raw=data))
        if packet:
            if packet.rig_id not in self.rigs and len(self.rigs) < self.rig_limit:
                self.rigs[packet.rig_id] = dict(id=packet.rig_id, name=packet.rig_id.removeprefix('WSJT-X - '),
                    call='', band=None, frequency=0, mode='', color='#70c9bd')
            if packet.rig_id in self.rigs:
                self.rigs[packet.rig_id].update(lastSeen=now, online=True, source=f'{source[0]}:{source[1]}')
            elif packet.kind != 1:
                self.counters['capacity'] += 1
        self.receiver['lastPacketAt'] = now

    def diagnostic_rows(self):
        return dict(generation=self.diagnostic_generation, latest=self.diagnostic_sequence,
                    limit=self.diagnostics.maxlen,
                    rows=[{k: v for k, v in row.items() if k not in ('raw', 'fields')} for row in reversed(self.diagnostics)])

    def diagnostic_detail(self, sequence):
        row = next((r for r in self.diagnostics if r['id'] == sequence), None)
        return None if row is None else {k: v for k, v in row.items() if k != 'raw'} | {'rawBase64': base64.b64encode(row['raw']).decode('ascii')}

    def clear_diagnostics(self):
        self.diagnostics.clear()
        self.diagnostic_generation += 1
        self.flush()

    def expire_instances(self, now=None):
        now = now if now is not None else int(time.time() * 1000)
        changed = False
        for rig in self.rigs.values():
            if rig.get('online') and now - rig['lastSeen'] > 90000:
                rig['online'] = False
                self.previous.pop(rig['id'], None)
                changed = True
        if changed:
            self.publish()

    def select_sample(self, call, rig_id, **kwargs):
        if self.ready and not self.sample:
            raise ValueError('Sample selections are disabled in the radio workspace; use the separate offline demo')
        return super().select_sample(call, rig_id, **kwargs)

    def close(self):
        if self.pending_publish:
            self.pending_publish.cancel()
        self.database.close()
