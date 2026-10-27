"""Step 0: persistent sample workspace, independent of radio reception."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import time
from .state import FocusState
from .private_storage import private_database

CALLS = ('JA2HDE', 'VK3DEMO', 'DL1DEMO', 'PY2DEMO', 'ZS6DEMO', 'W7DEMO')
RIGS = (
    ('WSJT-X - IC7300', 'IC-7300', '20m', 14074000),
    ('WSJT-X - QRPLabsQDX', 'QRP Labs QDX', '10m', 28074000),
    ('WSJT-X - Field', 'Field station', '15m', 21074000),
)


class FoundationState(FocusState):
    def __init__(self, path: Path):
        super().__init__()
        self.database = private_database(path)
        self.database.execute('CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, payload TEXT NOT NULL)')
        self.preferences = dict(title='My station', appearance='dark', radioStrip=False)
        row = self.database.execute('SELECT version, payload FROM workspace WHERE id=1').fetchone()
        if row:
            if row[0] != 1:
                raise ValueError('Unsupported workspace version; restore a compatible backup')
            data = json.loads(row[1])
            self.call, self.source = data['call'], data['source']
            self.history, self.rigs = data['history'], data['rigs']
            self.selection_sequence = data['sequence']
            self.preferences = data['preferences']
            self._saved = deepcopy(data)
        else:
            now = int(time.time() * 1000)
            for i, call in enumerate(reversed(CALLS)):
                self.select_sample(call, RIGS[i % len(RIGS)][0], at=now - (6-i)*94000)

    def snapshot(self):
        return dict(super().snapshot(), sample=True, preferences=self.preferences.copy())

    def publish(self):
        payload = dict(call=self.call, source=self.source, history=self.history, rigs=self.rigs,
                       sequence=self.selection_sequence, preferences=self.preferences)
        try:
            with self.database:
                self.database.execute('INSERT OR REPLACE INTO workspace VALUES (1, 1, ?)', (json.dumps(payload),))
        except sqlite3.Error:
            if hasattr(self, '_saved'):
                saved = deepcopy(self._saved)
                self.call, self.source = saved['call'], saved['source']
                self.history, self.rigs = saved['history'], saved['rigs']
                self.selection_sequence, self.preferences = saved['sequence'], saved['preferences']
            raise
        self._saved = deepcopy(payload)
        super().publish()

    def select_sample(self, call, rig_id, *, at=None):
        if call not in CALLS or rig_id not in {r[0] for r in RIGS}:
            raise ValueError('Choose a sample station and simulated rig from the catalog')
        rig_id, name, band, frequency = next(r for r in RIGS if r[0] == rig_id)
        now = at if at is not None else int(time.time() * 1000)
        self.rigs[rig_id] = dict(id=rig_id, name=name, band=band, frequency=frequency,
                               mode='FT8', call=call, lastSeen=now, online=False, color='#70c9bd')
        self.selection_sequence += 1
        self.history = [dict(call=call, rigId=rig_id, band=band, mode='FT8', frequency=frequency,
                             selectedAt=now, recency=self.selection_sequence)] + [e for e in self.history if e['call'] != call]
        del self.history[self.history_limit:]
        self.call, self.source = call, 'radio'
        self.publish()
