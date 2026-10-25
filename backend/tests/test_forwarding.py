import asyncio
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import socket
import struct
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.config import load_config, save_forwarding_config
from backend.forwarding import ForwardingService, encode_logged_adif, resolve_target
from backend.forwarding_config import ForwardingSettings
from backend.protocol import parse_packet
from backend.qso_config import QsoSettings
from backend.qso_model import adif_text, parse_completed
from backend.receiver import Settings, ingest
from backend.workspace import WorkspaceState
from backend.tests.fixtures import header,text,status,decode
from backend.tests.test_observations_history import fields


def destination(key,port,**changes):
    return dict(id=key,name=key,enabled=True,host='127.0.0.1',port=port,rigs=[],packets=[0,1,2,3,5,12],format='raw')|changes


def collector():
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('127.0.0.1',0));sock.setblocking(False)
    return sock


async def receive(sock,timeout=1):
    return (await asyncio.wait_for(asyncio.get_running_loop().sock_recvfrom(sock,65535),timeout))[0]


async def ready(service):
    for _ in range(100):
        if all(i['status']!='resolving' for i in service.outputs.values()):return
        await asyncio.sleep(.01)
    raise AssertionError('forwarding resolution timed out')


def service(tmp_path,rows,enrichment=None):
    state=WorkspaceState(tmp_path/'workspace.sqlite3');state.enter_radio_workspace()
    state.configure_receiver(Settings(enabled=True,group='',listen='127.0.0.1',interface='127.0.0.1',port=18299))
    enrichment=enrichment or SimpleNamespace(settings=SimpleNamespace(enabled=False),lock=asyncio.Lock())
    forward=ForwardingService(state,ForwardingSettings(rows),enrichment,lambda:QsoSettings(),tmp_path/'forwarding.sqlite3')
    state.forwarding=forward
    return state,forward


def test_raw_preserves_bytes_ids_future_schema_and_filters_without_commands(tmp_path):
    async def scenario():
        first,second=collector(),collector()
        state,fwd=service(tmp_path,[destination('first',first.getsockname()[1],rigs=['Rig A']),destination('second',second.getsockname()[1],packets=[2])])
        await fwd.start();await ready(fwd)
        raw=status(call='K1OBS',rig='Rig A');ingest(raw,state)
        assert await receive(first)==raw
        decoded=decode(rig='Rig A');ingest(decoded,state)
        assert await receive(first)==decoded and await receive(second)==decoded
        other=status(call='K2OTHER',rig='Rig B');ingest(other,state)
        future=decoded[:4]+struct.pack('!I',99)+decoded[8:];ingest(future,state)
        assert await receive(first)==future and await receive(second)==future
        control=header(rig='Rig A',kind=4);ingest(control,state)
        with pytest.raises(asyncio.TimeoutError):await receive(first,.05)
        assert fwd.outputs['first']['filtered']>=1 and fwd.outputs['second']['filtered']>=2
        assert state.call=='' # Baselines and Decodes never became selections.
        await fwd.stop();state.close();first.close();second.close()
    asyncio.run(scenario())


def test_disable_reenable_and_one_failed_output_do_not_block_another(tmp_path,monkeypatch):
    from backend import forwarding
    resolver=forwarding.resolve_target
    async def resolve(row,receiver):
        if row['host']=='unavailable.invalid':raise OSError('offline fixture')
        return await resolver(row,receiver)
    monkeypatch.setattr(forwarding,'resolve_target',resolve)
    async def scenario():
        sink=collector();rows=[destination('good',sink.getsockname()[1]),destination('bad',sink.getsockname()[1],host='unavailable.invalid')]
        state,fwd=service(tmp_path,rows);await fwd.start();await ready(fwd)
        raw=decode();ingest(raw,state);assert await receive(sink)==raw
        await asyncio.sleep(.02)
        assert fwd.outputs['bad']['dropped']==1 and fwd.outputs['good']['dispatched']==1
        await fwd.configure(ForwardingSettings([rows[0]|{'enabled':False}]))
        ingest(raw,state)
        with pytest.raises(asyncio.TimeoutError):await receive(sink,.05)
        await fwd.configure(ForwardingSettings([rows[0]]));await ready(fwd);ingest(raw,state)
        assert await receive(sink)==raw
        await fwd.stop();state.close();sink.close()
    asyncio.run(scenario())


