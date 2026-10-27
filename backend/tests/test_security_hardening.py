"""Host/origin boundaries and private storage; isolated fixtures only."""
from contextlib import contextmanager
import os
import stat

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import load_config
from backend.foundation import FoundationState
from backend.private_storage import private_database, private_directory, private_file
from backend.qso_delivery import DeliveryQueue
from backend.receiver import Settings, ingest
from backend.workspace import WorkspaceState
from .fixtures import status
from .test_deployment import installer, ROOT
from .test_qso_architecture import fields


@contextmanager
def normal_umask():
    previous = os.umask(0o022)
    try:
        yield
    finally:
        os.umask(previous)


@pytest.fixture
def http_app(tmp_path):
    config = tmp_path / 'config.toml'
    config.write_text((ROOT / 'config.example.toml').read_text().replace('host = "127.0.0.1"', 'host = "192.168.50.20"'))
    return create_app(Settings(), FoundationState(tmp_path / 'data/workspace.sqlite3'), config_path=config, serve_frontend=False)


@pytest.mark.parametrize('host', ['localhost', 'localhost:8799', 'LOCALHOST', '127.0.0.1', '127.0.0.1:8799', '192.168.50.20:8799'])
def test_expected_hosts_preserve_snapshot_and_settings(http_app, host):
    # Client address is independent of the requested server's Host header.
    with TestClient(http_app, base_url=f'http://{host}', client=('192.168.50.30', 50000)) as client:
        assert client.get('/api/snapshot').status_code == 200
        origin = f'http://{host.lower()}'
        response = client.put('/api/settings', json={'title':'Trusted LAN desk','appearance':'dark','radioStrip':False}, headers={'Origin':origin})
        assert response.status_code == 200
        assert response.json()['preferences']['title'] == 'Trusted LAN desk'


@pytest.mark.parametrize('host', ['attacker.example', 'localhost.attacker.example', '127.0.0.1.attacker.example', '192.168.50.21', '0.0.0.0', 'testserver'])
def test_unexpected_hosts_rejected_before_api_and_stream(http_app, host):
    before = http_app.state.focus.snapshot()
    with TestClient(http_app, base_url='http://localhost') as client:
        headers = {'Host':host, 'Origin':f'http://{host}', 'X-Forwarded-Host':'localhost'}
        for route in ['/api/snapshot', '/api/events']:
            assert client.get(route, headers=headers).status_code == 400
        assert client.put('/api/settings', content=b'invalid json', headers=headers).status_code == 400
        assert not http_app.state.focus.subscribers
        assert http_app.state.focus.preferences == before['preferences']


@pytest.mark.parametrize('headers', [{'Origin':'http://foreign.example'}, {'Origin':'http://localhost:9999'}, {'Sec-Fetch-Site':'cross-site'}])
def test_trusted_host_does_not_bypass_existing_origin_checks(http_app, headers):
    with TestClient(http_app, base_url='http://localhost') as client:
        before = http_app.state.focus.snapshot()['preferences']
        assert client.put('/api/settings', json={'title':'Blocked','appearance':'light','radioStrip':False}, headers=headers).status_code == 403
        assert http_app.state.focus.preferences == before


def test_default_app_does_not_accept_arbitrary_lan_addresses():
    with TestClient(create_app(serve_frontend=False), base_url='http://127.0.0.1') as client:
        assert client.get('/api/snapshot', headers={'Host':'192.168.50.20'}).status_code == 400


def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


def test_all_runtime_stores_and_sidecars_are_private(tmp_path):
    config = tmp_path / 'config.toml'
    config.write_text((ROOT / 'config.example.toml').read_text())
    with normal_umask():
        state = WorkspaceState(tmp_path / 'data/workspace.sqlite3')
        with TestClient(create_app(Settings(), state, config_path=config, serve_frontend=False), base_url='http://localhost'):
            data = tmp_path / 'data'
            assert {p.name for p in data.glob('*.sqlite3')} == {'workspace.sqlite3','delivery.sqlite3','observations.sqlite3','forwarding.sqlite3'}
            assert all(mode(p) == 0o600 for p in data.iterdir() if p.is_file())
            assert mode(data) == 0o700


def test_new_private_paths_and_existing_sidecars_are_owner_only(tmp_path):
    unrelated = tmp_path / 'unrelated'; unrelated.mkdir(mode=0o755)
    unrelated.chmod(0o755)
    with normal_umask():
        private_directory(tmp_path / 'data/nested')
        database = tmp_path / 'data/nested/test.sqlite3'
        db = private_database(database)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE retained (value TEXT)')
        db.execute("INSERT INTO retained VALUES ('pending')"); db.commit()
        for path in database.parent.iterdir():
            assert mode(path) == 0o600
        sidecar = database.with_name(database.name + '-wal')
        sidecar.chmod(0o644)
        before = sidecar.read_bytes()
        reopened = private_database(database)
        assert sidecar.read_bytes() == before and mode(sidecar) == 0o600
        assert reopened.execute('SELECT value FROM retained').fetchone() == ('pending',)
        reopened.close(); db.close()
    assert mode(tmp_path / 'data') == mode(database.parent) == 0o700
    assert mode(unrelated) == 0o755


