"""Native configuration/installation contract; no external station access."""
from pathlib import Path
import importlib.util
import shutil
from types import SimpleNamespace
import pytest
from backend.config import load_config
from backend import server

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('install_native', ROOT / 'scripts/install-native.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def test_safe_defaults():
    config = load_config(ROOT / 'config.example.toml')
    assert (config.host, config.port) == ('127.0.0.1', 8787)
    assert not config.receiver.enabled


@pytest.mark.parametrize('old,new', [('port = 8787', 'port = 80'), ('port = 8787', 'port = true'),
    ('enabled = false', 'enabled = "on"'), ('239.255.0.73', '10.176.1.5'),
    ('host = "127.0.0.1"', 'host = "0.0.0.0"'), ('host = "127.0.0.1"', 'host = "8.8.8.8"'),
    ('[http]', '[wrong]')])
def test_invalid_config(tmp_path, old, new):
    path = tmp_path / 'config.toml'
    path.write_text((ROOT / 'config.example.toml').read_text().replace(old, new))
    with pytest.raises(ValueError, match='Configuration error'):
        load_config(path)


def test_step0_config_is_accepted_with_receiver_defaults(tmp_path):
    config = tmp_path / 'config.toml'
    config.write_text('[http]\nhost="127.0.0.1"\nport=8787\n[wsjtx]\nenabled=false\ngroup="239.255.0.73"\nport=2238\ninterface="127.0.0.1"\n')
    parsed = load_config(config)
    assert parsed.receiver.listen == '0.0.0.0'
    assert parsed.receiver.retention == 200
    assert not parsed.receiver.enabled


def test_repeat_install_preserves_config_and_workspace(tmp_path, monkeypatch):
    shutil.copyfile(ROOT / 'config.example.toml', tmp_path / 'config.example.toml')
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    monkeypatch.setattr(installer.shutil, 'which', lambda name: '/fake/' + name)
    monkeypatch.setattr(installer.subprocess, 'check_output', lambda *a, **k: 'v24.21.0')
    calls = []
    monkeypatch.setattr(installer.subprocess, 'run', lambda command, **kwargs: calls.append(command))
    assert installer.main() == 0
    config = tmp_path / 'config.toml'
    config.write_text(config.read_text().replace('8787', '8789'))
    (tmp_path / 'data').mkdir()
    workspace = tmp_path / 'data/workspace.sqlite3'
    workspace.write_bytes(b'untouched-workspace')
    before = config.read_bytes()
    assert installer.main() == 0
    assert config.read_bytes() == before
    assert workspace.read_bytes() == b'untouched-workspace'
    assert len(calls) == 8
    assert not any('sudo' in cmd or 'systemctl' in cmd for cmd in calls)
