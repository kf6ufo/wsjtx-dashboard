"""Station mapping and read-only external resolution. All Wavelog reads are fixtures."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import threading
from types import SimpleNamespace
import pytest
from backend.station_mapping import resolve_station
from backend.qso_model import QsoError
from backend.qso_config import QsoSettings
from backend.qso_delivery import QsoDeliveryService, DeliveryError, WavelogLogWriter, ADIFLogWriter
from backend.wavelog import WavelogService, WavelogClient
from backend.wavelog_config import WavelogSettings
from backend.qso_history import QsoHistoryService
from backend.workspace import WorkspaceState
from backend.protocol import parse_packet
from .test_qso_architecture import fields, logged, wait_for

STATIONS = [dict(id=1,callsign='KF6UFO',name='Home'),dict(id=2,callsign='KF0TKE',name='Legacy')]


@pytest.fixture
def read_api(monkeypatch):
    data = dict(stations=deepcopy(STATIONS), records=[dict(id='77',call='K1ABC',date='2026-10-24T12:00:00.000000Z',station='KF6UFO',stationId=1,band='20m',mode='FT8',details=dict(freq='14074000'))], complete=True)
    monkeypatch.setattr(WavelogClient,'connect',lambda self: dict(status='ready',stations=data['stations'],scopes=['qso:read','station:read']))
    monkeypatch.setattr(WavelogClient,'station_by_id',lambda self,sid: next(s for s in data['stations'] if s['id']==sid))
    monkeypatch.setattr(WavelogClient,'lookup',lambda self,call: dict(complete=data['complete'],records=deepcopy(data['records'])))
    monkeypatch.setattr('backend.qso_delivery.requests.post',lambda *a,**k: (_ for _ in ()).throw(AssertionError('No live or unintended fixture POST')))
    return data


def service_at(tmp_path, enabled=False, profiles=None):
    state=WorkspaceState(tmp_path/'workspace.sqlite3'); state.enter_radio_workspace()
    wl=WavelogService(state,WavelogSettings(url='http://wavelog.invalid',token='wl2_fixture'))
    wl.connection=dict(status='ready',stations=deepcopy(STATIONS))
    config=QsoSettings(logging_enabled=enabled,log_to_wavelog=enabled,adif_path=str(tmp_path/'local.adi'),rigs=profiles or [])
    history=QsoHistoryService(state,config,wl)
    service=QsoDeliveryService(state,config,wl,SimpleNamespace(settings=SimpleNamespace(enabled=False)),tmp_path/'delivery.sqlite3',history)
    return state,service


def seed_legacy(service, values=None, station_id=0):
    values=values or fields()
    key=service.queue.capture('Rig A',values,{},dict(adif=dict(path=service.settings.adif_path),wavelog=dict(url=service.wavelog.settings.url,station_id=station_id)))
    ADIFLogWriter(service.settings.adif_path,service.queue).write(key,values)
    service.queue.delivered(key,'adif','existing ADIF receipt')
    service.queue.execute("UPDATE qso_outbox SET normalized=?,status='ready' WHERE id=?",(json.dumps(values),key))
    service.queue.execute("UPDATE qso_delivery SET status='error' WHERE id=? AND destination='wavelog'",(key,))
    return key


def test_exact_unique_callsigns_and_explicit_override():
    assert resolve_station(fields(),{},STATIONS)[0]['id']==1
    assert resolve_station(fields(station='KF0TKE'),{},STATIONS)[0]['id']==2
    duplicate=STATIONS+[dict(id=3,callsign='KF6UFO',name='Portable')]
    with pytest.raises(QsoError,match='Multiple'): resolve_station(fields(),{},duplicate)
    assert resolve_station(fields(),dict(wavelog_station_id=3),duplicate)[0]['id']==3
    for profile in [dict(wavelog_station_id=2),dict(wavelog_station_id=999)]:
        with pytest.raises(QsoError): resolve_station(fields(),profile,STATIONS)
    with pytest.raises(QsoError,match='No authorized'): resolve_station(fields(station='N0OTHER'),{},STATIONS)
    with pytest.raises(QsoError,match='missing'): resolve_station({}, {}, STATIONS)


def test_both_rigs_auto_resolve_and_frozen_target_survives_restart(tmp_path,read_api,monkeypatch):
    async def run():
        state,s=service_at(tmp_path,True)
        writes=[]
        def prepare(self,values,uncertain=False):
            frozen=json.loads(s.queue.execute("SELECT target FROM qso_delivery WHERE id IN (SELECT id FROM qso_outbox WHERE normalized=?) AND destination='wavelog'",(json.dumps(values),))[0][0])
            assert frozen['station_id']==1
            writes.append((self.station_id,values['STATION_CALLSIGN']))
            return '77'
        monkeypatch.setattr(WavelogLogWriter,'prepare',prepare)
        for rig in ['IC7300','IC9100']: state.rigs[rig]=dict(stationCall='KF6UFO')
        assert [r['stationId'] for r in s.associations()]==[1,1]
        await s.start()
        for i,rig in enumerate(state.rigs):s.capture(parse_packet(logged('K1ABC',rig=rig,TIME_ON=f'12000{i}')))
        await wait_for(lambda:s.queue.summary()['jobs'].get('delivered')==2)
        assert writes==[(1,'KF6UFO'),(1,'KF6UFO')]
        await s.stop()
        restored_state,restored=service_at(tmp_path)
        assert all(json.loads(r[0])['station_id']==1 for r in restored.queue.execute("SELECT target FROM qso_delivery WHERE destination='wavelog'"))
        restored.queue.close();restored_state.close();state.close()
    asyncio.run(run())


def test_status_identity_fallback_is_captured_and_adif_identity_wins(tmp_path,read_api,monkeypatch):
    async def run():
        state,s=service_at(tmp_path,True);state.rigs['Rig A']=dict(stationCall='KF6UFO')
        seen=[];monkeypatch.setattr(WavelogLogWriter,'prepare',lambda self,f,uncertain=False: seen.append((self.station_id,f['STATION_CALLSIGN'])) or '77')
        s.capture(parse_packet(logged(rig='Rig A',station='')))
        state.rigs['Rig A']['stationCall']='KF0TKE' # Does not rewrite captured identity.
        await s.start();await wait_for(lambda:s.queue.summary()['jobs'].get('delivered')==1)
        s.capture(parse_packet(logged('K2ABC',rig='Rig A',station='KF6UFO')))
        await wait_for(lambda:s.queue.summary()['jobs'].get('delivered')==2)
        assert seen==[(1,'KF6UFO'),(1,'KF6UFO')]
        await s.stop();state.close()
    asyncio.run(run())


def test_ambiguous_new_job_waits_for_override_and_missing_legacy_never_posts(tmp_path,read_api,monkeypatch):
    async def run():
        read_api['stations'].append(dict(id=3,callsign='KF6UFO',name='Portable'))
        state,s=service_at(tmp_path,True);posted=[]
        monkeypatch.setattr(WavelogLogWriter,'prepare',lambda self,f,uncertain=False: posted.append(self.station_id) or '77')
        await s.start();s.capture(parse_packet(logged(rig='Rig A')))
        await wait_for(lambda:bool(s.queue.execute("SELECT 1 FROM qso_delivery WHERE destination='wavelog' AND status='error'")))
        assert posted==[]
        profile=dict(id='Rig A',station_callsign='',operator='',tx_power='',wavelog_station_id=3)
        s.settings=replace(s.settings,rigs=[profile]);s.retry()
        await wait_for(lambda:s.queue.summary()['jobs'].get('delivered')==1)
        assert posted==[3]
        legacy=seed_legacy(s,fields('K3ABC'))
        s.retry();await wait_for(lambda:s.queue.execute("SELECT attempts FROM qso_delivery WHERE id=? AND destination='wavelog'",(legacy,))[0][0]>0)
        assert posted==[3]
        await s.stop();state.close()
    asyncio.run(run())


def test_external_resolution_is_read_only_exact_and_preserves_adif_receipts(tmp_path,read_api):
    async def run():
        state,s=service_at(tmp_path);key=seed_legacy(s)
        before=s.queue.execute("SELECT * FROM qso_delivery WHERE destination='adif'");file_before=__import__('pathlib').Path(s.settings.adif_path).read_bytes()
        await s.resolve_external(key,1)
        assert s.queue.execute("SELECT status,remote_id FROM qso_delivery WHERE destination='wavelog'")==[('resolved_external','77')]
        assert s.queue.execute("SELECT * FROM qso_delivery WHERE destination='adif'")==before
        assert __import__('pathlib').Path(s.settings.adif_path).read_bytes()==file_before
        assert s.queue.execute('SELECT id,original,normalized FROM qso_outbox')==[(key,'{}',None)]
        await s.resolve_external(key,1) # Idempotent; dedupe receipt remains.
        s.queue.close();state.close()
    asyncio.run(run())


def test_resolving_locks_out_the_worker_and_survives_restart(tmp_path,read_api,monkeypatch):
    async def run():
        state,s=service_at(tmp_path,True);key=seed_legacy(s,station_id=1)
        entered,release=threading.Event(),threading.Event()
        def lookup(self,call):
            entered.set(); assert release.wait(3)
            return dict(complete=True,records=read_api['records'])
        monkeypatch.setattr(WavelogClient,'lookup',lookup)
        resolution=asyncio.create_task(s.resolve_external(key,1))
        await wait_for(entered.is_set)
        worker=asyncio.create_task(s.deliver_worker('wavelog'))
        release.set();await resolution
        await asyncio.sleep(.15);s.stopping=True;await worker
        assert s.queue.execute("SELECT status FROM qso_delivery WHERE destination='wavelog'")==[('resolved_external',)]
        await s.stop();state.close()
        restored_state,restored=service_at(tmp_path,True);restored.retry()
        assert restored.queue.execute("SELECT status FROM qso_delivery WHERE destination='wavelog'")==[('resolved_external',)]
        await restored.stop();restored_state.close()
    asyncio.run(run())


def test_external_resolution_api_enforces_origin_and_read_only_location_selection(tmp_path,read_api):
    from pathlib import Path
    from fastapi.testclient import TestClient
    from backend.app import create_app
    from backend.config import save_wavelog_config
    from backend.receiver import Settings
    config=tmp_path/'config.toml';config.write_text(Path('config.example.toml').read_text())
    save_wavelog_config(config,WavelogSettings(url='http://wavelog.invalid',token='wl2_fixture'))
    state=WorkspaceState(tmp_path/'workspace.sqlite3')
    with TestClient(base_url='http://127.0.0.1', app=create_app(Settings(),state,config_path=config,serve_frontend=False)) as api:
        service=state.qso_service
        # Synthetic pre-upgrade delivery; ADIF receipt is already successful.
        key=service.queue.capture('Rig A',fields(),{},dict(wavelog=dict(url='http://wavelog.invalid',station_id=0)))
        service.queue.execute("UPDATE qso_outbox SET normalized=?,status='ready' WHERE id=?",(json.dumps(fields()),key))
        path=f'/api/qso/delivery/{key}/resolve-external'
        assert api.post(path,json={'station_id':1},headers={'Origin':'https://other.invalid'}).status_code==403
        assert api.post(path,json={'station_id':True}).status_code==409
        assert api.post(path,json={'station_id':1,'enable_logging':True}).status_code==409
        response=api.post(path,json={'station_id':1})
        assert response.status_code==200
        assert response.json()['qso']['config']['logging_enabled'] is False
        assert service.queue.execute("SELECT status,remote_id FROM qso_delivery")==[('resolved_external','77')]


@pytest.mark.parametrize('problem',['none','time','frequency','station','call','duplicates','incomplete','unauthorized','changed_destination'])
def test_unverified_external_resolution_is_held_without_submission(tmp_path,read_api,problem):
    async def run():
        state,s=service_at(tmp_path);key=seed_legacy(s)
        row=read_api['records'][0]
        if problem=='changed_destination':
            target=json.loads(s.queue.execute("SELECT target FROM qso_delivery WHERE destination='wavelog'")[0][0]);target['url']='http://other.invalid'
            s.queue.execute("UPDATE qso_delivery SET target=? WHERE destination='wavelog'",(json.dumps(target),))
        if problem=='none': read_api['records']=[]
        if problem=='time':row['date']='2026-10-24T12:00:01Z'
        if problem=='frequency':row['details']['freq']='14074001'
        if problem=='station':row['station']='KF0TKE'
        if problem=='call':row['call']='K2OTHER'
        if problem=='duplicates':read_api['records'].append(deepcopy(row))
        if problem=='incomplete':read_api['complete']=False
        with pytest.raises(DeliveryError):await s.resolve_external(key,2 if problem=='unauthorized' else 1)
        target,status=s.queue.execute("SELECT target,status FROM qso_delivery WHERE destination='wavelog'")[0]
        assert status=='held' and json.loads(target)['resolve_only']
        s.retry();assert s.queue.execute("SELECT status FROM qso_delivery WHERE destination='wavelog'")==[('held',)]
        await s.stop();state.close()
    asyncio.run(run())
