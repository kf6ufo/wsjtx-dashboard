"""Read-only Wavelog API v2 history. No QSO records are written to local disk."""
import asyncio
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
import json
import threading
import time
from uuid import uuid4

import requests
from .wavelog_config import WavelogSettings


class WavelogError(ValueError):
    """Only application-authored messages, never response bodies or request URLs."""


def positive_id(value):
    if type(value) is not int or value < 1:
        raise WavelogError('Wavelog returned an invalid record identifier.')
    return value


def text(value, limit=512):
    return '' if value is None else str(value)[:limit]


class WavelogClient:
    def __init__(self, settings):
        self.settings = settings
        self.connection = dict(status='idle', stations=[], logbooks=[], scopes=[])
        self.cache = OrderedDict()
        self.cancelled = threading.Event()
        self.deadline = 0
        self.cooldown_until = 0
        self.connected_at = 0

    def begin(self):
        self.deadline = time.monotonic() + 60
        if not self.settings.url or not self.settings.token:
            raise WavelogError('Enter the Wavelog URL and API v2 token in Settings.')

    def get_json(self, resource, params=None, *, public=False):
        # This transport deliberately has no write method or arbitrary endpoint input.
        if resource not in ('status', 'token', 'station', 'logbook', 'qso', 'confirmation') and not (
            resource.split('/')[0] in ('station', 'logbook') and resource.split('/')[-1].isdigit() and resource.count('/') == 1):
            raise WavelogError('Unsupported read operation.')
        if self.cancelled.is_set() or time.monotonic() >= self.deadline:
            raise WavelogError('History lookup stopped or exceeded its time limit. Retry to refresh.')
        if time.monotonic() < self.cooldown_until:
            raise WavelogError('Wavelog is rate limiting requests. Wait before retrying.')
        headers = {'Accept': 'application/json'}
        if not public:
            headers['Authorization'] = 'Bearer ' + self.settings.token
        try:
            timeout = min(self.settings.timeout_seconds, max(.1, self.deadline - time.monotonic()))
            with requests.get(self.settings.url + '/api/v2/' + resource, params=params,
                headers=headers, timeout=(min(5, timeout), timeout), allow_redirects=False, stream=True) as response:
                if 300 <= response.status_code < 400:
                    raise WavelogError('Wavelog redirected the request. Save the final application URL, including index.php if needed.')
                if response.status_code == 401:
                    raise WavelogError('Wavelog rejected the token. Check that it is a valid, unexpired API v2 token.')
                if response.status_code == 403:
                    raise WavelogError('Wavelog denied access. Check token scopes and the selected station locations.')
                if response.status_code == 404:
                    raise WavelogError('This Wavelog endpoint is unavailable. Check the URL and API v2 support (Wavelog 3.1.0 or later).')
                if response.status_code == 429:
                    self.cooldown_until = time.monotonic() + 60
                    raise WavelogError('Wavelog is rate limiting requests. Wait at least one minute before retrying.')
                if response.status_code != 200:
                    raise WavelogError('Wavelog could not complete the read request. Check the server and retry.')
                chunks, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > 4_000_000 or time.monotonic() >= self.deadline or self.cancelled.is_set():
                        raise WavelogError('Wavelog response exceeded the size/time limit. Reduce the page size and retry.')
                    chunks.append(chunk)
                payload = json.loads(b''.join(chunks))
            if not isinstance(payload, dict) or 'data' not in payload or 'error' in payload:
                raise WavelogError('Wavelog returned an unexpected API response. Check the application URL and API version.')
            return payload
        except WavelogError:
            raise
        except Exception:
            raise WavelogError('Cannot read Wavelog. Check the URL, network connection and server certificate.') from None

    @staticmethod
    def station(row):
        if not isinstance(row, dict):
            raise WavelogError('Wavelog returned invalid station information.')
        return dict(id=positive_id(row.get('id')), name=text(row.get('name')), callsign=text(row.get('callsign')),
            grid=text(row.get('gridsquare')), active=row.get('active') is True)

    @staticmethod
    def logbook(row):
        if not isinstance(row, dict) or not isinstance(row.get('station_ids'), list):
            raise WavelogError('Wavelog returned invalid logbook information.')
        return dict(id=positive_id(row.get('id')), name=text(row.get('name')), active=row.get('active') is True,
            stationIds=[positive_id(i) for i in row['station_ids']])

    def connect(self):
        if self.connection['status'] == 'ready' and time.monotonic() - self.connected_at < 600:
            return self.connection
        status = self.get_json('status', public=True).get('data')
        if not isinstance(status, dict) or status.get('status') != 'ok':
            raise WavelogError('Wavelog API v2 could not be verified at this URL.')
        token = self.get_json('token').get('data')
        if not isinstance(token, dict) or not isinstance(token.get('scopes'), list):
            raise WavelogError('Wavelog returned invalid token information.')
        scopes = token['scopes']
        if not {'qso:read', 'station:read'} <= set(scopes):
            raise WavelogError('The token needs qso:read and station:read. Add logbook:read or confirmation:read for those optional details.')
        stations = self.get_json('station')['data']
        if not isinstance(stations, list) or len(stations) > 1000:
            raise WavelogError('Wavelog returned invalid station information.')
        stations = [self.station(row) for row in stations]
        books, notices = [], []
        if 'logbook:read' in scopes:
            try:
                data = self.get_json('logbook')['data']
                if not isinstance(data, list) or len(data) > 1000:
                    raise WavelogError('Invalid logbook list.')
                books = [self.logbook(row) for row in data]
            except WavelogError:
                notices.append('Logbook listing is unavailable; all-locations and selected-locations scopes can still be used.')
        self.connection = dict(status='ready', api='v2', owner=text(token.get('owner')), expiresAt=text(token.get('expires_at')),
            scopes=[text(scope, 80) for scope in scopes], stations=stations, logbooks=books, notices=notices,
            checkedAt=int(time.time() * 1000), message='Read access verified. Wavelog remains the source of record.')
        self.connected_at = time.monotonic()
        return self.connection

    def scope(self):
        connection = self.connect()
        mode = self.settings.scope_mode
        stations = {row['id']: row for row in connection['stations']}
        if mode == 'all':
            ids, label = None, 'All station locations authorized by this token'
        elif mode == 'stations':
            ids, label = self.settings.station_ids, 'Selected station locations'
        else:
            book = self.logbook(self.get_json('logbook/' + str(self.settings.logbook_id))['data'])
            if book['id'] != self.settings.logbook_id:
                raise WavelogError('Wavelog returned a different logbook. Check the selected scope.')
            ids, label = book['stationIds'], book['name'] or f"Logbook {book['id']}"
            if not ids:
                raise WavelogError('The selected logbook has no station locations. Choose another scope.')
        for sid in ids or []:
            if sid not in stations:
                stations[sid] = self.station_by_id(sid)
        return ids, label, stations

    def station_by_id(self, sid):
        station = self.station(self.get_json('station/' + str(sid))['data'])
        if station['id'] != sid:
            raise WavelogError('Wavelog returned a different station location. History is incomplete.')
        return station

    def pages(self, resource, params, info, *, limit):
        expected_total, received = None, 0
        for page in range(1, self.settings.max_pages + 1):
            payload = self.get_json(resource, params | {'page': page, 'per_page': self.settings.page_size})
            rows, meta = payload['data'], payload.get('meta')
            if not isinstance(rows, list) or not isinstance(meta, dict):
                raise WavelogError('Wavelog did not return a paginated history response.')
            total, more = meta.get('total'), meta.get('has_more')
            if type(total) is not int or total < 0 or type(more) is not bool or meta.get('page', page) != page:
                raise WavelogError('Wavelog returned invalid pagination metadata.')
            if expected_total is not None and expected_total != total:
                raise WavelogError('The Wavelog history changed while loading. Refresh to obtain a complete result.')
            if meta.get('count', len(rows)) != len(rows) or len(rows) > self.settings.page_size:
                raise WavelogError('Wavelog returned an inconsistent page size.')
            expected_total = info['total'] = total
            if not rows and more:
                raise WavelogError('Wavelog returned an empty intermediate page. History is incomplete.')
            for row in rows:
                if received >= limit:
                    raise WavelogError('The configured record limit was reached. Increase the limit in Settings to load complete history.')
                received += 1
                yield row
            if received > total or more != (received < total):
                raise WavelogError('Wavelog pagination did not match its total. History is incomplete.')
            if not more:
                return
        raise WavelogError('The configured page limit was reached. Increase the limit in Settings to load complete history.')

    def qso(self, row, call, stations, ids):
        if not isinstance(row, dict) or text(row.get('call')).strip().upper() != call:
            raise WavelogError('Wavelog returned a record for a different callsign. History is incomplete.')
        qid, sid = positive_id(row.get('id')), positive_id(row.get('station_id'))
        if ids is not None and sid not in ids:
            raise WavelogError('Wavelog returned a record outside the selected scope.')
        if sid not in stations:
            if len(stations) >= 1000:
                raise WavelogError('Too many station locations to resolve safely.')
            stations[sid] = self.station_by_id(sid)
        try:
            date = datetime.fromisoformat(row['qso_date'].replace('Z', '+00:00'))
            date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise WavelogError('A Wavelog contact has an invalid date/time. History is incomplete.') from None
        band, mode = text(row.get('band')).strip(), text(row.get('submode') or row.get('mode')).strip()
        if not band or not mode:
            raise WavelogError('A Wavelog contact is missing band/mode. History is incomplete.')
        fields = {key: text(row.get(key)) for key in ('name', 'qth', 'comment', 'notes', 'freq', 'freq_rx', 'tx_pwr',
            'prop_mode', 'sat_name', 'sat_mode', 'operator', 'state', 'cnty', 'qsl_via', 'sota_ref', 'pota_ref', 'wwff_ref', 'iota') if row.get(key) is not None}
        return dict(id=str(qid), call=call, date=date.isoformat(timespec='microseconds').replace('+00:00', 'Z'), band=band.lower(), mode=mode.upper(),
            sent=text(row.get('rst_sent')), received=text(row.get('rst_rcvd')), station=stations[sid]['callsign'] or f'Station {sid}',
            stationId=sid, stationName=stations[sid]['name'], grid=text(row.get('gridsquare')), confirmed=None, confirmations=[], details=fields)

    def lookup(self, call):
        now = time.time()
        cached = self.cache.get(call)
        if cached and now - cached['updatedAt'] / 1000 < self.settings.cache_minutes * 60:
            self.cache.move_to_end(call)
            return deepcopy(cached) | {'cached': True}
        records, info, label, stations = [], {}, '', {}
        try:
            self.begin()
            ids, label, stations = self.scope()
            params = {'callsign': call}
            if ids is not None:
                params['station_id'] = ','.join(map(str, ids))
            seen = set()
            for row in self.pages('qso', params, info, limit=self.settings.max_records):
                contact = self.qso(row, call, stations, ids)
                if contact['id'] in seen:
                    raise WavelogError('Wavelog repeated a contact across pages. Refresh to obtain complete history.')
                seen.add(contact['id'])
                records.append(contact)
            confirmation_status = 'unavailable'
            if 'confirmation:read' in self.connection['scopes']:
                try:
                    confirmations, unique = {}, set()
                    for row in self.pages('confirmation', params, {}, limit=self.settings.max_records * 5):
                        if not isinstance(row, dict) or text(row.get('callsign')).upper() != call:
                            raise WavelogError('Invalid confirmation response.')
                        qid, kind = str(positive_id(row.get('qso_id'))), text(row.get('type'))
                        if qid not in seen or not kind or (qid, kind) in unique:
                            raise WavelogError('Confirmation data did not match the contact history.')
                        unique.add((qid, kind))
                        confirmations.setdefault(qid, []).append(dict(type=kind, date=text(row.get('confirmation_date'))))
                    for contact in records:
                        contact['confirmations'] = confirmations.get(contact['id'], [])
                        contact['confirmed'] = bool(contact['confirmations'])
                    confirmation_status = 'complete'
                except WavelogError:
                    pass  # QSO completeness and optional confirmation completeness are independent.
            records.sort(key=lambda record: (record['date'], int(record['id'])), reverse=True)
            result = dict(status='loaded' if records else 'empty', call=call, records=records, complete=True, total=len(records),
                scope=label, stations=list(stations.values()), updatedAt=int(now * 1000), cached=False,
                confirmationStatus=confirmation_status, message='' if confirmation_status == 'complete' else 'Confirmation details are unavailable; QSO history is complete.')
            self.cache[call] = deepcopy(result)
            while len(self.cache) > self.settings.cache_limit or sum(len(item['records']) for item in self.cache.values()) > 20000:
                self.cache.popitem(last=False)
            return result
        except Exception as error:
            message = str(error) if isinstance(error, WavelogError) else 'Wavelog history could not be read. Check the connection and retry.'
            self.connection.update(status='error', message=message)
            if not records and cached:
                records = deepcopy(cached['records'])
                message += ' Showing a previously loaded result; current completeness is unknown.'
            return dict(status='incomplete' if records else 'error', call=call, records=records, complete=False,
                total=info.get('total'), scope=label, stations=list(stations.values()), updatedAt=int(now * 1000),
                cached=False, confirmationStatus='unavailable', message=message)

    def test(self):
        self.begin()
        self.connected_at = 0
        self.connection['status'] = 'idle'
        result = self.connect()
        ids, _, _ = self.scope()
        params = {'per_page': 1, 'page': 1}
        if ids is not None:
            params['station_id'] = ','.join(map(str, ids))
        probe = self.get_json('qso', params)
        if not isinstance(probe.get('data'), list) or type(probe.get('meta', {}).get('total')) is not int:
            raise WavelogError('The QSO read capability could not be verified.')
        return deepcopy(result)


