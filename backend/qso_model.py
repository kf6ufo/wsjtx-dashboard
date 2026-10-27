"""Length-aware completeness checks around adif-io, and destination-neutral QSOs."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import re
import unicodedata
from functools import lru_cache
from copy import deepcopy
import adif_io
from urllib.parse import urlsplit
from .qso_fields import (adif_coordinate, destination_fields, number, qso_distance,
    valid_grid, locator_to_latlong)
from .enrichment_config import PROVIDERS
from .state import normalize_call
from .protocol import band_from_hz


class QsoError(ValueError): pass


def adif_records(stream):
    """Stream framing is strict: the library alone silently ignores damaged tails.

    Values are consumed by declared character length, so embedded <EOR> text
    cannot split a record. The existing library handles actual field decoding.
    """
    fields, seen, prologue = [], set(), ''
    header_done, records_seen = False, False
    while True:
        char = stream.read(1)
        if not char:
            if fields: raise QsoError('Unfinished ADIF record; history is incomplete')
            if prologue.strip(): raise QsoError('ADIF header is missing EOH')
            return
        if char != '<':
            if not char.isspace():
                if fields: raise QsoError('Unexpected text between ADIF fields')
                prologue += char
                if len(prologue) > 65536: raise QsoError('ADIF header exceeds safety limit')
            continue
        tag = ''
        while not tag.endswith('>'):
            c = stream.read(1)
            if not c or len(tag) > 128: raise QsoError('Malformed ADIF tag')
            tag += c
        name = tag[:-1].upper()
        if name == 'EOH':
            if header_done or records_seen or 'CALL' in seen: raise QsoError('Unexpected ADIF header')
            header_done = True
            fields, seen, prologue = [], set(), ''
            continue
        if name == 'EOR':
            if prologue or (not header_done and seen & {'ADIF_VER', 'PROGRAMID'}): raise QsoError('ADIF header is missing EOH')
            if not fields: raise QsoError('Empty ADIF record')
            try:
                rows, _ = adif_io.read_from_string(''.join(fields) + '<EOR>')
                if len(rows) != 1: raise ValueError()
                records_seen = True
                yield dict(rows[0])
            except Exception: raise QsoError('ADIF record could not be decoded') from None
            fields, seen = [], set()
            continue
        match = re.fullmatch(r'([A-Z][A-Z0-9_]*):(\d+)(?::[A-Z])?', name)
        if not match: raise QsoError('Malformed ADIF field')
        key, length = match[1], int(match[2])
        if length > 65536 or key in seen: raise QsoError('Oversized or duplicate ADIF field')
        value = stream.read(length)
        if len(value) != length: raise QsoError('Truncated ADIF field')
        seen.add(key); fields.append('<' + tag + value)
        if sum(map(len, fields)) > 131072: raise QsoError('ADIF record exceeds safety limit')


def parse_completed(raw):
    rows = list(adif_records(io.StringIO(raw)))
    if len(rows) != 1: raise QsoError('A Logged ADIF event must contain one completed QSO')
    return normalize_qso(rows[0])


@lru_cache(maxsize=128)
def _completed_fields(raw):
    return parse_completed(raw)


def completed_fields(packet):
    """One bounded normalization cache shared by observation, delivery and routing."""
    return deepcopy(_completed_fields(packet.fields['adif']))


async def enriched_completed(original, profile, enrichment):
    """Use the same provider lock and missing-only rules for every QSO output."""
    import asyncio
    result = {}
    if enrichment.settings.enabled:
        try:
            async with enrichment.lock:
                result = await asyncio.to_thread(enrichment.providers.enrich, {'call': original['CALL'], 'dxGrid': original.get('GRIDSQUARE', ''), 'deGrid': original.get('MY_GRIDSQUARE', '')})
        except Exception: pass
    return enrich_qso(original, profile, result)


def normalize_qso(fields):
    values = {str(k).upper(): str(v).strip() for k, v in fields.items() if str(v).strip()}
    call = normalize_call(values.get('CALL', ''))
    if not call: raise QsoError('QSO callsign is missing or invalid')
    values['CALL'] = call
    try:
        time = values['TIME_ON']
        if not re.fullmatch(r'\d{4}(?:\d{2})?', time): raise ValueError()
        values['TIME_ON'] = time.ljust(6, '0')
        datetime.strptime(values['QSO_DATE'] + values['TIME_ON'], '%Y%m%d%H%M%S')
        if not re.fullmatch(r'\d{8}', values['QSO_DATE']): raise ValueError()
    except (KeyError, ValueError): raise QsoError('QSO date/time is missing or invalid') from None
    if not values.get('MODE'): raise QsoError('QSO mode is missing')
    values['MODE'] = values['MODE'].upper()
    if values.get('SUBMODE'): values['SUBMODE'] = values['SUBMODE'].upper()
    if values.get('FREQ'):
        try:
            frequency = Decimal(values['FREQ'])
            if not frequency.is_finite() or frequency <= 0: raise ValueError()
            values.setdefault('BAND', band_from_hz(int(frequency * 1_000_000)) or '')
        except (InvalidOperation, ValueError, OverflowError): raise QsoError('Invalid QSO frequency') from None
    if not values.get('BAND'): raise QsoError('QSO band is missing or outside the known band plan')
    values['BAND'] = values['BAND'].lower()
    return values


def identity(fields):
    frequency = fields.get('FREQ', '')
    try:
        if frequency: frequency = format(Decimal(frequency).normalize(), 'f')
    except InvalidOperation: pass
    values = [fields.get('CALL',''), fields.get('QSO_DATE',''), fields.get('TIME_ON','').ljust(6,'0'), fields.get('BAND',''), fields.get('SUBMODE') or fields.get('MODE',''), frequency, fields.get('STATION_CALLSIGN','')]
    return hashlib.sha256(json.dumps([v.upper() for v in values], separators=(',', ':')).encode()).hexdigest()


def observed_identity(fields, rig):
    """Deduplicate an explicit contact across rigs; keep unknown stations separate."""
    key = identity(fields)
    return key if fields.get('STATION_CALLSIGN') else hashlib.sha256((rig + ':' + key).encode()).hexdigest()


def adif_text(fields):
    return adif_io.qso_to_adif(adif_io.qso_from_dict(destination_fields(fields, 'adif'))) + '\n'


def history_record(fields, number):
    f = normalize_qso(fields)
    date = datetime.strptime(f['QSO_DATE'] + f['TIME_ON'], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    confirmations = [dict(type=kind, date='') for key, kind in (('LOTW_QSL_RCVD', 'LoTW'), ('QSL_RCVD', 'QSL'), ('EQSL_QSL_RCVD', 'eQSL'), ('QRZCOM_QSO_DOWNLOAD_STATUS', 'QRZ')) if f.get(key, '').upper() == 'Y']
    known = any(key in f for key in ('LOTW_QSL_RCVD', 'QSL_RCVD', 'EQSL_QSL_RCVD'))
    details = {k.lower(): v for k, v in f.items() if k in ('NAME', 'QTH', 'COMMENT', 'NOTES', 'FREQ', 'FREQ_RX', 'TX_PWR', 'OPERATOR', 'STATE', 'CNTY', 'PROP_MODE', 'SAT_NAME')}
    for key in ('freq', 'freq_rx'):
        if key in details:
            try: details[key] = str(int(Decimal(details[key]) * 1_000_000))
            except (InvalidOperation, ValueError, OverflowError): details.pop(key)
    return dict(id='adif-' + str(number), call=f['CALL'], date=date.isoformat().replace('+00:00', 'Z'), band=f['BAND'], mode=f.get('SUBMODE') or f['MODE'],
        sent=f.get('RST_SENT', ''), received=f.get('RST_RCVD', ''), station=f.get('STATION_CALLSIGN') or f.get('OPERATOR') or 'Unknown station',
        stationName='Local ADIF', grid=f.get('GRIDSQUARE', ''), confirmed=bool(confirmations) if known else None, confirmations=confirmations,
        details=details)


def enrich_qso(original, profile, enrichment):
    """Only fill absent fields. Country predictions never supply a QSO grid/address."""
    result = dict(original)
    sources = {key: 'WSJT-X' for key in result}
    for key, name in (('STATION_CALLSIGN', 'station_callsign'), ('OPERATOR', 'operator'), ('TX_PWR', 'tx_power')):
        if not result.get(key) and profile.get(name): result[key] = profile[name]; sources[key] = 'Station configuration'
    fields, providers = enrichment.get('fields', {}), enrichment.get('providers', {})
    qrz_provider = providers.get('qrz', {})
    qrz = qrz_provider.get('fields', {}) if qrz_provider.get('status', 'loaded') == 'loaded' else {}
    def text(value):
        return value.strip() if isinstance(value, str) else ''
    def put(key, value, source):
        if not result.get(key) and isinstance(value, (str, int, float)) and not isinstance(value, bool) and str(value).strip():
            result[key], sources[key] = str(value).strip(), source

    reported, home = valid_grid(original.get('GRIDSQUARE')), valid_grid(qrz.get('locator'))
    conflict = bool(reported and home and not (reported.startswith(home) or home.startswith(reported)))
    precise = text(qrz.get('geoloc')).lower() not in ('zip', 'state', 'dxcc', 'none')
    location = qrz if not conflict and precise else {}
    # Only station-specific QRZ information may supply these fields.
    county = text(location.get('county'))
    if county and ',' not in county:
        county = f"{location['state']},{county}" if str(location.get('adif')) == '291' and text(location.get('state')) else ''
    station = {'NAME': text(qrz.get('name_fmt')) or ' '.join(filter(None, (text(qrz.get(k)) for k in ('fname', 'name')))),
        'QTH': text(location.get('addr2')), 'GRIDSQUARE': home if location else '',
        'STATE': text(location.get('state')), 'CNTY': county, 'QSL_VIA': text(qrz.get('qslmgr'))}
    email, web, iota = text(qrz.get('email')), text(qrz.get('url')), text(location.get('iota')).upper()
    if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email): station['EMAIL'] = email
    try:
        parsed = urlsplit(web)
        if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password: station['WEB'] = web
    except ValueError: pass
    if re.fullmatch(r'(?:AF|AN|AS|EU|NA|OC|SA)-\d{3}', iota): station['IOTA'] = iota
    if text(qrz.get('addr1')):
        city = ', '.join(filter(None, (text(qrz.get('addr2')), text(qrz.get('state')))))
        city = ' '.join(filter(None, (city, text(qrz.get('zipcode')))))
        station['ADDRESS'] = '\n'.join(filter(None, (text(qrz.get('attn')), text(qrz.get('addr1')), city, text(qrz.get('country')))))
    common = {'DXCC': 'adif', 'COUNTRY': 'country', 'CQZ': 'cqz', 'ITUZ': 'ituz', 'CONT': 'continent', 'PFX': 'prefix'}
    for key, value in station.items():
        if key in ('NAME', 'QTH', 'ADDRESS'):
            if original.get(key) or original.get(key + '_INTL'): continue
            if isinstance(value, str) and not value.isascii():
                put(key + '_INTL', value, 'QRZ XML')
                transcription = ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))
                value = transcription if transcription.isascii() else ''
        put(key, value, 'QRZ XML')
    for key, name in common.items():
        candidates = []
        if not conflict and precise and str(qrz.get('adif')) not in ('998','999'): candidates.append((qrz.get(name), 'QRZ XML'))
        for provider, data in providers.items():
            if provider != 'qrz' and data.get('status', 'loaded') == 'loaded' and str(data.get('fields', {}).get('adif')) not in ('998','999'):
                candidates.append((data.get('fields', {}).get(name), PROVIDERS.get(provider, 'Callsign enrichment')))
        if not providers and str(fields.get('adif')) not in ('998','999'): candidates.append((fields.get(name), enrichment.get('fieldSources', {}).get(name, 'Callsign enrichment')))
        for value, source in candidates:
            if key in ('DXCC', 'CQZ', 'ITUZ'):
                limit = {'DXCC': 522, 'CQZ': 40, 'ITUZ': 90}[key]
                parsed = number(value, 1, limit)
                value = str(int(parsed)) if parsed is not None and parsed.is_integer() else ''
            elif key == 'CONT': value = text(value).upper() if text(value).upper() in ('AF','AN','AS','EU','NA','OC','SA') else ''
            elif key == 'PFX': value = text(value).upper() if re.fullmatch(r'[A-Za-z0-9/]{1,16}', text(value)) else ''
            else: value = text(value) if text(value).lower() not in ('unknown','n/a','none','invalid') else ''
            if value not in ('', None):
                if key == 'COUNTRY' and not result.get(key) and not original.get('COUNTRY_INTL') and not value.isascii():
                    put('COUNTRY_INTL', value, source)
                    transcription = ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))
                    value = transcription if transcription.isascii() else ''
                if key != 'COUNTRY' or not original.get('COUNTRY_INTL'): put(key, value, source)
                break

    # Use the completed contact's grids, never a display estimate or another rig's focus.
    put('MY_GRIDSQUARE', valid_grid(enrichment.get('stationGrid')), enrichment.get('stationGridSource', 'Configured station grid'))
    for prefix, grid_key in (('', 'GRIDSQUARE'), ('MY_', 'MY_GRIDSQUARE')):
        if result.get(prefix + 'LAT') or result.get(prefix + 'LON'): continue
        locator = valid_grid(result.get(grid_key))
        coords, source = None, 'Grid centre (' + grid_key + ')'
        if locator: coords = locator_to_latlong(locator)
        if not prefix and location:
            lat, lon = number(qrz.get('latitude'), -90, 90), number(qrz.get('longitude'), -180, 180)
            if lat is not None and lon is not None and text(qrz.get('geoloc')).lower() in ('user','geocode','grid'):
                # QRZ coordinates must agree with the chosen grid, not just its home grid.
                from pyhamtools.locator import latlong_to_locator
                try: compatible = not locator or latlong_to_locator(lat, lon, precision=len(locator)).upper() == locator.upper()
                except ValueError: compatible = False
                if compatible: coords, source = (lat, lon), 'QRZ XML'
        if coords:
            put(prefix + 'LAT', adif_coordinate(coords[0], True), source)
            put(prefix + 'LON', adif_coordinate(coords[1], False), source)
    if not result.get('DISTANCE'):
        distance = qso_distance(result)
        if distance is not None: put('DISTANCE', str(distance), 'Great-circle distance from QSO grids')
    return result, sources
