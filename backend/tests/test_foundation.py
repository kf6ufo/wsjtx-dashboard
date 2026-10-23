from fastapi.testclient import TestClient
import pytest
from backend.app import create_app
from backend.foundation import FoundationState, RIGS
from backend.receiver import Settings


def test_sample_order_provenance_persistence_and_settings(tmp_path):
    path = tmp_path / 'data/workspace.sqlite3'
    state = FoundationState(path)
    queue = state.subscribe()
    assert queue.get_nowait()['sample']
    state.select_sample('DL1DEMO', RIGS[0][0], at=100)
    state.select_sample('JA2HDE', RIGS[1][0], at=101)
    assert queue.qsize() == 1  # Coalesces complete snapshots for a slow client.
    before = state.snapshot()['history']
    assert state.browse('DL1DEMO')
    after = state.snapshot()['history']
    assert [x['call'] for x in after] == [x['call'] for x in before]
    assert [(x['selectedAt'], x['rigId'], x['band']) for x in before] == [(x['selectedAt'], x['rigId'], x['band']) for x in after]
    assert len({x['call'] for x in after}) == len(after)
    state.database.close()
    restored = FoundationState(path)
    assert restored.call == 'DL1DEMO'
    assert restored.history == after
    assert restored.epoch != state.epoch
    assert restored.subscribe().get_nowait()['call'] == 'DL1DEMO'
    restored.database.close()


def test_http_validation_and_real_saved_preferences(tmp_path):
    path = tmp_path / 'workspace.sqlite3'
    with TestClient(create_app(Settings(), FoundationState(path), serve_frontend=False)) as client:
        assert client.get('/api/snapshot').json()['receiver']['status'] == 'disabled'
        assert client.post('/api/sample/select', json={'call': 'UNKNOWN', 'rigId': RIGS[0][0]}).status_code == 422
        assert client.post('/api/sample/select', json={'call': 'JA2HDE', 'rigId': RIGS[2][0]}).status_code == 200
        preferences = dict(title='Test desk', appearance='light', radioStrip=True)
        assert client.put('/api/settings', json=preferences).json()['preferences'] == preferences
        assert client.put('/api/settings', json=dict(preferences, appearance='bad')).status_code == 422
        assert client.put('/api/settings', json=preferences, headers={'Origin': 'http://foreign.example'}).status_code == 403
        assert client.post('/api/focus', json={'call': 'MISSING'}).status_code == 404
        assert client.get('/fixture/packet').status_code == 404
    restored = FoundationState(path)
    assert restored.preferences == preferences
    assert restored.history[0]['rigId'] == RIGS[2][0]
    restored.database.close()


def test_failed_disk_write_does_not_publish_unsaved_change(tmp_path):
    state = FoundationState(tmp_path / 'workspace.sqlite3')
    before = state.snapshot()
    state.database.execute('PRAGMA query_only = ON')
    import sqlite3
    with pytest.raises(sqlite3.OperationalError):
        state.select_sample('W7DEMO', RIGS[0][0])
    assert state.snapshot() == before
    state.database.close()