def test_enriched_completed_messages_are_valid_deduplicated_independent_and_restart_safe(tmp_path):
    async def scenario():
        raw_sink,enriched_sink=collector(),collector()
        enrichment=SimpleNamespace(settings=SimpleNamespace(enabled=True),lock=asyncio.Lock(),providers=SimpleNamespace(enrich=lambda ctx:dict(providers={'qrz':{'fields':{'name':'Fixture É','country':'Verified','adif':291}}})))
        rows=[destination('raw',raw_sink.getsockname()[1]),destination('rich',enriched_sink.getsockname()[1],format='enriched-adif')]
        state,fwd=service(tmp_path,rows,enrichment);await fwd.start();await ready(fwd)
        original=fields();raw=header(rig='Rig A',kind=12)+text(adif_text(original))
        # Hold only enrichment. Ordinary messages still reach both destinations.
        await enrichment.lock.acquire()
        ingest(raw,state);assert await receive(raw_sink)==raw
        routine=decode(rig='Rig A');ingest(routine,state)
        assert await receive(raw_sink)==routine and await receive(enriched_sink)==routine
        enrichment.lock.release()
        enriched=parse_packet(await receive(enriched_sink))
        assert '<EOH>' in enriched.fields['adif']
        output=parse_completed(enriched.fields['adif'])
        assert enriched.kind==12 and enriched.rig_id=='Rig A'
        assert all(output[k]==v for k,v in original.items())
        assert output['NAME']=='Fixture É' and output['COUNTRY']=='Verified'
        ingest(header(rig='Rig A',kind=5),state);ingest(raw,state);ingest(raw,state)
        ingest(header(rig='Rig B',kind=12)+text(adif_text(original)),state)
        with pytest.raises(asyncio.TimeoutError):await receive(enriched_sink,.08)
        assert fwd.outputs['rich']['filtered']>=4
        await fwd.stop();state.close()
        state,fwd=service(tmp_path,[rows[1]],enrichment);await fwd.start();await ready(fwd)
        ingest(raw,state)
        with pytest.raises(asyncio.TimeoutError):await receive(enriched_sink,.05)
        await fwd.stop();state.close();raw_sink.close();enriched_sink.close()
    asyncio.run(scenario())


def test_failed_enrichment_keeps_original_values_and_queues_are_bounded(tmp_path):
    async def scenario():
        sink=collector()
        def fail(_ctx):raise OSError('provider unavailable')
        enrichment=SimpleNamespace(settings=SimpleNamespace(enabled=True),lock=asyncio.Lock(),providers=SimpleNamespace(enrich=fail))
        state,fwd=service(tmp_path,[destination('rich',sink.getsockname()[1],format='enriched-adif')],enrichment)
        await fwd.start();await ready(fwd)
        raw=header(rig='Rig A',kind=12)+text(adif_text(fields()));ingest(raw,state)
        assert parse_completed(parse_packet(await receive(sink)).fields['adif'])==fields()
        item=fwd.outputs['rich']
        # No unbounded allocation even if a destination cannot drain telemetry.
        for _ in range(300):fwd.enqueue(item,b'bounded fixture')
        assert item['queue'].qsize()==256 and item['dropped']==44
        assert fwd.completed.maxsize==64
        await fwd.stop();state.close();sink.close()
    asyncio.run(scenario())


def test_loop_rejection_at_save_and_at_dispatch_and_settings_validation(tmp_path):
    async def scenario():
        row=destination('loop',18299)
        with pytest.raises(ValueError):await resolve_target(row,Settings(port=18299,interface='127.0.0.1'))
        for changes in [dict(host='239.255.0.73'),dict(host='0.0.0.0'),dict(host='https://localhost'),dict(packets=[4]),dict(format='naked-adif'),dict(format='enriched-adif',packets=[5])]:
            with pytest.raises(ValueError):ForwardingSettings([row|changes])
        with pytest.raises(ValueError):ForwardingSettings([row,row])
        with pytest.raises(ValueError):ForwardingSettings([row|{'id':str(i)} for i in range(17)])
    asyncio.run(scenario())
    config=tmp_path/'config.toml';config.write_text(Path('config.example.toml').read_text())
    state=WorkspaceState(tmp_path/'data/workspace.sqlite3')
    with TestClient(create_app(Settings(),state,config_path=config,serve_frontend=False)) as api:
        result=api.put('/api/forwarding',json={'destinations':[destination('loop',2238)]})
        assert result.status_code==422
        row=destination('stored',18349,enabled=False)
        assert api.put('/api/forwarding',json={'destinations':[row]}).status_code==200
        assert load_config(config).forwarding.destinations==[row]
        assert api.get('/api/snapshot').json()['qso']['config']['logging_enabled'] is False
        assert api.put('/api/forwarding',json={'destinations':[]},headers={'Origin':'https://other.invalid'}).status_code==403
