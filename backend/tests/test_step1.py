"""Step 1 tests use isolated local UDP only; never transmit to station services."""
import base64
from dataclasses import asdict
import json
import socket
import time
from fastapi.testclient import TestClient
import pytest
from backend.app import create_app
from backend.config import load_config, save_receiver_config
from backend.foundation import FoundationState
from backend.protocol import parse_packet
from backend.receiver import Settings, ingest
from backend.workspace import WorkspaceState
from .fixtures import status, decode, header


def test_upgrade_preserves_sample_preferences_and_separates_radio_history(tmp_path):
    path = tmp_path / 'workspace.sqlite3'
    step0 = FoundationState(path)
    step0.preferences['title'] = 'My custom desk'
    step0.browse('DL1DEMO')
    original = step0.snapshot()
    step0.database.close()
    state = WorkspaceState(path)
    assert state.sample and state.history == original['history']
    assert state.preferences == original['preferences']
    state.enter_radio_workspace()
    ingest(status(call='N0BASE', rig='A'), state, ('127.0.0.1', 1234))
    assert not state.history
    ingest(status(call='W1ACT', rig='A'), state, ('127.0.0.1', 1234))
    state.close()
    restored = WorkspaceState(path)
    assert not restored.sample and restored.call == 'W1ACT'
    assert restored.preferences['title'] == 'My custom desk'
    assert restored.rigs == {} and restored.previous == {}
    archived = json.loads(restored.database.execute('SELECT payload FROM workspace WHERE id=1').fetchone()[0])
    assert archived['history'] == original['history']
    restored.close()


def test_diagnostics_bounds_original_bytes_filters_and_no_disk_commit_for_decodes(tmp_path):
    state = WorkspaceState(tmp_path / 'workspace.sqlite3')
    state.enter_radio_workspace()
    state.configure_receiver(Settings(retention=50))
    ingest(status(call='N0BASE'), state)
    ingest(status(), state)
    commits = state.database.total_changes
    for _ in range(90):
        ingest(decode(), state, ('127.0.0.2', 1234))
    assert state.database.total_changes == commits
    raw = header(kind=999) + b'unknown binary\x00\xff'
    ingest(raw, state, ('127.0.0.3', 4321))
    ingest(b'broken', state, ('127.0.0.4', 4322))
    rows = state.diagnostic_rows()['rows']
    assert len(rows) == 50 and 'raw' not in rows[0] and 'fields' not in rows[0]
    assert rows[0]['error'] == 'invalid magic'
    detail = state.diagnostic_detail(rows[1]['id'])
    assert detail['name'] == 'Unknown'
    assert base64.b64decode(detail['rawBase64']) == raw
    assert detail['source'] == '127.0.0.3:4321'
    assert state.call == 'JA2HDE'
    history = state.snapshot()['history']
    counters = state.counters.copy()
    state.clear_diagnostics()
    assert not state.diagnostics and state.history == history and state.counters == counters
    assert state.diagnostic_rows()['generation'] == 1
    state.close()


def test_all_packet_last_seen_timeout_and_close_baselines(tmp_path):
    state = WorkspaceState(tmp_path / 'workspace.sqlite3')
    state.enter_radio_workspace()
    ingest(status(call='N0BASE', rig='A'), state)
    ingest(status(call='W1ACT', rig='A'), state)
    state.expire_instances(now=state.rigs['A']['lastSeen'] + 90001)
    assert not state.rigs['A']['online'] and 'A' not in state.previous
    ingest(status(call='K2BACK', rig='A'), state)
    assert state.call == 'W1ACT'  # Reappearance is a baseline.
    ingest(status(call='K3NEXT', rig='A'), state)
    before = state.rigs['A']['lastSeen']
    ingest(decode(rig='A'), state, ('127.0.0.2', 4242))
    assert state.rigs['A']['lastSeen'] >= before
    assert state.rigs['A']['source'] == '127.0.0.2:4242'
    ingest(header(kind=6, rig='A'), state)
    assert not state.rigs['A']['online']
    ingest(status(call='K4NEW', rig='A'), state)
    assert state.call == 'K3NEXT'
    state.close()


def test_packet_details_have_parsed_status_and_decode_fields():
    packet = parse_packet(status())
    assert packet.fields['dxCall'] == 'JA2HDE'
    assert packet.fields['frequency'] == 14074000 and packet.schema == 2
    assert 'transmitting' in packet.fields and 'dxGrid' in packet.fields
    assert parse_packet(decode()).fields['message']


