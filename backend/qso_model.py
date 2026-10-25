"""Length-aware completeness checks around adif-io, and destination-neutral QSOs."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import re
import adif_io
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


def adif_text(fields):
    return adif_io.qso_to_adif(adif_io.qso_from_dict(fields)) + '\n'


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
    qrz = providers.get('qrz', {}).get('fields', {})
    # Only station-specific QRZ information may supply these fields.
    county = str(qrz.get('county') or '')
    if county and ',' not in county:
        county = f"{qrz['state']},{county}" if str(qrz.get('adif')) == '291' and qrz.get('state') else ''
    station = {'NAME': qrz.get('name_fmt') or ' '.join(str(qrz.get(k, '')) for k in ('fname', 'name')).strip(),
        'QTH': qrz.get('addr2'), 'GRIDSQUARE': qrz.get('locator'), 'STATE': qrz.get('state'), 'CNTY': county}
    common = {'DXCC': 'adif', 'COUNTRY': 'country', 'CQZ': 'cqz', 'ITUZ': 'ituz', 'CONT': 'continent'}
    for key, value in station.items():
        if not result.get(key) and value not in (None, ''): result[key] = str(value); sources[key] = 'QRZ XML'
    for key, name in common.items():
        value = qrz.get(name, fields.get(name))
        if not result.get(key) and value not in (None, ''): result[key] = str(value); sources[key] = enrichment.get('fieldSources', {}).get(name, 'Callsign enrichment')
    return result, sources
