import asyncio
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sqlite3
import time
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.config import load_config, save_history_config
from backend.history_config import HistorySettings
from backend.observations import ObservationService, matches_contact
from backend.protocol import parse_packet
from backend.qso_model import adif_text, history_record
from backend.qso_config import QsoSettings
from backend.qso_history import QsoHistoryService
from backend.receiver import Settings, ingest
from backend.wavelog import WavelogService
from backend.wavelog_config import WavelogSettings
from backend.workspace import WorkspaceState
from backend.tests.fixtures import status, header, text, decode


def fields(call='K1OBS'):
    return dict(CALL=call, QSO_DATE='20261025', TIME_ON='120000', MODE='FT8', BAND='20m', FREQ='14.074', STATION_CALLSIGN='KF6UFO', RST_SENT='-10', RST_RCVD='-07')


def packet(call='K1OBS', rig='WSJT-X - IC7300'):
    return parse_packet(header(rig=rig,kind=12)+text(adif_text(fields(call))))


def services(tmp_path, enabled=False, adif=''):
    state = WorkspaceState(tmp_path/'workspace.sqlite3')
    state.enter_radio_workspace()
    wl = WavelogService(state, WavelogSettings(enabled=enabled))
    history = QsoHistoryService(state, QsoSettings(adif_path=adif, adif_complete=True), wl)
    obs = ObservationService(state,tmp_path/'observations.sqlite3',history,wl)
    state.observations=obs;state.wavelog_service=wl;state.qso_history=history
    return state,wl,history,obs


def select(state, call='K1OBS', rig='WSJT-X - IC7300'):
    ingest(status(call='K0BASE',rig=rig),state)
    ingest(status(call=call,rig=rig),state)


def test_observation_immediate_without_logging_or_history_and_no_reorder(tmp_path):
    state,wl,history,obs=services(tmp_path)
    select(state);select(state,'K2OTHER','WSJT-X - IC9100')
    original=deepcopy(state.history);current=state.call
    assert obs.capture(packet())
    assert state.call==current and state.history==original
    assert obs.snapshot()['summaries']['K1OBS']['pendingObserved']==1
    state.browse('K1OBS')
    result=obs.merged('K1OBS')
    assert result['recordCount']==1 and result['pendingObserved']==1 and not result['complete']
    assert result['records'][0]['observed'] and result['records'][0]['mode']=='FT8'
    assert not obs.capture(packet())
    # An identical event from another network ID is still one observed contact.
    assert not obs.capture(packet(rig='WSJT-X - IC9100'))
    assert not obs.capture(parse_packet(header(kind=5)))
    assert obs.capture(packet('K3ABSENT'))
    assert all(row['call']!='K3ABSENT' for row in state.history)
    assert state.history[1]['selectedAt']==original[1]['selectedAt']
    obs.db.close();state.close()


def test_pending_survives_restart_and_buffer_has_an_explicit_limit(tmp_path):
    state,wl,history,obs=services(tmp_path)
    select(state);obs.capacity=1
    assert obs.capture(packet())
    assert not obs.capture(packet('K2FULL')) and 'full' in obs.error
    obs.db.close();state.close()
    state,wl,history,obs=services(tmp_path)
    assert len(obs.pending)==1 and obs.snapshot()['summaries']['K1OBS']['pendingObserved']==1
    assert obs.records(obs.merged('K1OBS')['lookupId'])['recordCount']==1
    obs.db.close();state.close()


def test_match_requires_station_time_band_mode_and_frequency():
    original=fields();row=history_record(original,1)
    assert matches_contact(original,row)
    for key,value in [('call','K2NO'),('station','KF0TKE'),('date','2026-10-25T12:00:01Z'),('band','40m'),('mode','FT4')]:
        assert not matches_contact(original,row|{key:value})
    assert not matches_contact(original,row|{'details':{'freq':'14075000'}})
    assert not matches_contact(original,row|{'details':{}})
    assert not matches_contact(original|{'STATION_CALLSIGN':''},row)


def test_delayed_wavelog_replaces_observation_and_repeated_udp_stays_deduplicated(tmp_path):
    async def scenario():
        state,wl,history,obs=services(tmp_path,enabled=True);select(state)
        obs.delays=(.01,.02);obs.capture(packet())
        calls=[];real=history_record(fields(),77)
        def lookup(call):
            calls.append(call)
            return dict(call=call,status='empty' if len(calls)==1 else 'loaded',complete=True,records=[] if len(calls)==1 else [real])
        wl.client.lookup=lookup
        for item in obs.pending.values():item['due']=0
        await obs.start()
        await asyncio.sleep(.1)
        assert obs.merged(state.call)['pendingObserved']==1
        # The background reconciler retries without another Status or selection.
        deadline=time.monotonic()+4
        while obs.pending and time.monotonic()<deadline:await asyncio.sleep(.02)
        assert not obs.pending and len(calls)==2
        assert wl.result['records']==[real]
        assert obs.snapshot()['result'] is None
        assert not obs.capture(packet())
        assert obs.snapshot()['summaries']['K1OBS']['count']==1
        await obs.stop();state.close()
    asyncio.run(scenario())