@pytest.mark.parametrize('changes', [dict(retention=501), dict(retention=True), dict(listen='bad'), dict(port=True),
    dict(group='127.0.0.1'), dict(enabled=True, interface=''), dict(interface='0.0.0.0'), dict(group=123)])
def test_bad_receiver_settings(changes):
    with pytest.raises(ValueError):
        Settings(**changes)


def test_save_receiver_is_atomic_and_preserves_comments_and_http(tmp_path):
    path = tmp_path / 'config.toml'
    source = '[http]\n# HTTP stays exactly as configured\nhost="127.0.0.1"\nport=8789\n[wsjtx]\n# operator comment\nenabled=false\nport=2238\ngroup="239.255.0.73"\ninterface="127.0.0.1"\n'
    path.write_text(source)
    settings = Settings(enabled=True, listen='127.0.0.1', group='', interface='', port=12345, retention=100)
    save_receiver_config(path, settings)
    assert path.read_text().split('[wsjtx]')[0] == source.split('[wsjtx]')[0]
    assert '# operator comment' in path.read_text()
    assert load_config(path).receiver == settings
    assert not list(tmp_path.glob('.receiver-*'))


def test_real_loopback_udp_runtime_and_settings_restart(tmp_path):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserve:
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
    config = tmp_path / 'config.toml'
    config.write_text('[http]\nhost="127.0.0.1"\nport=8787\n[wsjtx]\nenabled=false\nport=2238\ngroup="239.255.0.73"\ninterface="127.0.0.1"\n')
    state = WorkspaceState(tmp_path / 'data/workspace.sqlite3')
    with TestClient(create_app(Settings(), state, serve_frontend=False, config_path=config)) as client, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        settings = Settings(enabled=True, group='', interface='', listen='127.0.0.1', port=port, retention=50)
        response = client.put('/api/receiver', json=asdict(settings))
        assert response.status_code == 200
        assert response.json()['receiver']['status'] == 'listening'
        assert not response.json()['history']
        assert client.post('/api/sample/select', json={'call': 'JA2HDE', 'rigId': 'WSJT-X - IC7300'}).status_code == 422
        assert client.put('/api/receiver', json=asdict(settings), headers={'Origin': 'http://foreign.example'}).status_code == 403

        def send(data):
            before = client.get('/api/snapshot').json()['counters']['packets']
            sender.sendto(data, ('127.0.0.1', port))
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                snapshot = client.get('/api/snapshot').json()
                if snapshot['counters']['packets'] > before:
                    return snapshot
                time.sleep(.01)
            pytest.fail('Local UDP packet did not arrive')

        assert not send(status(call='N0BASE', rig='A'))['history']
        assert not send(status(call='K1BASE', rig='B'))['history']
        assert send(status(call='W1ACT', rig='A'))['call'] == 'W1ACT'
        assert send(status(call='K2ACT', rig='B'))['call'] == 'K2ACT'
        client.post('/api/focus', json={'call': 'W1ACT'})
        before = client.get('/api/snapshot').json()
        after = send(decode())
        assert after['history'] == before['history'] and after['call'] == 'W1ACT'
        assert client.delete('/api/diagnostics').json()['rows'] == []
        assert client.get('/api/snapshot').json()['history'] == before['history']
        assert client.post('/api/receiver/restart').json()['receiver']['status'] == 'listening'
        assert send(status(call='K3BASE', rig='A'))['call'] == 'W1ACT'
        assert send(status(call='K4ACT', rig='A'))['call'] == 'K4ACT'
        disabled = asdict(settings) | {'enabled': False}
        assert client.put('/api/receiver', json=disabled).json()['receiver']['status'] == 'disabled'
        assert not client.get('/api/snapshot').json()['sample']
        assert load_config(config).receiver.enabled is False


def test_malformed_payload_retains_valid_header_identity_without_selecting(tmp_path):
    state = WorkspaceState(tmp_path / 'workspace.sqlite3')
    state.enter_radio_workspace()
    ingest(header(rig='Radio A', kind=1) + b'broken payload', state, ('127.0.0.1', 2222))
    row = state.diagnostic_rows()['rows'][0]
    assert row['instance'] == 'Radio A' and row['kind'] == 1 and row['schema'] == 2
    assert row['error']
    assert state.rigs == {} and state.history == []
    ingest(header(rig='Radio B', kind=1, schema=99), state)
    row = state.diagnostic_rows()['rows'][0]
    assert row['schema'] == 99 and row['instance'] == 'Radio B'
    assert row['error'] == 'unsupported schema'
    state.close()
