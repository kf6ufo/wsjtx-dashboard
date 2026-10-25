"""Installed server, real loopback UDP and an offline Wavelog API fixture."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from backend.config import save_wavelog_config
from backend.wavelog_config import WavelogSettings

with tempfile.TemporaryDirectory(prefix='wsjtx-wavelog-browser-') as directory:
    config = Path(directory) / 'config.toml'
    source = (root / 'config.example.toml').read_text().replace('port = 8787', 'port = 8794').replace('enabled = false', 'enabled = true', 1).replace('group = "239.255.0.73"', 'group = ""').replace('listen = "0.0.0.0"', 'listen = "127.0.0.1"').replace('port = 2238', 'port = 18240')
    config.write_text(source)
    save_wavelog_config(config, WavelogSettings(enabled=True, url='http://wavelog-fixture.invalid', token='wl2_browser-fixture'))
    launcher = """
from datetime import datetime, timedelta
import time
from backend.wavelog import WavelogClient, WavelogError
stations = [dict(id=1, name='Fixture current station', callsign='KF6UFO', gridsquare='DM57', active=True), dict(id=2, name='Fixture previous station', callsign='KF0TKE', gridsquare='DM57', active=False)]
book = dict(id=7, name='Fixture combined logbook', station_ids=[1,2], active=True)
def get_json(self, resource, params=None, **kwargs):
    params = params or {}
    if resource == 'status': return dict(data=dict(status='ok', name='Wavelog API'))
    if resource == 'token': return dict(data=dict(owner='KF6UFO', scopes=['qso:read','station:read','logbook:read','confirmation:read']))
    if resource == 'station': return dict(data=stations)
    if resource.startswith('station/'): return dict(data=stations[int(resource.split('/')[1])-1])
    if resource == 'logbook': return dict(data=[book])
    if resource == 'logbook/7': return dict(data=book)
    call, page, size = params.get('callsign','K1MNY'), params.get('page',1), params.get('per_page',100)
    if call == 'K4SLO' and page == 1: time.sleep(.8)
    if call == 'K3ERR' and resource == 'qso' and page == 2: raise WavelogError('Fixture later-page failure. History is incomplete.')
    count = 0 if call == 'K2NEW' else 213
    if resource == 'confirmation':
        rows = [] if not count else [dict(qso_id=1, callsign=call, type=kind, confirmation_date='2026-10-01') for kind in ('LoTW', 'QRZ')]
        if params.get('station_id') == '2': rows=[]
    else:
        rows=[dict(id=i, call=call, station_id=1 if i%2 else 2, band='20m' if i%2 else '40m', mode='MFSK', submode='FT8', qso_date=(datetime(2024,1,1)+timedelta(days=i)).isoformat(' '), rst_sent='-07', rst_rcvd='-10', gridsquare='FN31', freq=14074000, comment='Offline fixture '+call) for i in range(1,count+1)]
        if params.get('station_id'): rows=[row for row in rows if row['station_id'] in map(int,params['station_id'].split(','))]
    total=len(rows);data=rows[(page-1)*size:page*size]
    return dict(data=data, meta=dict(total=total, page=page, count=len(data), per_page=size, has_more=page*size<total))
WavelogClient.get_json=get_json
from backend.server import main
raise SystemExit(main())
"""
    child = subprocess.Popen([sys.executable, '-c', launcher, '--config', str(config)], cwd=root)
    try:
        sys.exit(child.wait())
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=15)