def test_adif_reconciliation_does_not_append_and_partial_history_stays_explicit(tmp_path):
    async def scenario():
        path=tmp_path/'history.adi';path.write_text('')
        state,wl,history,obs=services(tmp_path,adif=str(path));select(state)
        obs.capture(packet());original=path.read_bytes()
        assert obs.merged(state.call)['pendingObserved']==1 and path.read_bytes()==original
        path.write_text(adif_text(fields()))
        history.adif.coverage=False
        partial=history.adif.lookup('K1OBS');history.result=partial|{'lookupId':'partial'}
        combined=obs.merged(state.call)
        assert len(combined['records'])==1 and combined['pendingObserved']==1 and not combined['complete']
        history.adif.coverage=True;history.adif.stamp=None
        for item in obs.pending.values():item['due']=0
        await obs.start()
        deadline=time.monotonic()+2
        while obs.pending and time.monotonic()<deadline:await asyncio.sleep(.02)
        assert not obs.pending and history.result['complete']
        assert path.read_text()==adif_text(fields())
        await obs.stop();state.close()
    asyncio.run(scenario())


def test_retention_uses_selection_time_and_clear_keeps_rigs_pending_work_and_contacts(tmp_path):
    state,wl,history,obs=services(tmp_path);select(state)
    old=state.history[0]['selectedAt']
    state.history[0]['selectedAt']=old-8*86400000
    state.history[0]['browsedAt']=old
    state.configure_history(HistorySettings(limit=50,retention_days=7))
    state.publish()
    assert state.history==[] and state.call==''
    select(state,'K2CURRENT')
    obs.capture(packet('K2CURRENT'))
    previous=deepcopy(state.previous);rigs=deepcopy(state.rigs)
    state.clear_history()
    assert not state.history and not state.call and state.previous==previous and state.rigs==rigs
    assert len(obs.pending)==1
    ingest(status(call='K2CURRENT'),state)
    assert not state.history # Unchanged Status must not undo Clear.
    obs.db.close();state.close()


def test_history_settings_api_limits_persistence_clear_and_secret_preservation(tmp_path):
    config=tmp_path/'config.toml';config.write_text(Path('config.example.toml').read_text())
    state=WorkspaceState(tmp_path/'data/workspace.sqlite3')
    with TestClient(create_app(Settings(),state,config_path=config,serve_frontend=False)) as api:
        for limit in (50,100,200,500):
            assert api.put('/api/history/settings',json={'limit':limit,'retention_days':30}).status_code==200
            assert load_config(config).history.limit==limit
        assert api.put('/api/history/settings',json={'limit':25,'retention_days':7}).status_code==422
        assert api.put('/api/history/settings',json={'limit':50,'retention_days':1}).status_code==422
        select(state)
        state.observations.capture(packet())
        state.qso_service.queue.capture('Fixture rig', fields(), {}, {'adif': {'path': str(tmp_path/'never-write.adi')}})
        assert api.delete('/api/history',headers={'Origin':'https://other.invalid'}).status_code==403
        response=api.delete('/api/history');assert response.status_code==200
        assert response.json()['history']==[] and response.json()['call']==''
        assert response.json()['observations']['pending']==1
        assert response.json()['qso']['config']['logging_enabled'] is False
        assert response.json()['qso']['queue']['jobs']['pending']==1
        assert not (tmp_path/'never-write.adi').exists()
    restored=WorkspaceState(tmp_path/'data/workspace.sqlite3')
    assert restored.history==[] and restored.call==''
    restored.close()


def test_size_limit_is_enforced_and_neither_telemetry_nor_observation_reorders(tmp_path):
    state,wl,history,obs=services(tmp_path)
    state.configure_history(HistorySettings(limit=50))
    ingest(status(call='K0BASE'),state)
    for n in range(60):ingest(status(call=f'K{n}ABC'),state)
    assert len(state.history)==50 and state.history[0]['call']=='K59ABC'
    entries=deepcopy(state.history)
    ingest(decode(),state);obs.capture(packet('K10ABC'))
    assert state.history==entries and state.call=='K59ABC'
    obs.db.close();state.close()


def test_missing_station_identity_can_be_filled_later_without_a_second_observation(tmp_path):
    state,wl,history,obs=services(tmp_path);select(state)
    original=fields();original.pop('STATION_CALLSIGN')
    event=parse_packet(header(rig='Unknown rig',kind=12)+text(adif_text(original)))
    assert obs.capture(event)
    state.rigs['Unknown rig']={'stationCall':'KF6UFO'}
    assert not obs.capture(event)
    assert len(obs.pending)==1 and next(iter(obs.pending.values()))['fields']['STATION_CALLSIGN']=='KF6UFO'
    obs.db.close();state.close()


def test_lookup_ids_are_bound_to_the_displayed_call_and_summary_scope(tmp_path):
    state,wl,history,obs=services(tmp_path);select(state)
    obs.capture(packet());old=obs.merged('K1OBS')['lookupId']
    obs.capture(packet('K2OTHER'));select(state,'K2OTHER')
    with pytest.raises(ValueError):obs.records(old)
    obs.remember(dict(call='K1OBS',complete=True,records=[history_record(fields(),1)]),'wavelog')
    assert obs.summaries['K1OBS']['count']==1
    wl.settings=replace(wl.settings,scope_mode='stations',station_ids=[99])
    obs.sync_context()
    assert obs.summaries=={} and len(obs.pending)==2
    obs.db.close();state.close()