def test_private_paths_do_not_follow_symlinks_or_touch_operator_files(tmp_path):
    operator = tmp_path / 'operator'; operator.mkdir(mode=0o755)
    operator.chmod(0o755)
    target = operator / 'existing.adi'; target.write_bytes(b'operator ADIF stays unchanged')
    before, owner, permissions = target.read_bytes(), target.stat().st_uid, mode(target)
    link = tmp_path / 'linked.sqlite3'; link.symlink_to(target)
    with pytest.raises(OSError): private_database(link)
    directory = tmp_path / 'linked-data'; directory.symlink_to(operator, target_is_directory=True)
    with pytest.raises(OSError): private_directory(directory)
    fifo = tmp_path / 'not-a-regular-file'; os.mkfifo(fifo)
    with pytest.raises(ValueError): private_file(fifo)
    assert target.read_bytes() == before and target.stat().st_uid == owner and mode(target) == permissions
    assert mode(operator) == 0o755


def test_repeat_install_and_restart_preserve_config_history_queue_receipts_and_adif(tmp_path, monkeypatch):
    (tmp_path / 'config.example.toml').write_text((ROOT / 'config.example.toml').read_text())
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    monkeypatch.setattr(installer.shutil, 'which', lambda name: '/fake/' + name)
    monkeypatch.setattr(installer.subprocess, 'check_output', lambda *a, **k: 'v24.21.0')
    monkeypatch.setattr(installer.subprocess, 'run', lambda *a, **k: None)
    with normal_umask():
        assert installer.main() == 0
        config = tmp_path / 'config.toml'
        assert mode(config) == 0o600
        config.write_text(config.read_text().replace('port = 8787', 'port = 18897'))
        state = WorkspaceState(tmp_path / 'data/workspace.sqlite3')
        state.enter_radio_workspace()
        for rig, call in [('WSJT-X - IC7300','K1ALPHA'), ('WSJT-X - IC9100','K2BRAVO')]:
            ingest(status(call='N0BASE', rig=rig), state)
            ingest(status(call=call, rig=rig), state)
        history = state.snapshot()['history']
        state.close()
        queue_path = tmp_path / 'data/delivery.sqlite3'
        queue = DeliveryQueue(queue_path)
        pending = queue.capture('Rig A', fields(), {}, {'adif':{'path':'/fictional/pending.adi'}})
        delivered = queue.capture('Rig B', fields('K3DONE'), {}, {'adif':{'path':'/fictional/delivered.adi'}})
        queue.delivered(delivered, 'adif', 'fixture-receipt')
        rows = queue.execute('SELECT * FROM qso_delivery ORDER BY id')
        queue.db.close()
        adif = tmp_path / 'operator.adi'; adif.write_bytes(b'Unchanged operator-owned ADIF')
        adif.chmod(0o644)
        before = {p:p.read_bytes() for p in [config, queue_path, adif, tmp_path / 'data/workspace.sqlite3']}
        owners = {p:p.stat().st_uid for p in before}
        config.chmod(0o644)  # Earlier installs/manual edits can have broader modes.
        assert installer.main() == 0
        assert all(p.read_bytes() == content for p,content in before.items())
        assert mode(config) == 0o600 and mode(adif) == 0o644
        for _ in range(2):
            restored = WorkspaceState(tmp_path / 'data/workspace.sqlite3')
            assert restored.snapshot()['history'] == history
            restored.close()
            queue = DeliveryQueue(queue_path)
            assert queue.execute('SELECT * FROM qso_delivery ORDER BY id') == rows
            assert queue.capture('Rig A', fields(), {}, {'adif':{'path':'/fictional/pending.adi'}}) == pending
            assert queue.capture('Rig B', fields('K3DONE'), {}, {'adif':{'path':'/fictional/delivered.adi'}}) == delivered
            assert len(queue.execute('SELECT id FROM qso_outbox')) == 2
            queue.db.close()
        assert adif.read_bytes() == before[adif]
        assert config.read_bytes() == before[config]
        assert all(p.stat().st_uid == owner for p,owner in owners.items())
        assert all(mode(p) == 0o600 for p in (tmp_path / 'data').glob('*.sqlite3'))
        assert mode(tmp_path / 'data') == 0o700
