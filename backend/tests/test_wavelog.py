"""Offline API fixtures: full pagination, scope, independent workers and secrets."""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import pytest
from backend.app import create_app
from backend.config import load_config, save_wavelog_config, save_enrichment_config, save_receiver_config
from backend.enrichment_config import EnrichmentSettings
from backend.receiver import Settings, ingest
from backend.wavelog import WavelogClient, WavelogService
from backend.wavelog_config import WavelogSettings, update_wavelog_settings
from backend.workspace import WorkspaceState
from .fixtures import status, decode

STATIONS = [dict(id=1, name='Current home', callsign='KF6UFO', gridsquare='DM57', active=True),
            dict(id=2, name='Former callsign', callsign='KF0TKE', gridsquare='DM57', active=False)]


def contact(number, call='K1ABC', sid=None):
    return dict(id=number, call=call, station_id=sid or (1 if number % 2 else 2),
        qso_date=(datetime(2020, 1, 1) + timedelta(minutes=number)).isoformat(' '),
        band='20m' if number % 2 else '40m', mode='MFSK', submode='FT8', rst_sent='-07', rst_rcvd='-10',
        gridsquare='FN31', freq='14074000', comment='Fixture contact')


class Response:
    def __init__(self, body, status=200):
        self.status_code, self.body = status, body
    def iter_content(self, _): yield json.dumps(self.body).encode()
    def __enter__(self): return self
    def __exit__(self, *args): pass


