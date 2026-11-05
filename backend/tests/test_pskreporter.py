import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.config import load_config
from backend.protocol import parse_packet
from backend.state import FocusState
from backend.tests.fixtures import status
from backend.pskreporter import PskReporterService, parse_spot, topic_for
from backend.pskreporter_config import PskReporterSettings
from backend.workspace import WorkspaceState

NOW = 1793900000


def test_selection_captures_station_identity_without_telemetry_rewriting_provenance():
    state = FocusState()
    state.accept(parse_packet(status(call='K0BASE')))
    state.accept(parse_packet(status(call='K1FOCUS')))
    assert state.history[0]['stationCall'] == 'N0TEST'
    selection = deepcopy(state.history[0])
    packet = parse_packet(status(call='K1FOCUS'))
    packet.fields['deCall'] = 'K2NEW'
    state.accept(packet)
    assert state.rigs[packet.rig_id]['stationCall'] == 'K2NEW'
    assert state.history[0] == selection


def spot(**changes):
    return json.dumps(dict(sc='N0CALL', rc='K1FOCUS', rl='FN31ab', f=14074653,
                           b='20m', md='FT8', rp=-12, t=NOW - 60) | changes).encode()


@pytest.mark.parametrize('changes', [dict(sc='K1OTHER'), dict(sc=5), dict(rc=''), dict(rl='ZZ99'),
    dict(t=NOW-3600), dict(t=NOW+31), dict(t=True), dict(t=float('nan')), dict(f=True),
    dict(f=123), dict(f=float('inf')), dict(rl=123)])
def test_invalid_reverse_old_and_wrong_identity_reports_are_rejected(changes):
    assert parse_spot(spot(**changes), {'N0CALL'}, NOW) is None


def test_schema_time_frequency_band_and_literal_portable_calls():
    parsed = parse_spot(spot(t_tx=NOW-80, b='10m'), {'N0CALL'}, NOW)
    assert parsed['heardAt'] == (NOW-80)*1000
    assert parsed['band'] == '20m'  # Frequency wins over an inconsistent label.
    assert parsed['grid'] == 'FN31AB' and parsed['snr'] == -12
    assert topic_for('N0CALL/P') == 'pskr/filter/v2/+/+/N0CALL/P/#'
    for raw in (b'null', b'[]', b'bad JSON', b'\xff', b' ' * 4097):
        assert parse_spot(raw, {'N0CALL'}, NOW) is None


class FakeClient:
    def __init__(self, inbox):
        self.inbox, self.topics, self.removed = inbox, [], []
        self.connected, self.stopped = False, False

    def is_connected(self): return self.connected
    def subscribe(self, topic, qos): self.topics.append(topic); return (0, len(self.topics))
    def unsubscribe(self, topic): self.removed.append(topic)
    def disconnect(self): self.connected = False
    def loop_stop(self): self.stopped = True
    def connect(self):
        self.connected = True
        self.inbox.put_nowait(('connected', None))


