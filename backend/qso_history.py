"""Provider-independent history queries and lazy ADIF fallback/recovery."""
import asyncio
from copy import deepcopy
from pathlib import Path
import time
import threading
from typing import Protocol
from uuid import uuid4
from .wavelog import WavelogError
from .qso_model import adif_records, history_record, QsoError


def filter_history(result, band=None, mode=None):
    out = deepcopy(result)
    out['records'] = [r for r in out.get('records', []) if (not band or r['band'].lower() == band.lower()) and (not mode or r['mode'].upper() == mode.upper())]
    out['total'] = len(out['records']) if out.get('complete') else None
    out['worked'] = bool(out['records']) if out.get('complete') else True if out['records'] else None
    return out


class HistoryProvider(Protocol):
    def lookup(self, call: str, band: str | None = None, mode: str | None = None) -> dict: ...


class WavelogHistoryProvider:
    def __init__(self, client): self.client = client
    def lookup(self, call, band=None, mode=None): return filter_history(self.client.lookup(call), band, mode)


class ADIFHistoryProvider:
    def __init__(self, path, complete=False):
        self.path, self.coverage = Path(path), complete
        self.index, self.stamp, self.error, self.complete = {}, None, '', False
        self.version = uuid4().hex
        self.loads = 0
        self.lock = threading.RLock()

    def load(self):
        with self.lock: return self._load()

    def _load(self):
        index = {}
        try:
            if self.path.is_symlink() or not self.path.is_file(): raise OSError()
            before = self.path.stat()
            stamp = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            if stamp == self.stamp: return
            self.loads += 1
            error = ''
            with self.path.open(encoding='utf-8-sig', newline='') as source:
                try:
                    for number, fields in enumerate(adif_records(source)):
                        try:
                            row = history_record(fields, number)
                            keys = {(row['call'], None, None), (row['call'], row['band'], None)}
                            for mode in {row['mode'], fields.get('MODE', '').upper()} - {''}:
                                keys.update({(row['call'], None, mode), (row['call'], row['band'], mode)})
                            for key in keys: index.setdefault(key, []).append(row)
                        except QsoError: error = 'Some ADIF contacts are invalid; history is incomplete.'
                except (QsoError, UnicodeError): error = 'ADIF is malformed or unfinished; history is incomplete.'
            after = self.path.stat()
            if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != stamp:
                error = 'ADIF changed while loading; history is incomplete. Retry after the writer finishes.'
            for rows in index.values(): rows.sort(key=lambda r: (r['date'], r['id']), reverse=True)
            self.index, self.stamp = index, stamp
            self.complete = self.coverage and not error
            self.error = error or ('' if self.coverage else 'Local History Only · historical coverage has not been declared complete.')
            self.version = uuid4().hex
        except (OSError, UnicodeError):
            message = 'ADIF history is missing, unreadable or not a regular file; worked status is unknown.'
            if self.complete or self.error != message: self.version = uuid4().hex
            self.complete, self.error = False, message

    def lookup(self, call, band=None, mode=None):
        with self.lock: return self._lookup(call, band, mode)

    def _lookup(self, call, band=None, mode=None):
        self.load()
        rows = deepcopy(self.index.get((call.upper(), band.lower() if band else None, mode.upper() if mode else None), []))
        return dict(call=call, worked=bool(rows) if self.complete else True if rows else None, status=('loaded' if rows else 'empty') if self.complete else ('incomplete' if rows else 'error'),
            complete=self.complete, records=rows, total=len(rows) if self.complete else None,
            source='adif', scope='Local ADIF file', message=self.error, coverage='complete' if self.complete else 'incomplete',
            confirmationStatus='file-only', cached=False, updatedAt=int(time.time()*1000), version=self.version)


