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
from backend.pskreporter import MqttInbox, PskReporterService, inspect_spot, parse_spot, topic_for
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


@pytest.mark.parametrize(('payload','reason'), [(b'bad JSON','malformed_json'), (spot(sc='K2OTHER'),'wrong_sender'),
    (spot(rl=''),'invalid_grid'), (spot(t=NOW-4000),'too_old'), (spot(t=NOW+90),'future_timestamp'),
    (spot(f=123),'unsupported_frequency'), (spot(t=None),'invalid_timestamp')])
def test_diagnostic_rejection_reasons(payload, reason):
    result, actual, preview = inspect_spot(payload, {'N0CALL'}, NOW)
    assert result is None and actual == reason
    assert not set(preview) - {'sc','rc','rl','f','md','rp','t','t_tx'}


def test_wire_counters_capture_overflow_and_oversized_messages_without_unbounded_retention():
    import queue
    inbox = MqttInbox(lambda: NOW)
    for _ in range(512): inbox.put_nowait(('spot',spot()))
    with pytest.raises(queue.Full): inbox.put_nowait(('spot',spot()))
    with pytest.raises(queue.Full): inbox.put_nowait(('disconnected','fixture disconnect'))
    inbox.put_nowait(('spot',b'x'*4097))
    metrics = inbox.metrics()
    assert inbox.qsize() == 512
    assert metrics['received'] == 514 and metrics['queueDropped'] == 1 and metrics['controlDropped'] == 1
    assert metrics['oversized'] == 1 and metrics['lastMessageAt'] == NOW*1000


def test_diagnostics_show_acknowledgements_filtering_cache_and_clear_independence(tmp_path):
    async def scenario():
        state = WorkspaceState(tmp_path/'workspace.sqlite3'); state.enter_radio_workspace()
        state.call = 'K1FOCUS'
        state.history = [dict(call='K1FOCUS',rigId='A',stationCall='N0CALL',band='12m',selectedAt=NOW*1000,recency=1)]
        service = PskReporterService(state, PskReporterSettings(True,'N0CALL'),client_factory=FakeClient,clock=lambda:NOW)
        await service.start(); service.client.connect(); await service.tick()
        assert service.diagnostics()['subscriptions'][0]['status'] == 'pending'
        service.inbox.put_nowait(('subscribed',dict(mid=1,reason='Granted QoS 0')))
        for payload in (spot(extra_private_field='never retain this'),spot(),spot(rl='ZZ99'),spot(t=NOW-4000)):
            service.inbox.put_nowait(('spot',dict(payload=payload,topic=topic_for('N0CALL'))))
        before_history = deepcopy(state.history)
        await service.tick()
        d = service.diagnostics()
        assert d['subscriptions'][0]['status'] == 'acknowledged'
        assert d['counts']['received'] == 4 and d['counts']['accepted'] == 1 and d['counts']['duplicates'] == 1
        assert d['counts']['rejected'] == 2 and d['rejectionReasons'] == {'invalid_grid':1,'too_old':1}
        assert d['counts']['cached'] == 1 and d['counts']['matchingWindow'] == 0
        assert d['bands'] == [dict(sender='N0CALL',band='20m',count=1)]
        assert 'cached, but none match' in d['explanation']
        assert 'never retain this' not in json.dumps(d)
        state.history[0]['band'] = '20m'
        assert service.diagnostics()['focus']['focusHeard']
        state.history = before_history
        counts = deepcopy(d['counts'])
        service.clear_diagnostics()
        d = service.diagnostics()
        assert not d['events'] and not d['reports'] and d['counts'] == counts
        assert len(service.cache) == 1 and state.history == before_history
        for _ in range(150): service.ingest(spot())
        for _ in range(75): service.event('fixture','bounded event')
        d = service.diagnostics(); assert len(d['reports']) == 100 and len(d['events']) == 50
        d['reports'][0]['preview']['sc'] = 'MUTATED'
        assert service.diagnostics()['reports'][0]['preview']['sc'] == 'N0CALL'
        service.inbox.put_nowait(('disconnected','Fixture network outage')); service.client.connected = False
        await service.tick()
        assert service.diagnostics()['counts']['disconnects'] == 1
        assert service.diagnostics()['subscriptions'][0]['status'] == 'waiting'
        assert service.diagnostics()['lastDisconnectedAt'] == NOW*1000
        await service.stop(); state.close()
    asyncio.run(scenario())


def test_diagnostics_api_disabled_state_and_same_origin_clear(tmp_path):
    config = tmp_path/'config.toml'; config.write_text(Path('config.example.toml').read_text())
    state = WorkspaceState(tmp_path/'workspace.sqlite3')
    with TestClient(create_app(state=state,config_path=config,serve_frontend=False),base_url='http://127.0.0.1') as api:
        data = api.get('/api/pskreporter/diagnostics').json()
        assert data['status'] == 'disabled' and 'disabled' in data['explanation']
        assert data['subscriptions'] == [] and data['counts']['received'] == 0
        state.pskreporter.event('fixture','clear just this event')
        before = config.read_bytes(); history = deepcopy(state.history)
        assert api.delete('/api/pskreporter/diagnostics',headers={'Origin':'https://other.invalid'}).status_code == 403
        assert api.get('/api/pskreporter/diagnostics').json()['events']
        assert not api.delete('/api/pskreporter/diagnostics').json()['events']
        assert state.history == history and config.read_bytes() == before