@pytest.fixture
def gateway(monkeypatch):
    class Gateway:
        def __init__(self):
            self.calls, self.failures, self.total = [], {}, 23
            self.stations = STATIONS.copy()
            self.mutate = lambda body, params: body
        def get(self, url, **kwargs):
            resource = urlsplit(url).path.split('/api/v2/')[-1]
            params = kwargs.get('params') or {}
            self.calls.append((resource, params, kwargs))
            assert kwargs['allow_redirects'] is False
            assert 'fixture-secret' not in url
            failure = self.failures.get((resource, params.get('page', 1)))
            if failure: return Response({'error': {'message': 'fixture-secret private response'}}, failure)
            if resource == 'status': return Response({'data': {'status': 'ok', 'name': 'Wavelog API'}})
            if resource == 'token': return Response({'data': {'owner': 'KF6UFO', 'scopes': ['qso:read', 'station:read', 'logbook:read', 'confirmation:read'], 'expires_at': None}})
            if resource == 'station': return Response({'data': self.stations})
            if resource.startswith('station/'): return Response({'data': STATIONS[int(resource.split('/')[1]) - 1]})
            book = dict(id=9, name='Both callsigns', station_ids=[1, 2], active=True)
            if resource == 'logbook': return Response({'data': [book]})
            if resource == 'logbook/9': return Response({'data': book})
            call, page, size = params.get('callsign', 'K1ABC'), params.get('page', 1), params.get('per_page', 100)
            if resource == 'qso':
                rows = [contact(i, call) for i in range(1, self.total + 1)]
                if params.get('station_id'): rows = [row for row in rows if row['station_id'] in map(int, params['station_id'].split(','))]
            elif resource == 'confirmation':
                rows = [] if not self.total else [dict(qso_id=1, callsign=call, type='LoTW', confirmation_date='2021-01-01')]
                if params.get('station_id') == '2': rows = []
            else: raise AssertionError(resource)
            total = len(rows); rows = rows[(page - 1) * size:page * size]
            body = dict(data=rows, meta=dict(page=page, per_page=size, count=len(rows), total=total, total_pages=(total+size-1)//size, has_more=page*size < total))
            return Response(self.mutate(body, params) if resource == 'qso' else body)
    gateway = Gateway()
    monkeypatch.setattr('backend.wavelog.requests.get', gateway.get)
    return gateway


def client(**settings):
    return WavelogClient(WavelogSettings(url='http://wavelog.test/index.php/api', token='wl2_fixture-secret', page_size=10, **settings))


def test_all_pages_both_station_callsigns_and_confirmations_are_read_only(gateway):
    provider = client()
    result = provider.lookup('K1ABC')
    assert result['complete'] and result['status'] == 'loaded' and len(result['records']) == 23
    assert {row['station'] for row in result['records']} == {'KF6UFO', 'KF0TKE'}
    assert result['records'][0]['date'] > result['records'][-1]['date']
    assert result['records'][0]['mode'] == 'FT8' and result['records'][0]['details']['freq'] == '14074000'
    assert next(row for row in result['records'] if row['id'] == '1')['confirmed'] is True
    assert next(row for row in result['records'] if row['id'] == '2')['confirmed'] is False
    assert [params['page'] for resource, params, _ in gateway.calls if resource == 'qso'] == [1, 2, 3]
    assert all('station_id' not in params for resource, params, _ in gateway.calls if resource == 'qso')
    assert 'fixture-secret' not in json.dumps(result)
    before = len(gateway.calls)
    assert provider.lookup('K1ABC')['cached']
    assert len(gateway.calls) == before


@pytest.mark.parametrize('failure', [401, 403, 404, 429, 500])
def test_failed_first_page_is_never_empty_or_secret_bearing(gateway, failure):
    gateway.failures[('qso', 1)] = failure
    result = client().lookup('K1ABC')
    assert result['status'] == 'error' and result['complete'] is False
    assert result['records'] == [] and 'fixture-secret' not in json.dumps(result)


def test_later_page_failure_preserves_partial_contacts_without_claiming_complete(gateway):
    gateway.failures[('qso', 2)] = 500
    result = client().lookup('K1ABC')
    assert result['status'] == 'incomplete' and not result['complete']
    assert len(result['records']) == 10 and result['total'] == 23


@pytest.mark.parametrize('variant', ['changed-total', 'duplicate', 'empty-intermediate', 'false-empty'])
def test_bad_pagination_is_not_treated_as_complete(gateway, variant):
    def mutate(body, params):
        if variant == 'false-empty': body['data'] = []; body['meta'].update(count=0, has_more=False)
        elif params.get('page') == 2:
            if variant == 'changed-total': body['meta']['total'] += 1
            elif variant == 'duplicate': body['data'][0]['id'] = 1
            elif variant == 'empty-intermediate': body['data'] = []; body['meta']['count'] = 0
        return body
    gateway.mutate = mutate
    result = client().lookup('K1ABC')
    assert not result['complete'] and result['status'] in ('error', 'incomplete')


@pytest.mark.parametrize('settings, count', [(dict(max_pages=1), 10), (dict(max_records=3), 3)])
def test_safety_limits_preserve_incomplete_state(gateway, settings, count):
    result = client(**settings).lookup('K1ABC')
    assert result['status'] == 'incomplete' and len(result['records']) == count
    assert not result['complete'] and 'limit' in result['message']


def test_genuine_zero_is_complete_and_optional_confirmation_failure_is_separate(gateway):
    gateway.total = 0
    assert client().lookup('K1ABC')['status'] == 'empty'
    gateway.total = 23
    gateway.failures[('confirmation', 1)] = 403
    result = client().lookup('K1ABC')
    assert result['complete'] and result['confirmationStatus'] == 'unavailable'
    assert all(row['confirmed'] is None for row in result['records'])


def test_station_scope_and_hidden_former_location_are_resolved(gateway):
    result = client(scope_mode='stations', station_ids=[2]).lookup('K1ABC')
    assert result['complete'] and {row['station'] for row in result['records']} == {'KF0TKE'}
    gateway.stations = STATIONS[:1]
    result = client().lookup('K1ABC')
    assert result['complete'] and {row['station'] for row in result['records']} == {'KF6UFO', 'KF0TKE'}
    assert any(resource == 'station/2' for resource, _, _ in gateway.calls)
    assert client(scope_mode='logbook', logbook_id=9).lookup('K1ABC')['complete']


def test_wrong_location_identity_and_fractional_dates(gateway):
    gateway.total = 2
    def fractional(body, params):
        body['data'][0]['qso_date'] = '2020-01-01 00:00:00'
        body['data'][1]['qso_date'] = '2020-01-01 00:00:00.500000'
        return body
    gateway.mutate = fractional
    assert client().lookup('K1ABC')['records'][0]['id'] == '2'
    gateway.stations = STATIONS[:1]
    STATIONS[1]['id'] = 3
    try:
        result = client().lookup('K1ABC')
        assert not result['complete'] and 'different station' in result['message']
    finally:
        STATIONS[1]['id'] = 2


def test_expired_cache_failure_and_refresh_keep_worked_status_unknown(gateway):
    provider = client(cache_limit=1)
    assert provider.lookup('K1ABC')['complete']
    provider.cache['K1ABC']['updatedAt'] = 0
    gateway.failures[('qso', 1)] = 500
    result = provider.lookup('K1ABC')
    assert result['status'] == 'incomplete' and not result['complete']
    assert len(result['records']) == 23 and 'previously loaded' in result['message']
    gateway.failures.clear()
    provider.lookup('K2XYZ')
    assert list(provider.cache) == ['K2XYZ']


def test_config_saves_preserve_qrz_receiver_and_secret_retention(tmp_path):
    path = tmp_path / 'config.toml'
    path.write_text(Path('config.example.toml').read_text())
    save_enrichment_config(path, EnrichmentSettings(qrz_username='operator', qrz_password='private-qrz'))
    settings = WavelogSettings(url='http://wavelog.test/api', token='wl2_fixture-secret')
    save_wavelog_config(path, settings)
    save_receiver_config(path, Settings(retention=50))
    assert load_config(path).wavelog == settings
    assert load_config(path).enrichment.qrz_password == 'private-qrz'
    assert path.stat().st_mode & 0o077 == 0
    assert 'fixture-secret' not in repr(settings) + json.dumps(settings.public())
    assert update_wavelog_settings(settings, {'token': ''}).token == settings.token
    assert update_wavelog_settings(settings, {'clear_token': True}).token == ''
    with pytest.raises(ValueError): WavelogSettings(url='http://user:private-password@host/')
    with pytest.raises(ValueError): WavelogSettings(token='old-api-key')


def test_api_metadata_omits_records_and_qso_fetch_does_not_mutate_history(tmp_path, gateway):
    path = tmp_path / 'config.toml'; path.write_text(Path('config.example.toml').read_text())
    state = WorkspaceState(tmp_path / 'workspace.sqlite3')
    with TestClient(create_app(Settings(), state, config_path=path, serve_frontend=False)) as api:
        state.enter_radio_workspace(); ingest(status(call='K0BASE'), state); ingest(status(call='K1ABC'), state)
        before = json.loads(json.dumps(state.history)); previous = state.previous.copy()
        response = api.put('/api/wavelog', json=dict(enabled=True, url='http://wavelog.test/api', token='wl2_fixture-secret', page_size=10))
        assert response.status_code == 200 and 'fixture-secret' not in response.text
        for _ in range(100):
            snapshot = api.get('/api/snapshot').json()
            if snapshot['wavelog']['result']['status'] == 'loaded': break
            time.sleep(.01)
        result = snapshot['wavelog']['result']
        assert result['complete'] and 'records' not in result
        assert 'fixture-secret' not in json.dumps(snapshot)
        history = api.get('/api/wavelog/history/' + result['lookupId']).json()
        assert len(history['records']) == 23
        assert state.history == before and state.previous == previous
        assert api.get('/api/wavelog/history/not-current').status_code == 409
        assert api.put('/api/wavelog', json={}, headers={'Origin': 'https://foreign.test'}).status_code == 403


def test_slow_history_does_not_block_decodes_or_replace_a_new_focus(tmp_path, monkeypatch):
    async def scenario():
        state = WorkspaceState(tmp_path / 'workspace.sqlite3');state.enter_radio_workspace()
        started, release = threading.Event(), threading.Event()
        def lookup(self, call):
            if call == 'K1SLOW': started.set();release.wait(2)
            return dict(status='empty', call=call, records=[], total=0, complete=True)
        monkeypatch.setattr(WavelogClient, 'lookup', lookup)
        service = WavelogService(state, WavelogSettings(enabled=True));state.wavelog_service = service
        await service.start()
        ingest(status(call='K0BASE'), state);ingest(status(call='K1SLOW'), state)
        while not started.is_set(): await asyncio.sleep(.005)
        ingest(status(call='K2FAST'), state);ingest(decode(), state)
        assert state.call == 'K2FAST' and state.counters['decodes'] == 1
        assert service.snapshot()['result']['status'] == 'pending'
        release.set()
        for _ in range(100):
            if service.result['status'] == 'empty': break
            await asyncio.sleep(.01)
        assert service.result['call'] == 'K2FAST'
        await service.stop();state.close()
    asyncio.run(scenario())