class WavelogService:
    def __init__(self, state, settings):
        self.state, self.settings = state, settings
        self.client = WavelogClient(settings)
        self.connection = deepcopy(self.client.connection)
        self.result = dict(status='idle' if settings.enabled else 'disabled', call='', records=[], complete=False)
        self.call = None
        self.generation = 0
        self.event, self.lock = asyncio.Event(), asyncio.Lock()
        self.task = None

    def snapshot(self):
        # Only small metadata travels in frequent radio/SSE snapshots. Contacts are
        # fetched once by lookupId, avoiding a full logbook resend on each Decode.
        return dict(config=self.settings.public(), connection=deepcopy(self.connection),
            result={key: deepcopy(value) for key, value in self.result.items() if key != 'records'} |
                {'recordCount': len(self.result.get('records', []))})

    def history(self, lookup_id):
        if self.result.get('lookupId') != lookup_id:
            raise WavelogError('The focused history has changed. Use the latest dashboard snapshot.')
        return deepcopy(self.result)

    def observe(self):
        call = self.state.call if self.settings.enabled and not self.state.sample and self.state.call else None
        if call == self.call:
            return
        self.call = call
        self.generation += 1
        self.result = dict(status='pending' if call else 'idle' if self.settings.enabled else 'disabled',
            call=call or '', complete=False, records=[])
        self.event.set()

    async def start(self):
        self.task = asyncio.create_task(self.worker())
        self.observe()

    async def worker(self):
        while True:
            await self.event.wait()
            self.event.clear()
            call, token, client = self.call, self.generation, self.client
            if not call:
                continue
            async with self.lock:
                result = await asyncio.to_thread(client.lookup, call)
            if token == self.generation:
                self.result = result | {'lookupId': uuid4().hex}
                self.connection = deepcopy(client.connection)
                self.state.flush()

    def configure(self, settings):
        self.client.cancelled.set()
        self.settings, self.client = settings, WavelogClient(settings)
        self.connection = deepcopy(self.client.connection)
        self.call = None
        self.generation += 1
        self.result = dict(status='idle' if settings.enabled else 'disabled', call='', complete=False, records=[])
        self.observe()
        self.state.flush()

    def refresh(self):
        cached = deepcopy(self.client.cache)
        cached.pop(self.call, None)
        self.configure(self.settings)
        self.client.cache = cached

    async def test(self):
        if self.lock.locked():
            raise WavelogError('A Wavelog lookup is in progress. Try again shortly.')
        client = self.client
        async with self.lock:
            try:
                connection = await asyncio.to_thread(client.test)
            except Exception as error:
                message = str(error) if isinstance(error, WavelogError) else 'Wavelog connection test could not be completed.'
                connection = deepcopy(client.connection) | dict(status='error', message=message)
        if client is self.client:
            self.connection = connection
            self.state.flush()
        return connection

    async def stop(self):
        self.client.cancelled.set()
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
