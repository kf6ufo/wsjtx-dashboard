"""Offline QSO pipeline contracts; no operator logs, credentials or production writes."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import pytest
from backend.qso_model import adif_records, parse_completed, adif_text, enrich_qso, QsoError
from backend.qso_config import QsoSettings
from backend.qso_history import ADIFHistoryProvider, WavelogHistoryProvider, QsoHistoryService
from backend.qso_delivery import DeliveryQueue, ADIFLogWriter, QsoDeliveryService, DeliveryError, UncertainDelivery, WavelogLogWriter
from backend.wavelog import WavelogService, WavelogClient
from backend.wavelog_config import WavelogSettings
from backend.protocol import parse_packet, PacketError
from backend.receiver import ingest, Settings
from backend.workspace import WorkspaceState
from backend.config import load_config, save_qso_config
from backend.app import create_app
from fastapi.testclient import TestClient
from .fixtures import header, text, status, decode
from .test_wavelog import gateway  # shared fake API read contract

PROFILE = dict(id='WSJT-X - IC7300', station_callsign='KF6UFO', operator='KF6UFO', wavelog_station_id=1, tx_power='20')

def fields(call='K1ABC', station='KF6UFO', **extra):
    return dict(CALL=call,QSO_DATE='20261024',TIME_ON='120000',MODE='FT8',BAND='20m',FREQ='14.074',STATION_CALLSIGN=station,RST_SENT='-07',RST_RCVD='-10') | extra

def logged(call='K1ABC', rig=PROFILE['id'], **extra): return header(rig=rig,kind=12) + text(adif_text(fields(call,**extra)))

def test_parser_completed_qso_and_strict_completeness():
    f = fields(COMMENT='literal <EOR> and <EOH> text', NAME='André')
    assert parse_completed(adif_text(f)) == f
    assert parse_packet(logged()).fields['adif']
    for raw in [adif_text(f)+'<CALL:20>unfinished', '<CALL:4>K1AB<EOR>', '<CALL:5>K1ABC<QSO_DATE:8>20260230<TIME_ON:4>1200<MODE:3>FT8<BAND:3>20m<EOR>', adif_text(f)+adif_text(f), 'Header<ADIF_VER:5>3.1.0'+adif_text(f)]:
        with pytest.raises(QsoError): parse_completed(raw)
    with pytest.raises(PacketError): parse_packet(header(kind=12))
    with pytest.raises(PacketError): parse_packet(logged()+b'x')


def test_adif_queries_thousands_and_incomplete_coverage(tmp_path):
    path=tmp_path/'log.adi'
    rows=[fields('K1ABC', station='KF6UFO' if i%2 else 'KF0TKE', TIME_ON=f'{i//3600:02}{i//60%60:02}{i%60:02}', BAND='20m' if i%2 else '40m', MODE='MFSK',SUBMODE='FT8') for i in range(10000)]
    path.write_text(''.join(map(adif_text,rows)))
    provider=ADIFHistoryProvider(path,True)
    assert len(provider.lookup('K1ABC')['records'])==10000
    assert provider.lookup('K1ABC')['records'][0]['details']['freq']=='14074000'
    assert len(provider.lookup('K1ABC','20m','FT8')['records'])==5000
    assert len(provider.lookup('K1ABC',mode='MFSK')['records'])==10000
    assert {q['station'] for q in provider.lookup('K1ABC')['records']}=={'KF0TKE','KF6UFO'}
    assert provider.loads==1
    assert provider.lookup('K2XYZ')['status']=='empty'
    uncertain=ADIFHistoryProvider(path,False)
    assert not uncertain.lookup('K2XYZ')['complete'] and uncertain.lookup('K2XYZ')['status']=='error'
    path.write_text(path.read_text()+'<CALL:20>bad')
    assert not provider.lookup('K2XYZ')['complete']
    assert len(provider.lookup('K1ABC')['records'])==10000
    path.unlink()
    assert provider.lookup('K2XYZ')['status']=='error'
    path.write_text('')
    assert ADIFHistoryProvider(path,False).lookup('K2XYZ')['status']=='error'
    assert ADIFHistoryProvider(path,True).lookup('K2XYZ')['status']=='empty'


def test_source_precedence_preserves_authoritative_qso_and_zero_power():
    original=fields(NAME='Original',GRIDSQUARE='FN31',TX_PWR='0',COMMENT='Operator comment')
    result,sources=enrich_qso(original,PROFILE,dict(fields=dict(country='Prediction',adif=999,locator='AA00',cqz=5),providers=dict(qrz=dict(fields=dict(name='QRZ Name',locator='FN31PR',country='Verified',adif=291,state='CT',county='New Haven')))))
    assert result['NAME']=='Original' and result['GRIDSQUARE']=='FN31' and result['TX_PWR']=='0'
    assert result['COUNTRY']=='Verified' and result['DXCC']=='291' and result['STATE']=='CT' and result['CNTY']=='CT,New Haven'
    assert result['COMMENT']=='Operator comment' and sources['NAME']=='WSJT-X'
    assert 'GRIDSQUARE' not in enrich_qso({k:v for k,v in original.items() if k!='GRIDSQUARE'},PROFILE,dict(fields=dict(locator='AA00')))[0]


def test_adif_atomic_recovery_and_duplicate_appends(tmp_path):
    queue=DeliveryQueue(tmp_path/'queue.sqlite3'); path=tmp_path/'log.adi'; writer=ADIFLogWriter(path,queue)
    writer.write('receipt',fields()); first=path.read_bytes()
    assert len(list(adif_records(io.StringIO(first.decode()))))==1
    writer.write('receipt',fields()); assert path.read_bytes()==first
    # Simulate a process dying partway through the journaled append.
    path.write_bytes(first[:-12]); writer.write('receipt',fields()); assert path.read_bytes()==first
    # An unrelated edit must never be truncated during recovery.
    path.write_bytes(b'Changed'+first)
    with pytest.raises(DeliveryError): writer.write('receipt',fields())
    queue.close()


@pytest.mark.parametrize('existing', ['', 'K2ORIGINAL'])
def test_qsl_via_qrz_fills_missing_only_and_survives_outputs(existing, monkeypatch):
    original = fields(QSL_VIA=existing)
    before = deepcopy(original)
    result, sources = enrich_qso(original, PROFILE, {'providers': {'qrz': {'fields': {'qslmgr': ' K1MANAGER via bureau '}}}})
    expected = existing or 'K1MANAGER via bureau'
    assert result['QSL_VIA'] == expected
    assert sources['QSL_VIA'] == ('WSJT-X' if existing else 'QRZ XML')
    assert original == before
    assert list(adif_records(io.StringIO(adif_text(result))))[0]['QSL_VIA'] == expected

    sent = []
    class Response:
        status_code = 201
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, size): yield b'{"data":{"id":42}}'
    def post(url, **kwargs):
        sent.append((url, kwargs['json']))
        return Response()
    monkeypatch.setattr('backend.qso_delivery.requests.post', post)
    writer = WavelogLogWriter(WavelogSettings(url='http://wavelog.invalid', token='wl2_fixture'), 1, 'KF6UFO')
    assert writer.write('fixture-key', result) == '42'
    assert len(sent) == 1 and sent[0][1]['qsl_via'] == expected


@pytest.mark.parametrize('qrz', [{}, {'qslmgr': ''}, {'qslmgr': None}, {'qslmgr': '   '}, {'lotw': 'Y', 'eqsl': 'Y'}])
def test_qsl_via_not_inferred_without_qrz_manager(qrz):
    result, sources = enrich_qso(fields(), PROFILE, dict(fields=dict(qslmgr='Generic prediction'), providers=dict(qrz=dict(fields=qrz))))
    assert 'QSL_VIA' not in result and 'QSL_VIA' not in sources


def test_config_roundtrip_and_default_read_only(tmp_path):
    path=tmp_path/'config.toml'; path.write_text(Path('config.example.toml').read_text())
    assert not load_config(path).qso.logging_enabled
    settings=QsoSettings(adif_path=str(tmp_path/'log.adi'),rigs=[PROFILE])
    save_qso_config(path,settings); assert load_config(path).qso==settings
    for values in [dict(adif_path='relative.adi'),dict(adif_path='/tmp/config.toml'),dict(logging_enabled=1),dict(rigs=[PROFILE,PROFILE])]:
        with pytest.raises(ValueError): QsoSettings(**values)


def test_optional_wavelog_history_adapter_filters(gateway):
    provider=WavelogHistoryProvider(WavelogClient(WavelogSettings(url='http://wavelog.test',token='wl2_fixture-secret')))
    assert len(provider.lookup('K1ABC',band='20m',mode='FT8')['records'])==12
    gateway.total=0; assert provider.lookup('K2XYZ')['worked'] is False
    gateway.failures[('qso',1)]=500; assert provider.lookup('K3ERR')['worked'] is None


async def wait_for(predicate):
    for _ in range(300):
        if predicate(): return
        await asyncio.sleep(.01)
    raise AssertionError('Pipeline did not settle')


def test_three_rigs_adif_only_duplicates_and_restart(tmp_path):
    async def scenario():
        state=WorkspaceState(tmp_path/'workspace.sqlite3');state.enter_radio_workspace()
        wl=WavelogService(state,WavelogSettings())
        config=QsoSettings(logging_enabled=True,adif_path=str(tmp_path/'log.adi'),adif_complete=True,rigs=[PROFILE])
        history=QsoHistoryService(state,config,wl)
        enrich=SimpleNamespace(settings=SimpleNamespace(enabled=False),lock=asyncio.Lock())
        service=QsoDeliveryService(state,config,wl,enrich,tmp_path/'queue.sqlite3',history);state.qso_service=service
        await service.start()
        for i,rig in enumerate(('WSJT-X - IC7300','WSJT-X - IC9100','WSJT-X - IC9700')):
            for _ in range(2): ingest(logged('K'+str(i+1)+'ABC',rig=rig),state)
            ingest(decode(rig=rig),state)
        await wait_for(lambda: service.queue.summary()['jobs'].get('delivered')==3)
        rows=list(adif_records(io.StringIO((tmp_path/'log.adi').read_text())))
        assert len(rows)==3 and {r['CALL'] for r in rows}=={'K1ABC','K2ABC','K3ABC'}
        assert state.call=='' and state.history==[]  # completed-QSO events do not select stations
        assert all(json.loads(row[0])=={} for row in service.queue.execute('SELECT original FROM qso_outbox'))
        await service.stop()
        restored=QsoDeliveryService(state,config,wl,enrich,tmp_path/'queue.sqlite3',history)
        await restored.start(); restored.capture(parse_packet(logged('K1ABC')))
        await asyncio.sleep(.2)
        assert restored.queue.summary()['jobs']['delivered']==3
        await restored.stop();state.close()
    asyncio.run(scenario())


def test_dual_destination_failure_does_not_block_local_logging(tmp_path,monkeypatch):
    async def scenario():
        state=WorkspaceState(tmp_path/'workspace.sqlite3')
        wl=WavelogService(state,WavelogSettings(enabled=True,url='http://wavelog.test',token='wl2_fixture-secret'))
        config=QsoSettings(logging_enabled=True,log_to_wavelog=True,adif_path=str(tmp_path/'log.adi'),rigs=[PROFILE])
        history=QsoHistoryService(state,config,wl); enrich=SimpleNamespace(settings=SimpleNamespace(enabled=False),lock=asyncio.Lock())
        service=QsoDeliveryService(state,config,wl,enrich,tmp_path/'queue.sqlite3',history)
        monkeypatch.setattr(WavelogLogWriter,'prepare',lambda *args: (_ for _ in ()).throw(DeliveryError('Offline')))
        await service.start();service.capture(parse_packet(logged()))
        await wait_for(lambda: any(r['status']=='delivered' and r['destination']=='adif' for r in service.queue.summary()['destinations']))
        assert service.queue.execute("SELECT status FROM qso_delivery WHERE destination='wavelog'")[0][0]=='error'
        await service.stop()
        # Reconnect/restart reuses the same frozen QSO and target; no ADIF reappend.
        service=QsoDeliveryService(state,config,wl,enrich,tmp_path/'queue.sqlite3',history)
        monkeypatch.setattr(WavelogLogWriter,'prepare',lambda *args: '42')
        service.retry();await service.start()
        await wait_for(lambda: service.queue.summary()['jobs'].get('delivered')==1)
        assert len(list(adif_records(io.StringIO((tmp_path/'log.adi').read_text()))))==1
        await service.stop();state.close()
    asyncio.run(scenario())


def test_wavelog_writer_permissions_mapping_and_lost_response(gateway,monkeypatch):
    settings=WavelogSettings(url='http://wavelog.test',token='wl2_fixture-secret')
    writer=WavelogLogWriter(settings,1,'KF6UFO')
    with pytest.raises(DeliveryError): writer.prepare(fields())  # read-only token
    monkeypatch.setattr(writer.client,'connect',lambda:dict(scopes=['qso:read','station:read','qso:write']))
    monkeypatch.setattr(writer.client,'station_by_id',lambda sid:dict(callsign='KF6UFO'))
    monkeypatch.setattr(writer,'matches',lambda f: None)
    with pytest.raises(UncertainDelivery): writer.prepare(fields(),True)
    with pytest.raises(DeliveryError): writer.prepare(fields(station='KF0TKE'))
    class Response:
        status_code=201
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,size):yield b'{"data":{"id":42}}'
    sent=[]
    def post(url,**kwargs): sent.append((url,kwargs));return Response()
    monkeypatch.setattr('backend.qso_delivery.requests.post',post)
    assert writer.write('fixture-key',fields())=='42'
    assert sent[0][1]['json']['freq']==14074000 and sent[0][1]['json']['qso_date']=='2026-10-24'
    assert sent[0][1]['allow_redirects'] is False
    monkeypatch.setattr('backend.qso_delivery.requests.post',lambda *a,**kw: (_ for _ in ()).throw(OSError()))
    with pytest.raises(UncertainDelivery): writer.write('fixture-key',fields())


def test_adif_fallback_then_wavelog_recovery_without_eager_index(tmp_path):
    async def scenario():
        path=tmp_path/'log.adi';path.write_text(adif_text(fields()))
        state=WorkspaceState(tmp_path/'workspace.sqlite3');state.enter_radio_workspace();state.call='K1ABC'
        wl=WavelogService(state,WavelogSettings(enabled=True)); wl.call='K1ABC'
        wl.result=dict(call='K1ABC',status='loaded',complete=True,records=[dict(id='wl-row')],lookupId='one')
        wl.connection['status']='ready'
        config=QsoSettings(adif_path=str(path),adif_complete=True)
        history=QsoHistoryService(state,config,wl);history.task=asyncio.create_task(history.worker());history.event.set()
        await wait_for(lambda: history.result.get('source')=='wavelog')
        assert history.adif.loads==0
        wl.result=dict(call='K1ABC',status='error',complete=False,records=[]);wl.connection['status']='error';history.next_probe=time.monotonic()+100
        history.event.set();await wait_for(lambda: history.result.get('source')=='adif')
        assert history.result['complete'] and history.adif.loads==1
        wl.result=dict(call='K1ABC',status='empty',complete=True,records=[],lookupId='two');wl.connection['status']='ready';history.event.set()
        await wait_for(lambda: history.result.get('source')=='wavelog')
        assert history.result['status']=='empty'
        await history.stop();state.close()
    asyncio.run(scenario())


def test_installed_api_adif_history_no_wavelog_and_no_secret_leaks(tmp_path):
    path=tmp_path/'config.toml';path.write_text(Path('config.example.toml').read_text())
    log=tmp_path/'history.adi';log.write_text(adif_text(fields()))
    save_qso_config(path,QsoSettings(adif_path=str(log),adif_complete=True))
    state=WorkspaceState(tmp_path/'workspace.sqlite3')
    with TestClient(base_url='http://127.0.0.1', app=create_app(Settings(),state,config_path=path,serve_frontend=False)) as api:
        state.enter_radio_workspace();ingest(status(call='K0BASE'),state);ingest(status(call='K1ABC'),state)
        for _ in range(100):
            s=api.get('/api/snapshot').json()
            if s['qsoHistory']['result'].get('lookupId'):break
            time.sleep(.02)
        result=s['qsoHistory']['result'];assert result['complete']
        assert len(api.get('/api/qso/history/'+result['lookupId']).json()['records'])==1
        assert api.put('/api/qso/settings',json={},headers={'Origin':'https://other.test'}).status_code==403
        assert api.put('/api/qso/settings',json={'adif_complete':False}).status_code==200
        ingest(logged(),state);assert api.get('/api/snapshot').json()['qso']['queue']['jobs']=={}


def test_unknown_wavelog_outcome_survives_restart_and_only_reconciles(tmp_path,monkeypatch):
    async def scenario():
        state=WorkspaceState(tmp_path/'workspace.sqlite3')
        wl=WavelogService(state,WavelogSettings(url='http://wavelog.test',token='wl2_fixture-secret'))
        config=QsoSettings(logging_enabled=True,log_to_wavelog=True,rigs=[PROFILE])
        history=QsoHistoryService(state,config,wl); enrich=SimpleNamespace(settings=SimpleNamespace(enabled=False),lock=asyncio.Lock())
        stored=[]; seen=[]
        def prepare(self,fields,uncertain=False):
            seen.append(uncertain)
            return '77' if stored else None
        def write(self,key,fields):
            stored.append(deepcopy(fields))
            raise UncertainDelivery('Response lost after server committed')
        monkeypatch.setattr(WavelogLogWriter,'prepare',prepare);monkeypatch.setattr(WavelogLogWriter,'write',write)
        service=QsoDeliveryService(state,config,wl,enrich,tmp_path/'queue.sqlite3',history)
        await service.start();service.capture(parse_packet(logged()))
        await wait_for(lambda: service.queue.execute("SELECT status FROM qso_delivery")==[('uncertain',)])
        await service.stop()
        restored=QsoDeliveryService(state,config,wl,enrich,tmp_path/'queue.sqlite3',history)
        restored.retry();await restored.start()
        await wait_for(lambda: restored.queue.summary()['jobs'].get('delivered')==1)
        assert len(stored)==1 and seen==[False,True]
        assert restored.queue.execute('SELECT remote_id FROM qso_delivery')==[('77',)]
        await restored.stop();state.close()
    asyncio.run(scenario())


def test_enrichment_failure_and_missing_adif_destination_are_independent(tmp_path):
    async def scenario():
        state=WorkspaceState(tmp_path/'workspace.sqlite3');wl=WavelogService(state,WavelogSettings())
        config=QsoSettings(logging_enabled=True,adif_path=str(tmp_path/'missing'/'log.adi'),rigs=[PROFILE])
        history=QsoHistoryService(state,config,wl)
        class Providers:
            def enrich(self,context): raise ValueError('Provider unavailable')
        enrich=SimpleNamespace(settings=SimpleNamespace(enabled=True),providers=Providers(),lock=asyncio.Lock())
        service=QsoDeliveryService(state,config,wl,enrich,tmp_path/'queue.sqlite3',history)
        await service.start();service.capture(parse_packet(logged()))
        await wait_for(lambda: service.queue.execute('SELECT status FROM qso_delivery')==[('error',)])
        assert service.queue.execute('SELECT normalized FROM qso_outbox')[0][0]
        (tmp_path/'missing').mkdir();service.retry()
        await wait_for(lambda: service.queue.summary()['jobs'].get('delivered')==1)
        row=list(adif_records(io.StringIO((tmp_path/'missing'/'log.adi').read_text())))[0]
        assert row['CALL']=='K1ABC' and row['TX_PWR']=='20' and row['RST_SENT']=='-07'
        await service.stop();state.close()
    asyncio.run(scenario())


def test_file_writer_lock_keeps_simultaneous_appends_valid(tmp_path):
    queue=DeliveryQueue(tmp_path/'queue.sqlite3');path=tmp_path/'log.adi'
    errors=[]
    def append(number):
        try: ADIFLogWriter(path,queue).write(str(number),fields('K'+str(number)+'ABC'))
        except Exception as error: errors.append(error)
    threads=[threading.Thread(target=append,args=(n,)) for n in range(1,11)]
    for thread in threads:thread.start()
    for thread in threads:thread.join()
    assert not errors
    assert len(list(adif_records(io.StringIO(path.read_text()))))==10
    queue.close()


def test_automatic_recovery_rechecks_wavelog_and_clears_adif_fallback(tmp_path,monkeypatch):
    async def scenario():
        path=tmp_path/'history.adi';path.write_text(adif_text(fields()))
        state=WorkspaceState(tmp_path/'workspace.sqlite3');state.enter_radio_workspace();state.call='K1ABC'
        wl=WavelogService(state,WavelogSettings(enabled=True));state.wavelog_service=wl
        online=False
        def lookup(self,call):
            self.connection['status']='ready' if online else 'error'
            return dict(call=call,status='empty' if online else 'error',complete=online,records=[],message='' if online else 'Offline')
        async def test_connection():
            wl.connection['status']='error'
        monkeypatch.setattr(WavelogClient,'lookup',lookup);monkeypatch.setattr(wl,'test',test_connection)
        history=QsoHistoryService(state,QsoSettings(adif_path=str(path)),wl)
        await wl.start();await history.start()
        await wait_for(lambda: history.result.get('source')=='adif')
        assert not history.result['complete']
        online=True;history.next_probe=0;history.event.set()
        await wait_for(lambda: history.result.get('source')=='wavelog')
        assert history.result['complete'] and history.adif.loads==1
        await history.stop();await wl.stop();state.close()
    asyncio.run(scenario())


def test_missing_identity_is_held_and_mapping_retry_preserves_contact(tmp_path):
    async def scenario():
        state=WorkspaceState(tmp_path/'workspace.sqlite3');wl=WavelogService(state,WavelogSettings())
        config=QsoSettings(logging_enabled=True,adif_path=str(tmp_path/'log.adi'))
        history=QsoHistoryService(state,config,wl);enrich=SimpleNamespace(settings=SimpleNamespace(enabled=False),lock=asyncio.Lock())
        service=QsoDeliveryService(state,config,wl,enrich,tmp_path/'queue.sqlite3',history)
        await service.start();service.capture(parse_packet(logged(station='')))
        await wait_for(lambda: service.queue.summary()['jobs'].get('blocked')==1)
        assert not (tmp_path/'log.adi').exists()
        service.settings=replace(config,rigs=[PROFILE]);service.retry()
        await wait_for(lambda: service.queue.summary()['jobs'].get('delivered')==1)
        row=list(adif_records(io.StringIO((tmp_path/'log.adi').read_text())))[0]
        assert row['STATION_CALLSIGN']=='KF6UFO' and row['APP_WSJT_DASHBOARD_RIG']==PROFILE['id']
        await service.stop();state.close()
    asyncio.run(scenario())
