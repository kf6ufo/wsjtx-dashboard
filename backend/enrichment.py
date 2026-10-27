"""Configurable pyhamtools providers. One background worker, no radio/QSO writes."""
import asyncio
from collections import OrderedDict
from copy import deepcopy
from datetime import date, datetime
import math
import os
from pathlib import Path
import tempfile
import time
from xml.etree import ElementTree as ET

import requests
from pyhamtools import Callinfo, LookupLib
from pyhamtools.frequency import freq_to_band
from pyhamtools.locator import (calculate_distance, calculate_distance_longpath,
    calculate_heading, calculate_heading_longpath, latlong_to_locator)
from .enrichment_config import EnrichmentSettings, update_settings, grid, PROVIDERS
from .private_storage import private_directory


def safe_values(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): safe_values(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_values(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def xml_response(response, content=None):
    response.raise_for_status()
    content = response.content if content is None else content
    if len(content) > 2_000_000 or b'<!DOCTYPE' in content.upper():
        raise ValueError('Invalid QRZ response')
    root = ET.fromstring(content)
    for element in root.iter():
        element.tag = element.tag.split('}')[-1]
    if root.tag != 'QRZDatabase':
        raise ValueError('Invalid QRZ response')
    return root


class QRZLibrary(LookupLib):
    """pyhamtools adapter: HTTPS POST, full fields, no credential-bearing URLs.

    Also avoids the upstream 0.13.2 Python 3 `long(serial)` parser defect.
    Only Callsign fields are retained; session keys never enter results.
    """
    def _post(self, values):
        with requests.post(f'https://xmldata.qrz.com/xml/{self._apiv}/',
            data=values, timeout=(5, 10), allow_redirects=False, stream=True) as response:
            response.raise_for_status()
            if response.is_redirect:
                raise ValueError('Unexpected QRZ redirect')
            chunks, size = [], 0
            deadline = time.monotonic() + 20
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 2_000_000 or time.monotonic() > deadline:
                    raise ValueError('Invalid QRZ response')
                chunks.append(chunk)
            return xml_response(response, b''.join(chunks))

    def _get_qrz_session_key(self, username, pwd):
        root = self._post(dict(username=username, password=pwd, agent='WSJTXDashboard-0.2'))
        self.subscription = root.findtext('Session/SubExp') or ''
        self.notice = root.findtext('Session/Message') or ''
        key = root.findtext('Session/Key')
        if not key:
            raise ValueError('QRZ login failed; check XML username, password and subscription')
        return key

    def _lookup_qrz_callsign(self, callsign=None, apikey=None, apiv='current'):
        for attempt in range(2):
            root = self._post(dict(s=self._apikey, callsign=callsign))
            self.notice = root.findtext('Session/Message') or ''
            self.subscription = root.findtext('Session/SubExp') or self.subscription
            if root.findtext('Session/Key'):
                self._apikey = root.findtext('Session/Key')
            error = root.findtext('Session/Error') or ''
            if 'not found' in error.lower():
                raise KeyError('No QRZ entry')
            if error and attempt == 0 and ('session' in error.lower() or 'key' in error.lower()):
                self._apikey = self._get_qrz_session_key(self._username, self._pwd)
                continue
            if error:
                raise ValueError('QRZ lookup failed; check XML access and subscription')
            calls = root.find('Callsign')
            if calls is None:
                raise ValueError('QRZ returned no callsign data; check XML subscription')
            # Preserve all returned callbook fields; normalize names for get_all users.
            mapping = {'call': 'callsign', 'dxcc': 'adif', 'grid': 'locator', 'lat': 'latitude',
                'lon': 'longitude', 'cqzone': 'cqz', 'ituzone': 'ituz', 'zip': 'zipcode', 'class': 'license_class'}
            result = {mapping.get(node.tag, node.tag): (node.text or '')[:8192] for node in calls if len(node) == 0}
            for key in ('adif', 'cqz', 'ituz', 'latitude', 'longitude'):
                if result.get(key):
                    result[key] = float(result[key]) if key in ('latitude', 'longitude') else int(result[key])
            return result
        raise ValueError('QRZ session could not be renewed')


class FileLibrary(LookupLib):
    def _remove_clublog_xml_header(self, filename):
        # Upstream uses a fixed /tmp/NoHeader_cty.xml name. Keep the
        # intermediate in this lookup's private temporary directory instead.
        path = Path(filename)
        lines = path.read_text().splitlines(keepends=True)
        target = path.with_name('parsed-' + path.name)
        target.write_text('<clublog>\n' + ''.join(lines[1:]))
        return str(target)


class ClubLogAPILibrary(LookupLib):
    def _check_html_response(self, response):
        # Upstream logs the raw response body, which can include a supplied key.
        if response.status_code != 200:
            raise ValueError('Club Log API unavailable')
        return True


class Providers:
    """Serial worker-owned libraries and a bounded, expiring lookup cache."""
    def __init__(self, settings, directory):
        self.settings, self.directory = settings, Path(directory)
        self.libraries, self.cache = {}, OrderedDict()
        self.health = {}
        self.force_refresh = False

    def _download_library(self, source, target):
        url = 'https://www.country-files.com/cty/cty.plist' if source == 'countryfile' else 'https://cdn.clublog.org/cty.php'
        params = {'api': self.settings.clublog_key} if source == 'clublogxml' else None
        private_directory(self.directory)
        pending = None
        try:
            with requests.get(url, params=params, timeout=(5, 10), stream=True, allow_redirects=False) as response:
                response.raise_for_status()
                if response.is_redirect:
                    raise ValueError('Unexpected data-source redirect')
                with tempfile.NamedTemporaryFile(dir=self.directory, delete=False) as output:
                    pending = Path(output.name)
                    size = 0
                    deadline = time.monotonic() + 30
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > 16_000_000 or time.monotonic() > deadline:
                            raise ValueError('Provider download exceeded its size or time limit')
                        output.write(chunk)
            if source == 'clublogxml' and pending.read_bytes()[:2] == b'\x1f\x8b':
                import gzip
                with gzip.open(pending, 'rb') as compressed:
                    content = compressed.read(16_000_001)
                if len(content) > 16_000_000:
                    raise ValueError('Provider data exceeds 16 MB')
                pending.write_bytes(content)
            library = self._load_file(source, pending)
            os.replace(pending, target)
            return library
        finally:
            if pending and pending.exists():
                pending.unlink()

    def _load_file(self, source, path):
        if source != 'clublogxml':
            return LookupLib(lookuptype=source, filename=str(path), apikey=self.settings.clublog_key or None)
        # Upstream strips XML headers into a sibling file. Keep that work away
        # from operator-owned files and clean up its intermediate output.
        import shutil
        private_directory(self.directory)
        with tempfile.TemporaryDirectory(dir=self.directory) as temporary:
            local = Path(temporary) / 'cty.xml'
            shutil.copyfile(path, local)
            return FileLibrary(lookuptype=source, filename=str(local), apikey=self.settings.clublog_key or None)

    def library(self, source):
        now = time.time()
        cached = self.libraries.get(source)
        if cached and now - cached[0] < self.settings.refresh_hours * 3600:
            return cached[1]
        try:
            self.health.pop(source, None)
            if source == 'qrz':
                if not self.settings.qrz_username or not self.settings.qrz_password:
                    raise ValueError('Enter QRZ XML username and password in Settings')
                library = QRZLibrary(lookuptype='qrz', username=self.settings.qrz_username,
                    pwd=self.settings.qrz_password, apiv=self.settings.qrz_version)
            elif source == 'clublogapi':
                if not self.settings.clublog_key:
                    raise ValueError('Enter a Club Log API key in Settings')
                library = ClubLogAPILibrary(lookuptype=source, apikey=self.settings.clublog_key)
            elif self.settings.filename:
                path = Path(self.settings.filename).expanduser()
                if not path.is_absolute():
                    path = self.directory.parent.parent / path
                if path.stat().st_size > 16_000_000:
                    raise ValueError('Provider data exceeds 16 MB')
                library = self._load_file(source, path)
            else:
                target = self.directory / ('countryfile.plist' if source == 'countryfile' else 'clublog.xml')
                if not self.force_refresh and target.exists() and now - target.stat().st_mtime < self.settings.refresh_hours * 3600:
                    library = self._load_file(source, target)
                else:
                    try:
                        library = self._download_library(source, target)
                    except Exception:
                        if not target.exists():
                            raise
                        library = self._load_file(source, target)
                        self.health[source] = dict(status='stale', message='Refresh failed; using the last downloaded data', updatedAt=int(target.stat().st_mtime * 1000))
            self.libraries[source] = (now, library)
            return library
        except Exception:
            if cached:
                self.health[source] = dict(status='stale', message='Refresh failed; using the last loaded data', updatedAt=int(cached[0] * 1000))
                return cached[1]
            raise

    def lookup(self, source, call):
        key, now = (source, call), time.time()
        cached = self.cache.get(key)
        if cached and now - cached[0] < self.settings.cache_minutes * 60:
            self.cache.move_to_end(key)
            return deepcopy(cached[1]) | {'cached': True}
        try:
            library = self.library(source)
            # Callinfo applies prefix/portable exceptions; QRZ preserves every returned field.
            values = safe_values(Callinfo(library).get_all(call))
            item = dict(status='loaded', fields=values, updatedAt=int(now * 1000), cached=False)
            if source == 'qrz':
                item.update(subscription=library.subscription, message=library.notice)
            previous = self.health.get(source, {})
            self.health[source] = previous if previous.get('status') == 'stale' else dict(status='ready', updatedAt=int(now * 1000), message=item.get('message', ''))
            item['dataStatus'] = self.health[source]['status']
            self.cache[key] = (now, deepcopy(item))
            while len(self.cache) > self.settings.cache_limit:
                self.cache.popitem(last=False)
            return item
        except KeyError:
            self.health[source] = dict(status='ready', message='No matching entry for this callsign')
            return dict(status='empty', fields={}, message='No matching entry', updatedAt=int(now * 1000))
        except Exception as error:
            # Never return exception text: request errors can contain secret query strings.
            message = str(error) if isinstance(error, ValueError) and str(error).startswith(('Enter ', 'QRZ ')) else 'Provider unavailable. Check credentials, data file and network connection.'
            for secret in (self.settings.clublog_key, self.settings.qrz_username, self.settings.qrz_password):
                if secret:
                    message = message.replace(secret, '[redacted]')
            self.health[source] = dict(status='error', message=message)
            return dict(status='error', fields={}, message=message, updatedAt=int(now * 1000))

    def enrich(self, context):
        results = {self.settings.source: self.lookup(self.settings.source, context['call'])}
        if self.settings.qrz_enabled and self.settings.source != 'qrz':
            results['qrz'] = self.lookup('qrz', context['call'])
        order = list(results)
        if 'qrz' in order:
            order.remove('qrz')
            order.insert(0 if self.settings.field_priority == 'qrz_first' else len(order), 'qrz')
        values, sources = {}, {}
        for source in order:
            for key, value in results[source]['fields'].items():
                if key not in values and value not in ('', None):
                    values[key], sources[key] = value, PROVIDERS[source]
        reported = context.get('dxGrid', '')
        callbook = values.get('locator', '')
        target, location_source = '', ''
        for candidate, label in ((reported, 'WSJT-X reported operating grid'), (callbook, 'QRZ callbook grid')):
            try:
                if grid(str(candidate)):
                    target, location_source = grid(str(candidate)), label
                    break
            except ValueError:
                pass
        if not target and self.settings.allow_country_estimate and 'latitude' in values and 'longitude' in values and values.get('adif') not in (998, 999):
            try:
                target = latlong_to_locator(values['latitude'], values['longitude'])
                location_source = 'Approximate provider coordinates; not a reported station grid'
            except (ValueError, TypeError):
                pass
        station = self.settings.station_grid or context.get('deGrid', '')
        computed = {}
        try:
            station = grid(station)
            if target and station:
                computed = dict(distanceKm=round(calculate_distance(station, target)),
                    heading=round(calculate_heading(station, target), 1),
                    longPathKm=round(calculate_distance_longpath(station, target)),
                    longPathHeading=round(calculate_heading_longpath(station, target), 1))
        except (ValueError, KeyError, TypeError):
            station = ''
        try:
            if context.get('frequency'):
                computed['frequencyBand'] = safe_values(freq_to_band(context['frequency'] / 1000))
        except KeyError:
            pass
        try:
            computed['homeCall'] = Callinfo.get_homecall(context['call'])
        except ValueError:
            pass
        loaded = any(r['status'] == 'loaded' for r in results.values())
        status = 'loaded' if loaded else 'error' if any(r['status'] == 'error' for r in results.values()) else 'empty'
        return dict(status=status, call=context['call'], fields=values, fieldSources=sources,
            providers=results, computed=computed, reportedGrid=reported, callbookGrid=callbook,
            locationGrid=target, locationSource=location_source, stationGrid=station,
            stationGridSource='Configured station grid' if self.settings.station_grid else 'WSJT-X reported station grid',
            updatedAt=int(time.time() * 1000))


class EnrichmentService:
    def __init__(self, state, settings, directory):
        self.state, self.settings, self.directory = state, settings, directory
        self.providers = Providers(settings, directory)
        self.health = {}
        self.result = dict(status='disabled', call='')
        self.context = None
        self.generation = 0
        self.event = asyncio.Event()
        self.lock = asyncio.Lock()
        self.task = None

    def snapshot(self):
        return dict(config=self.settings.public(), result=deepcopy(self.result), health=deepcopy(self.health))

    def context_now(self):
        if self.state.sample or not self.state.call:
            return None
        entry = next((e for e in self.state.history if e['call'] == self.state.call), {})
        rig = self.state.rigs.get(entry.get('rigId'), {})
        context = {key: entry.get(key, '') for key in ('call', 'dxGrid', 'deGrid', 'frequency')}
        if rig.get('call') == self.state.call:
            for key in ('dxGrid', 'deGrid'):
                context[key] = context[key] or rig.get(key, '')
        return context

    def observe(self):
        context = self.context_now() if self.settings.enabled else None
        if context == self.context:
            return
        self.context = context
        self.generation += 1
        self.result = dict(status='pending' if context else 'idle' if self.settings.enabled else 'disabled', call=context['call'] if context else '')
        self.event.set()

    async def start(self):
        self.task = asyncio.create_task(self.worker())
        self.observe()

    async def worker(self):
        while True:
            await self.event.wait()
            self.event.clear()
            context, token, providers = deepcopy(self.context), self.generation, self.providers
            if context is None:
                continue
            async with self.lock:
                try:
                    result = await asyncio.to_thread(providers.enrich, context)
                except Exception:
                    result = dict(status='error', call=context['call'], message='Enrichment failed; check provider settings.')
            qrz = result.get('providers', {}).get('qrz', {})
            photo_changed = (providers is self.providers and qrz.get('status') == 'loaded'
                and self.state.remember_photo(context['call'], qrz.get('fields', {}).get('image', '')))
            if token == self.generation:
                self.result = result
                self.health = deepcopy(providers.health)
                if photo_changed:
                    self.state.publish()
                else:
                    self.state.flush()
            elif photo_changed:
                self.state.publish()

    def configure(self, settings, *, refresh=False):
        self.settings = settings
        self.providers = Providers(settings, self.directory)
        self.health = {}
        self.providers.force_refresh = refresh
        self.context = None
        self.generation += 1
        self.result = dict(status='idle' if settings.enabled else 'disabled', call='')
        self.observe()
        self.state.flush()

    async def test(self, call):
        if self.lock.locked():
            raise ValueError('A provider lookup is in progress. Try again shortly.')
        providers = self.providers
        async with self.lock:
            result = await asyncio.to_thread(providers.enrich, dict(call=call))
        if providers is self.providers:
            self.health = deepcopy(providers.health)
        self.state.flush()
        return result

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
