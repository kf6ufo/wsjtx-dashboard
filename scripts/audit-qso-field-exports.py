#!/usr/bin/env python3
"""Read-only comparison of local delivery receipts/ADIF with Wavelog exports.

Uses the configured server-side token for GET only. Raw evidence is private,
outside the checkout; stdout contains aggregate field counts, never QSO values.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.config import load_config
from backend.qso_model import adif_records
from backend.qso_fields import WAVELOG_QSO_FIELDS
from backend.qso_delivery import WavelogLogWriter
from backend.wavelog import WavelogClient

# Wavelog 3.2.3 AdifHelper::getAdifLine does not export these accepted fields.
EXPORT_OMISSIONS = frozenset('''ADDRESS_INTL COMMENT_INTL COUNTRY_INTL MY_CITY_INTL
MY_COUNTRY_INTL MY_FISTS MY_IOTA_ISLAND_ID MY_LAT MY_LON MY_NAME MY_NAME_INTL
MY_POSTAL_CODE MY_SIG_INFO_INTL MY_SIG_INTL MY_STREET MY_STREET_INTL MY_USACA_COUNTIES
NAME_INTL NOTES_INTL QTH_INTL RIG_INTL SIG_INFO_INTL SIG_INTL'''.split())


def key(record):
    try: frequency = str(Decimal(record.get('FREQ','0')).normalize())
    except InvalidOperation: frequency = 'unverifiable'
    return tuple(str(record.get(k,'')).upper() for k in ('CALL','QSO_DATE')) + (
        record.get('TIME_ON','').replace(':','').ljust(6,'0'), record.get('BAND','').upper(),
        (record.get('SUBMODE') or record.get('MODE','')).upper(), frequency)


def exported_value_status(field, expected, actual, exported):
    if actual is None or actual == '':
        if field in EXPORT_OMISSIONS: return 'not_exported_by_wavelog'
        if field in ('DISTANCE','HEADING') and Decimal(str(expected)) == 0: return 'zero_omitted_by_wavelog'
        return 'missing_from_export'
    if str(expected) == str(actual): return 'equal'
    if field == 'GRIDSQUARE' and str(actual).upper().startswith(str(expected).upper()) and len(str(actual)) > len(str(expected)):
        return 'grid_refined_in_export'
    if field in ('DISTANCE','HEADING','FREQ','FREQ_RX','TX_PWR','RX_PWR','DXCC','CQZ','ITUZ'):
        try:
            if abs(Decimal(str(expected))-Decimal(str(actual))) <= Decimal('0.001'): return 'numeric_equivalent'
        except InvalidOperation: pass
    if field in ('MODE','SUBMODE') and str(expected).upper() == (exported.get('SUBMODE') or exported.get('MODE','')).upper(): return 'mode_normalized'
    if ' '.join(str(expected).casefold().split()) == ' '.join(str(actual).casefold().split()): return 'text_normalized'
    return 'different_in_export'


def audit(config_path, after_id=0):
    config = load_config(config_path)
    if not config.qso.adif_path: raise ValueError('No configured local ADIF destination to compare.')
    path = Path(config.qso.adif_path)
    before = path.stat()
    with path.open(encoding='utf-8-sig') as stream: local = list(adif_records(stream))
    after = path.stat()
    if (before.st_size,before.st_mtime_ns) != (after.st_size,after.st_mtime_ns):
        raise ValueError('Local ADIF changed during the read; rerun the audit.')
    db = sqlite3.connect((config_path.parent/'data/delivery.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:
        receipts = {ident:(int(remote),json.loads(target)) for ident,remote,target in db.execute(
            "SELECT id,remote_id,target FROM qso_delivery WHERE destination='wavelog' AND status='delivered'") if remote and int(remote)>after_id}
    finally: db.close()
    candidates = [r for r in local if r.get('APP_WSJT_DASHBOARD_ID') in receipts]
    since = min((r['QSO_DATE'] for r in candidates),default=datetime.now().strftime('%Y%m%d'))
    since = datetime.strptime(since,'%Y%m%d').strftime('%Y-%m-%d')
    client = WavelogClient(config.wavelog);client.begin()
    remote, exported, evidence = [], [], []
    for format in ('json','adif'):
        for page in range(1,101):
            response = client.get_json('qso',dict(format=format,per_page=100,page=page,qso_since=since))
            evidence.append(dict(format=format,page=page,response=response))
            if format=='json': remote.extend(response['data'])
            elif response['data'].get('adif'): exported.extend(adif_records(io.StringIO(response['data']['adif'])))
            if response.get('meta',{}).get('has_more') is False: break
        else: raise ValueError('Export exceeded the audit limit; no completeness claim can be made.')
    by_id = {int(r['id']):r for r in remote}
    by_key = defaultdict(list)
    for record in exported: by_key[key(record)].append(record)
    counts, outcomes, details = defaultdict(Counter), Counter(), []
    for original in candidates:
        remote_id, target = receipts[original['APP_WSJT_DASHBOARD_ID']]
        if target.get('url') != config.wavelog.url:
            outcomes['delivery_destination_changed'] += 1; continue
        row = by_id.get(remote_id)
        if not row or row.get('station_id') != target.get('station_id'):
            outcomes['receipt_not_in_export_scope'] += 1; continue
        dt = datetime.fromisoformat(row['qso_date'].replace('Z','+00:00'))
        remote_record = dict(CALL=row['call'],QSO_DATE=dt.strftime('%Y%m%d'),TIME_ON=dt.strftime('%H%M%S'),
            BAND=row['band'],MODE=row.get('submode') or row['mode'],FREQ=str(Decimal(str(row.get('freq') or 0))/1_000_000))
        if key(original) != key(remote_record): outcomes['receipt_identity_differs'] += 1; continue
        matches = [r for r in by_key[key(original)] if r.get('STATION_CALLSIGN','').upper()==original.get('STATION_CALLSIGN','').upper()]
        if len(matches) != 1: outcomes['export_identity_not_unique'] += 1; continue
        record = matches[0]
        payload = WavelogLogWriter(config.wavelog,target['station_id'],original.get('STATION_CALLSIGN','')).payload(original)
        expected = {k:v for k,v in original.items() if k in WAVELOG_QSO_FIELDS}
        for calculated in ('DISTANCE','HEADING'):
            if calculated.lower() in payload: expected[calculated] = payload[calculated.lower()]
        comparison = {}
        for field,value in expected.items():
            status = exported_value_status(field,value,record.get(field),record)
            counts[field][status] += 1; comparison[field] = status
        outcomes['verified_receipt_and_unique_export_identity'] += 1
        details.append(dict(receipt=original['APP_WSJT_DASHBOARD_ID'],remote_id=remote_id,expected_payload=payload,export=record,comparison=comparison))
    summary = dict(local_records=len(local),eligible_delivered_receipts=len(candidates),
        export_records=len(exported),after_id=after_id,outcomes=dict(outcomes),fields={k:dict(v) for k,v in sorted(counts.items())},
        note='Expected submission is reconstructed with the current adapter from local ADIF; old records may predate it or have subsequent Wavelog edits. Export differences are reported, never repaired.')
    os.umask(0o077)
    directory = Path(tempfile.mkdtemp(prefix='wsjtx-field-export-audit-'))
    (directory/'evidence.json').write_text(json.dumps(dict(local=local,api=evidence,verified=details)))
    (directory/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(dict(summary=summary,private_evidence=str(directory)),indent=2))
    return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--after-id',type=int,default=0,help='Only compare delivered receipts above this Wavelog QSO ID.')
    args=parser.parse_args()
    try: audit(args.config.resolve(),args.after_id)
    except Exception:
        # Do not echo requests, tokens, response bodies or private QSO values.
        print('Audit could not complete; check configuration, read permissions and complete ADIF/export availability.',file=sys.stderr)
        sys.exit(1)
