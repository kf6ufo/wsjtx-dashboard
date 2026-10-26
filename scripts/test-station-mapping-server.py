"""Offline mapping/recovery browser fixture; never joins station multicast."""
from pathlib import Path
import subprocess
import sys
import tempfile
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from backend.config import save_qso_config, save_wavelog_config
from backend.qso_config import QsoSettings
from backend.wavelog_config import WavelogSettings

with tempfile.TemporaryDirectory(prefix='wsjtx-mapping-browser-') as directory:
    data=Path(directory);config=data/'config.toml'
    config.write_text((root/'config.example.toml').read_text().replace('port = 8787','port = 8798').replace('enabled = false','enabled = true',1).replace('group = "239.255.0.73"','group = ""').replace('listen = "0.0.0.0"','listen = "127.0.0.1"').replace('port = 2238','port = 18244'))
    save_qso_config(config,QsoSettings(adif_path=str(data/'fixture.adi')))
    save_wavelog_config(config,WavelogSettings(url='http://mapping-fixture.invalid',token='wl2_fixture'))
    launcher='''
import json
from backend.wavelog import WavelogClient
from backend.qso_delivery import QsoDeliveryService, ADIFLogWriter
stations=[dict(id=1,callsign='KF6UFO',name='Home',active=True),dict(id=2,callsign='KF0TKE',name='Legacy',active=False)]
def get_json(self,resource,params=None,**kwargs):
    if resource=='status':return dict(data=dict(status='ok'))
    if resource=='token':return dict(data=dict(scopes=['qso:read','station:read']))
    if resource=='station':return dict(data=stations)
    if resource.startswith('station/'):return dict(data=stations[int(resource.split('/')[1])-1])
    params=params or {}
    rows=[dict(id=44,call='K1MATCH',station_id=1,qso_date='2026-10-26 18:51:00',band='15m',mode='FT8',freq=21074000)] if params.get('callsign','K1MATCH')=='K1MATCH' else []
    return dict(data=rows,meta=dict(total=len(rows),page=1,count=len(rows),has_more=False))
WavelogClient.get_json=get_json
import requests
def no_post(*args,**kwargs):raise AssertionError('Fixture forbids Wavelog submissions')
requests.post=no_post
original_start=QsoDeliveryService.start
async def start(self):
    for call,time in [('K1MATCH','185100'),('K2MISS','184730')]:
        f=dict(CALL=call,QSO_DATE='20261026',TIME_ON=time,BAND='15m',MODE='FT8',FREQ='21.074',STATION_CALLSIGN='KF6UFO')
        key=self.queue.capture('Rig A',f,{},dict(adif=dict(path=self.settings.adif_path),wavelog=dict(url=self.wavelog.settings.url,station_id=0)))
        ADIFLogWriter(self.settings.adif_path,self.queue).write(key,f)
        self.queue.delivered(key,'adif','Fixture ADIF receipt')
        self.queue.execute("UPDATE qso_outbox SET normalized=?,status='ready' WHERE id=?",(json.dumps(f),key))
        self.queue.execute("UPDATE qso_delivery SET status='error' WHERE id=? AND destination='wavelog'",(key,))
    await original_start(self)
QsoDeliveryService.start=start
from backend.server import main
raise SystemExit(main())
'''
    child=subprocess.Popen([sys.executable,'-c',launcher,'--config',str(config)],cwd=root)
    try:sys.exit(child.wait())
    finally:
        if child.poll() is None:child.terminate();child.wait(timeout=15)
