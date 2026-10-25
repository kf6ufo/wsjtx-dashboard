"""Bounded, restart-recoverable QSO observations. Never submits or appends contacts."""
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import json
import hashlib
import os
from pathlib import Path
import sqlite3
import time
import threading
from uuid import uuid4
from .qso_model import completed_fields, observed_identity, history_record, QsoError


def matches_contact(fields, row):
    """A callsign alone is never enough to retire an observed contact."""
    if not fields.get('STATION_CALLSIGN'): return False
    expected = datetime.strptime(fields['QSO_DATE'] + fields['TIME_ON'], '%Y%m%d%H%M%S').isoformat()
    if (row.get('call', '').upper(), row.get('station', '').upper(), row.get('date', '')[:19], row.get('band', '').lower(), row.get('mode', '').upper()) != (fields['CALL'], fields['STATION_CALLSIGN'].upper(), expected, fields['BAND'], fields.get('SUBMODE', fields['MODE'])): return False
    if fields.get('FREQ'):
        try: return Decimal(row.get('details', {}).get('freq', '')) == Decimal(fields['FREQ']) * 1_000_000
        except InvalidOperation: return False
    return True


class ObservationService:
    capacity = 1000
    delays = (2, 5, 15, 30, 60, 120, 300, 900)

    def __init__(self, state, path, history, wavelog):
        self.state, self.history, self.wavelog = state, history, wavelog
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.RLock()
        os.chmod(path, 0o600)
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1): self.db.close(); raise ValueError('Unsupported observation database version')
        self.db.execute('PRAGMA user_version=1')
        self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, rig TEXT NOT NULL, fields TEXT NOT NULL, created REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, due REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS observation_receipts(id TEXT PRIMARY KEY, created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS history_summaries(call TEXT PRIMARY KEY, payload TEXT NOT NULL, updated REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS observation_context(id INTEGER PRIMARY KEY CHECK(id=1), fingerprint TEXT NOT NULL);''')
        self.db.commit()
        self.revision, self.error = 0, ''
        self.event, self.task = asyncio.Event(), None
        self.pending = {}
        self.view_key, self.view = None, None
        self.summaries = {}
        self.context = None
        self.sync_context()
        for key, rig, raw, created, attempts, due in self.db.execute('SELECT * FROM observations'):
            self.pending[key] = dict(rig=rig, fields=json.loads(raw), created=created, attempts=attempts, due=due)
        self.summaries = {call: json.loads(raw) for call, raw in self.db.execute('SELECT call,payload FROM history_summaries')}

    def sync_context(self):
        # Only an irreversible context digest is stored, never provider credentials.
        configuration = dict(wavelog=asdict(self.wavelog.settings), source=self.history.settings.history_source, adif=self.history.settings.adif_path, complete=self.history.settings.adif_complete)
        context = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()
        if self.context == context: return
        previous = self.db.execute('SELECT fingerprint FROM observation_context WHERE id=1').fetchone()
        if not previous or previous[0] != context:
            with self.lock, self.db:
                self.db.execute('DELETE FROM history_summaries')
                self.db.execute('INSERT OR REPLACE INTO observation_context VALUES(1,?)', (context,))
            self.summaries.clear()
        self.context = context
        self.view_key = None

    def capture(self, packet):
        if packet.kind != 12: return False
        try:
            fields = completed_fields(packet)
            key = observed_identity(fields, packet.rig_id)
            if not fields.get('STATION_CALLSIGN'):
                rig = self.state.rigs.get(packet.rig_id, {})
                mapped = next((r for r in self.history.settings.rigs if r['id'] == packet.rig_id), {})
                station = rig.get('stationCall') or mapped.get('station_callsign')
                if station: fields['STATION_CALLSIGN'] = station.upper()
            if key in self.pending:
                previous = self.pending[key]['fields']
                if not previous.get('STATION_CALLSIGN') and fields.get('STATION_CALLSIGN'):
                    with self.lock, self.db:
                        self.db.execute('UPDATE observations SET fields=? WHERE id=?', (json.dumps(fields),key))
                    self.pending[key]['fields'] = fields
                    self.revision += 1; self.event.set()
                return False
            if self.db.execute('SELECT 1 FROM observation_receipts WHERE id=?', (key,)).fetchone(): return False
            if len(self.pending) >= self.capacity:
                self.error = 'The observation buffer is full. Unverified contacts are retained; historical lookups and logging remain independent.'
                return False
            now = time.time()
            with self.lock, self.db:
                self.db.execute('INSERT INTO observations(id,rig,fields,created,due) VALUES(?,?,?,?,?)', (key, packet.rig_id, json.dumps(fields), now, now + self.delays[0]))
            self.pending[key] = dict(rig=packet.rig_id, fields=fields, created=now, attempts=0, due=now+self.delays[0])
            self.revision += 1; self.error = ''; self.event.set()
            return True
        except (QsoError, KeyError, sqlite3.Error):
            self.error = 'Completed contact could not be recorded as an observation. Check packet diagnostics and local storage.'
            return False

    def fill_station_identity(self, key, item):
        if item['fields'].get('STATION_CALLSIGN'): return False
        rig = self.state.rigs.get(item['rig'], {})
        mapping = next((r for r in self.history.settings.rigs if r['id'] == item['rig']), {})
        station = rig.get('stationCall') or mapping.get('station_callsign')
        if not station: return False
        fields = item['fields'] | {'STATION_CALLSIGN': station.upper()}
        with self.lock, self.db:
            self.db.execute('UPDATE observations SET fields=? WHERE id=?', (json.dumps(fields),key))
        item['fields'] = fields
        self.revision += 1
        return True

    def remember(self, result, source):
        self.sync_context()
        if not result.get('call') or (not result.get('complete') and not result.get('records')): return
        rows = result.get('records', [])
        summary = dict(count=len(rows), complete=bool(result.get('complete')), source=source, bands=sorted({r['band'] for r in rows}), modes=sorted({r['mode'] for r in rows}))
        call = result['call']
        if self.summaries.get(call) == summary: return
        try:
            with self.lock, self.db:
                self.db.execute('INSERT OR REPLACE INTO history_summaries VALUES(?,?,?)', (call, json.dumps(summary), time.time()))
                self.db.execute('DELETE FROM history_summaries WHERE call NOT IN (SELECT call FROM history_summaries ORDER BY updated DESC LIMIT 500)')
            self.summaries[call] = summary
            if len(self.summaries) > 500:
                retained = {r[0] for r in self.db.execute('SELECT call FROM history_summaries')}
                self.summaries = {c: s for c, s in self.summaries.items() if c in retained}
        except sqlite3.Error: self.error = 'History summary could not be saved. Check local storage.'

    def base_result(self, call):
        if self.history.active:
            base = self.history.result
        else:
            base = self.wavelog.result
        if base.get('call') != call:
            return dict(call=call, status='pending', complete=False, records=[])
        return base

    def merged(self, call):
        base = self.base_result(call)
        view_key = (call, base.get('lookupId'), base.get('status'), self.revision, self.history.generation, self.wavelog.generation, id(base) if base.get('call') == call and base.get('lookupId') else 0)
        if view_key == self.view_key: return self.view
        rows = deepcopy(base.get('records', []))
        candidates = {}
        for row in rows:
            signature = (row.get('call', '').upper(), row.get('station', '').upper(), row.get('date', '')[:19], row.get('band', '').lower(), row.get('mode', '').upper())
            candidates.setdefault(signature, []).append(row)
        pending_count = 0
        source = base.get('source') or ('wavelog' if self.wavelog.settings.enabled else 'none')
        awaiting = 'Wavelog' if source == 'wavelog' else 'ADIF history' if source == 'adif' else 'a configured history source'
        for key, item in self.pending.items():
            fields = item['fields']
            if fields['CALL'] != call: continue
            date = datetime.strptime(fields['QSO_DATE'] + fields['TIME_ON'], '%Y%m%d%H%M%S').isoformat()
            signature = (call, fields.get('STATION_CALLSIGN', '').upper(), date, fields['BAND'], fields.get('SUBMODE', fields['MODE']))
            matched = [r for r in candidates.get(signature, []) if matches_contact(fields, r)]
            if matched:
                if not base.get('complete'):
                    for row in matched: row.update(observed=True, observationStatus='Found in partial history · coverage incomplete', observedRig=item['rig'])
                    pending_count += 1
                continue
            row = history_record(fields, key)
            row.update(id='observed-'+key, observed=True, observationStatus='Awaiting '+awaiting, observedRig=item['rig'])
            rows.append(row); pending_count += 1
        rows.sort(key=lambda r: (r['date'], r['id']), reverse=True)
        pending_count = sum(bool(row.get('observed')) for row in rows)
        self.view_key = view_key
        self.view = base | dict(call=call, records=rows, status='loaded' if rows else base.get('status', 'error'),
            recordCount=len(rows), pendingObserved=pending_count, historicalCount=len(rows)-pending_count,
            total=len(rows) if base.get('complete') else None, lookupId=f"{call}:{base.get('lookupId', 'observation')}:{self.revision}",
            source=source, observed=True)
        return self.view

    def snapshot(self):
        if self.task and self.task.done() and not self.task.cancelled() and self.task.exception():
            self.error = 'Observation reconciliation stopped. Pending contacts are retained; check storage and restart this Dashboard.'
        call = self.state.call
        result = self.merged(call) if call and any(i['fields']['CALL'] == call for i in self.pending.values()) else None
        summaries = {}
        counts = Counter(i['fields']['CALL'] for i in self.pending.values())
        for entry in self.state.history:
            selected = entry['call']; summary = deepcopy(self.summaries.get(selected, {}))
            count = counts[selected]
            if selected == call and result: count = result['pendingObserved']
            if count: summary['pendingObserved'] = count
            if summary: summaries[selected] = summary
        return dict(pending=len(self.pending), capacity=self.capacity, error=self.error, summaries=summaries,
            result={k: v for k,v in result.items() if k != 'records'} if result else None)

    def records(self, lookup_id):
        result = self.merged(self.state.call)
        if result['lookupId'] != lookup_id: raise QsoError('Observed history changed; use the current result')
        return deepcopy(result)

    async def start(self):
        self.task = asyncio.create_task(self.worker())

    async def worker(self):
        while True:
            due = [(key, item) for key, item in self.pending.items() if item['due'] <= time.time()]
            if not due:
                try: await asyncio.wait_for(self.event.wait(), timeout=.5)
                except asyncio.TimeoutError: pass
                self.event.clear(); continue
            call = due[0][1]['fields']['CALL']
            group = [(k,i) for k,i in self.pending.items() if i['fields']['CALL'] == call]
            settings, client, adif = self.history.settings, self.wavelog.client, self.history.adif
            result, source = None, ''
            try:
                for key, item in group: self.fill_station_identity(key, item)
                if settings.history_source != 'adif' and self.wavelog.settings.enabled:
                    async with self.wavelog.lock:
                        client.cache.pop(call, None)
                        result = await asyncio.to_thread(client.lookup, call)
                    if client is not self.wavelog.client or settings != self.history.settings: continue
                    source = 'wavelog'
                    if self.state.call == call and self.wavelog.call == call:
                        self.wavelog.result = result | {'lookupId': uuid4().hex}
                        self.wavelog.connection = deepcopy(client.connection)
                        if self.history.active:
                            self.history.result = self.wavelog.result | {'source': source}
                            self.history.key = None
                elif adif:
                    result = await asyncio.to_thread(adif.lookup, call)
                    if adif is not self.history.adif or settings != self.history.settings: continue
                    source = 'adif'
                    if self.state.call == call:
                        self.history.result = result | {'lookupId': uuid4().hex}
                        self.history.key = None
                if result: self.remember(result, source)
                now = time.time()
                retired = []
                with self.lock, self.db:
                    for key, item in group:
                        matches = [r for r in (result or {}).get('records', []) if matches_contact(item['fields'], r)]
                        verified = result and (result.get('complete') or (source == 'adif' and result.get('recordsVerified')))
                        if verified and len(matches) == 1:
                            self.db.execute('DELETE FROM observations WHERE id=?', (key,))
                            self.db.execute('INSERT OR REPLACE INTO observation_receipts VALUES(?,?)', (key, now))
                            retired.append(key)
                        else:
                            attempts = item['attempts'] + 1
                            item.update(attempts=attempts, due=now+self.delays[min(attempts, len(self.delays)-1)])
                            self.db.execute('UPDATE observations SET attempts=?,due=? WHERE id=?', (attempts,item['due'],key))
                    self.db.execute('DELETE FROM observation_receipts WHERE created<? OR id NOT IN (SELECT id FROM observation_receipts ORDER BY created DESC LIMIT 5000)', (now-30*86400,))
                for key in retired: self.pending.pop(key, None)
                if result and result.get('complete'): self.error = ''
                self.revision += 1
                self.history.event.set(); self.state.flush()
            except asyncio.CancelledError: raise
            except Exception:
                self.error = 'History reconciliation is unavailable; locally observed contacts remain unverified.'
                for key, item in group:
                    item['due'] = time.time()+60
                self.state.flush()
            # Global read pacing prevents an outage/restart from producing a request burst.
            await asyncio.sleep(2)

    async def stop(self):
        if self.task:
            self.task.cancel()
            try: await self.task
            except asyncio.CancelledError: pass
        self.db.close()