class QsoHistoryService:
    """Compose the existing asynchronous Wavelog service without duplicating its lookups."""
    def __init__(self, state, settings, wavelog):
        self.state, self.settings, self.wavelog = state, settings, wavelog
        self.adif = ADIFHistoryProvider(settings.adif_path, settings.adif_complete) if settings.adif_path else None
        self.result = dict(call='', status='idle', complete=False, records=[])
        self.event, self.task, self.next_probe = asyncio.Event(), None, 0
        self.generation = 0
        self.key = None
        self.probe = None

    @property
    def active(self): return bool(self.settings.adif_path or self.settings.history_source == 'adif')

    def configure(self, settings):
        self.settings = settings
        self.adif = ADIFHistoryProvider(settings.adif_path, settings.adif_complete) if settings.adif_path else None
        self.generation += 1; self.key = None; self.next_probe = 0; self.event.set()

    def snapshot(self):
        result = self.result if self.result.get('call') == self.state.call else dict(call=self.state.call, status='pending', complete=False, records=[])
        return dict(provider=result.get('source', 'none'), notice='Local History Only' if result.get('source') == 'adif' else '', label='Local ADIF' if result.get('source') == 'adif' else 'Wavelog' if result.get('source') == 'wavelog' else 'QSO history', result={k: deepcopy(v) for k,v in result.items() if k != 'records'} | {'recordCount': len(result.get('records', []))})

    def history(self, lookup_id):
        if not self.active: return self.wavelog.history(lookup_id)
        if self.result.get('lookupId') != lookup_id: raise QsoError('History changed; use the latest snapshot')
        return deepcopy(self.result)

    def observe(self): self.event.set()

    def refresh(self):
        if self.adif: self.adif.stamp = None
        self.key = None; self.wavelog.refresh(); self.event.set()

    async def start(self):
        async def startup():
            if self.wavelog.settings.enabled:
                try: await self.wavelog.test()
                except WavelogError: pass
            if self.adif and (self.settings.history_source == 'adif' or not self.wavelog.settings.enabled or self.wavelog.connection.get('status') == 'error'):
                await asyncio.to_thread(self.adif.load)
            self.event.set()
        self.probe = asyncio.create_task(startup())
        self.task = asyncio.create_task(self.worker())
        self.event.set()

    async def worker(self):
        while True:
            try: await asyncio.wait_for(self.event.wait(), timeout=1)
            except asyncio.TimeoutError: pass
            self.event.clear()
            if not self.active or self.state.sample or not self.state.call: continue
            call, token = self.state.call, self.generation
            observation_revision = getattr(getattr(self.state, 'observations', None), 'revision', 0)
            wr = self.wavelog.result
            enabled = self.wavelog.settings.enabled
            source = self.settings.history_source
            if source != 'adif' and enabled and wr.get('call') == call and wr.get('complete'):
                result = deepcopy(wr) | {'source': 'wavelog'}
                key = ('wavelog', wr.get('lookupId'))
            elif source != 'adif' and enabled and self.wavelog.connection.get('status') != 'error' and wr.get('status') in ('pending', 'idle'):
                # Do not load an ADIF index unnecessarily while Wavelog connects.
                if self.result.get('call') == call and self.result.get('source') == 'adif': continue
                result = dict(call=call, status='pending', complete=False, records=[], source='wavelog')
                key = ('pending', call)
            elif source != 'wavelog' and self.adif:
                result = await asyncio.to_thread(self.adif.lookup, call)
                if not result['records'] and not result['complete'] and wr.get('call') == call and wr.get('records'):
                    result = deepcopy(wr) | {'source': 'wavelog', 'complete': False, 'status': 'incomplete'}
                key = (result.get('source'), call, result.get('version'), result.get('status'), result.get('updatedAt') if result.get('source') == 'wavelog' else '')
            else:
                result = deepcopy(wr) | {'source': 'wavelog'} if source != 'adif' and wr.get('call') == call else dict(call=call, status='error', complete=False, records=[], source='none', message='No history source is configured; worked status is unknown.')
                key = (result.get('source'), call, result.get('lookupId'), result.get('status'))
            if call != self.state.call or token != self.generation: continue
            if observation_revision != getattr(getattr(self.state, 'observations', None), 'revision', 0): continue
            if key != self.key:
                self.key = key; self.result = result | {'lookupId': uuid4().hex}
                if getattr(self.state, 'observations', None): self.state.observations.remember(self.result, self.result.get('source', 'none'))
                self.state.flush()
            if source != 'adif' and enabled and self.wavelog.connection.get('status') == 'error' and time.monotonic() >= self.next_probe and not self.wavelog.lock.locked():
                self.next_probe = time.monotonic() + self.settings.recovery_seconds
                for item in self.wavelog.client.cache.values(): item['updatedAt'] = 0
                self.wavelog.call = None; self.wavelog.observe()

    async def stop(self):
        if self.probe: await self.probe
        if self.task:
            self.task.cancel()
            try: await self.task
            except asyncio.CancelledError: pass