def test_shared_cache_reconnect_identities_expiry_and_no_focus_side_effects(tmp_path, monkeypatch):
    async def scenario():
        state = WorkspaceState(tmp_path/'workspace.sqlite3'); state.enter_radio_workspace()
        state.rigs = {'A': dict(stationCall='N0CALL'), 'B': dict(stationCall='K2OTHER')}
        state.call = 'K1FOCUS'
        state.history = [dict(call='K1FOCUS',rigId='A',stationCall='N0CALL',band='20m',selectedAt=NOW*1000,recency=1)]
        clock = [NOW]
        service = PskReporterService(state, PskReporterSettings(True), client_factory=FakeClient, clock=lambda: clock[0])
        state.pskreporter = service
        await service.start()
        client = service.client; client.connect(); await service.tick()
        assert set(client.topics) == {topic_for('N0CALL'), topic_for('K2OTHER')}
        assert service.status == 'connected'
        history, focus = deepcopy(state.history), state.call
        for raw in (spot(), spot(t=NOW-90), spot(f=21074000), spot(sc='K2OTHER')):
            client.inbox.put_nowait(('spot', raw))
        await service.tick()
        assert len(service.cache) == 3
        assert service.cache[('N0CALL','20m','K1FOCUS')]['heardAt'] == (NOW-60)*1000
        assert state.history == history and state.call == focus
        # Browser snapshots carry independent copies, and reconnect subscribes again.
        snapshot = service.snapshot(); snapshot['spots'][0]['receiver'] = 'CHANGED'
        assert all(s['receiver'] == 'K1FOCUS' for s in service.cache.values())
        assert len(snapshot['spots']) == 1
        state.history[0]['band'] = '15m'
        assert [s['band'] for s in service.snapshot()['spots']] == ['15m']
        state.history[0]['band'] = '20m'
        assert len(client.topics) == 2  # Browsing/filtering does not resubscribe.
        client.connect(); await service.tick(); assert len(client.topics) == 4
        # Refused subscriptions retry with a delay, rather than claiming coverage.
        client.inbox.put_nowait(('subscription_error', None)); await service.tick()
        assert service.status == 'error' and len(client.topics) == 4
        clock[0] += 60; await service.tick(); assert len(client.topics) == 6
        client.inbox.put_nowait(('subscribed', None)); await service.tick()
        assert service.status == 'connected' and not service.error
        del state.rigs['B']; await service.tick()
        assert client.removed == [topic_for('K2OTHER')]
        assert len(service.cache) == 2
        # Shrinking the display window keeps the one-hour buffer for re-expansion.
        await service.configure(PskReporterSettings(True, window_minutes=5))
        assert len(service.cache) == 2 and service.client is client
        monkeypatch.setattr('backend.pskreporter.CACHE_LIMIT', 2)
        service.ingest(spot(rc='K3NEW', t=NOW-10)); assert len(service.cache) == 2 and service.evicted == 1
        clock[0] += 3600; await service.tick(); assert not service.cache
        await service.configure(PskReporterSettings())
        assert service.status == 'disabled' and client.stopped
        await service.stop(); state.close()
    asyncio.run(scenario())


def test_wait_for_identity_and_explicit_override_without_network(tmp_path):
    async def scenario():
        state = WorkspaceState(tmp_path/'workspace.sqlite3')
        service = PskReporterService(state, PskReporterSettings(True), client_factory=FakeClient)
        await service.start(); assert service.status == 'waiting' and service.client is None
        await service.configure(PskReporterSettings(True, 'N0CALL'))
        assert service.calls == {'N0CALL'} and service.client is not None
        await service.stop(); state.close()
    asyncio.run(scenario())


def test_config_api_defaults_validation_and_other_settings_preserved(tmp_path):
    config = tmp_path/'config.toml'; config.write_text(Path('config.example.toml').read_text().split('[pskreporter]')[0])
    assert load_config(config).pskreporter == PskReporterSettings()
    before = load_config(config)
    state = WorkspaceState(tmp_path/'workspace.sqlite3')
    app = create_app(state=state, config_path=config, serve_frontend=False)
    # Enable only with no radio identity: this test must never connect upstream.
    with TestClient(app, base_url='http://127.0.0.1') as api:
        body = dict(enabled=True, callsign='', window_minutes=30)
        assert api.put('/api/pskreporter', json=body, headers={'Origin':'https://other.invalid'}).status_code == 403
        for invalid in ({'window_minutes':1}, {'enabled':1}, {'callsign':'+'}, {'callsign':'n0call'}, {'extra':1}):
            assert api.put('/api/pskreporter', json=body | invalid).status_code == 422
        response = api.put('/api/pskreporter', json=body)
        assert response.status_code == 200
        assert response.json()['pskreporter']['status'] == 'waiting'
        assert response.json()['pskreporter']['config'] == body
        assert replace(load_config(config), pskreporter=before.pskreporter) == before
        assert api.put('/api/pskreporter', json=body | {'enabled':False}).status_code == 200
        assert api.get('/api/snapshot').json()['pskreporter']['spots'] == []
