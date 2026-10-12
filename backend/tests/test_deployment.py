"""Offline deployment checks. No sudo, package downloads or systemd mutations."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
import pytest
from backend.config import load_config
from backend import server

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('install_ubuntu', ROOT / 'scripts/install-ubuntu.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def test_known_station_configuration():
    config = load_config(ROOT / 'config.example.toml')
    assert (config.host, config.port) == ('10.176.1.6', 8000)
    assert config.receiver.enabled
    assert (config.receiver.group, config.receiver.port, config.receiver.interface) == ('239.255.0.73', 2238, '10.176.1.6')


@pytest.mark.parametrize('old,new', [('port = 8000', 'port = 80'), ('port = 8000', 'port = true'),
    ('enabled = true', 'enabled = "on"'), ('239.255.0.73', '10.176.1.5'),
    ('host = "10.176.1.6"', 'host = "0.0.0.0"'), ('host = "10.176.1.6"', 'host = "8.8.8.8"'),
    ('interface = "10.176.1.6"', 'interface = "0.0.0.0"'), ('[http]', '[wrong]')])
def test_invalid_configuration_fails_clearly(tmp_path, old, new):
    path = tmp_path / 'config.toml'
    path.write_text((ROOT / 'config.example.toml').read_text().replace(old, new))
    with pytest.raises(ValueError, match='Configuration error'):
        load_config(path)


def test_missing_configuration_and_frontend_fail_before_start(tmp_path, monkeypatch, capsys):
    with pytest.raises(ValueError, match='Configuration error'):
        load_config(tmp_path / 'missing.toml')
    config = tmp_path / 'config.toml'
    shutil.copyfile(ROOT / 'config.example.toml', config)
    monkeypatch.setattr(server, 'ROOT', tmp_path)
    monkeypatch.setattr('sys.argv', ['server', '--config', str(config)])
    assert server.main() == 1
    assert 'Built frontend missing' in capsys.readouterr().err


def test_server_reads_http_and_radio_from_one_file(tmp_path, monkeypatch):
    (tmp_path / 'dist').mkdir()
    (tmp_path / 'dist/index.html').write_text('dashboard')
    config = tmp_path / 'config.toml'
    config.write_text((ROOT / 'config.example.toml').read_text().replace('8000', '8765').replace('enabled = true', 'enabled = false'))
    monkeypatch.setattr(server, 'ROOT', tmp_path)
    monkeypatch.setattr('sys.argv', ['server', '--config', str(config)])
    captured = {}
    def run(app, **kwargs):
        captured.update(kwargs)
        assert app.state.focus.receiver['status'] == 'disabled'
    monkeypatch.setattr('uvicorn.run', run)
    assert server.main() == 0
    assert captured == dict(host='10.176.1.6', port=8765, workers=1)


def test_unit_runs_as_user_with_quoted_paths_and_no_shell_config(tmp_path):
    root = tmp_path / 'station % desk'
    (root / 'deploy').mkdir(parents=True)
    shutil.copyfile(ROOT / 'deploy/wsjtx-dashboard.service', root / 'deploy/wsjtx-dashboard.service')
    unit = installer.render_service(root, 'jerry', 'jerry')
    assert 'User=jerry\nGroup=jerry' in unit
    assert 'station %% desk/.venv/bin/python" -m backend.server --config "' in unit
    assert 'Restart=on-failure' in unit and 'ProtectHome=read-only' in unit
    assert 'EnvironmentFile' not in unit and '@ROOT@' not in unit
    with pytest.raises(ValueError):
        installer.unit_quote('bad\npath')


@pytest.fixture
def simulated_install(tmp_path, monkeypatch):
    (tmp_path / 'deploy').mkdir()
    shutil.copyfile(ROOT / 'deploy/wsjtx-dashboard.service', tmp_path / 'deploy/wsjtx-dashboard.service')
    shutil.copyfile(ROOT / 'config.example.toml', tmp_path / 'config.toml')
    calls = []
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    unit = tmp_path / 'installed.service'
    monkeypatch.setattr(installer, 'UNIT_PATH', unit)
    monkeypatch.setattr(installer, 'ensure_host', lambda: None)
    monkeypatch.setattr(installer, 'check_stopped', lambda _: None)
    monkeypatch.setattr(installer, 'install_packages', lambda: None)
    monkeypatch.setattr(installer, 'prepare_node', lambda: tmp_path / 'node/bin')
    monkeypatch.setattr(installer.pwd, 'getpwuid', lambda _: SimpleNamespace(pw_name='jerry', pw_gid=123))
    monkeypatch.setattr(installer.grp, 'getgrgid', lambda _: SimpleNamespace(gr_name='jerry'))
    def run(*args, **kwargs):
        calls.append((args, kwargs))
        if args[:3] == ('npm', 'run', 'build'):
            (tmp_path / 'dist').mkdir(exist_ok=True)
            (tmp_path / 'dist/index.html').write_text('built frontend')
        if args[:2] == ('sudo', 'install'):
            shutil.copyfile(args[4], args[5])
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(installer, 'run', run)
    return tmp_path, calls, run


def test_repeat_install_preserves_config_and_builds_without_releases(simulated_install):
    root, calls, _ = simulated_install
    config = root / 'config.toml'
    config.write_text(config.read_text().replace('8000', '8765'))
    before = config.read_bytes()
    installer.install()
    installer.install()
    assert config.read_bytes() == before
    assert (root / 'dist/index.html').is_file()
    assert 'User=jerry' in (root / 'installed.service').read_text()
    commands = [call for call, _ in calls]
    assert commands.count(('npm', 'ci')) == 2
    assert commands.count(('npm', 'run', 'build')) == 2
    assert commands.count(('python3', '-m', 'venv', '.venv')) == 2
    assert commands.count(('sudo', 'systemctl', 'daemon-reload')) == 2
    assert not any('start' in command or 'stop' in command or 'gh' in command or 'checkout' in command for command in commands)
    assert all(options['env']['PATH'].startswith(str(root / 'node/bin')) for command, options in calls if command[0] == 'npm')


def test_build_failure_does_not_update_service_or_change_config(simulated_install, monkeypatch, capsys):
    root, calls, original = simulated_install
    before = (root / 'config.toml').read_bytes()
    def fail(*args, **kwargs):
        if args[:3] == ('npm', 'run', 'build'):
            raise subprocess.CalledProcessError(1, args)
        return original(*args, **kwargs)
    monkeypatch.setattr(installer, 'run', fail)
    assert installer.main() == 1
    assert 'Installation failed' in capsys.readouterr().err
    assert (root / 'config.toml').read_bytes() == before
    assert not (root / 'installed.service').exists()
    assert not any('daemon-reload' in command for command, _ in calls)


def test_running_service_refused_before_changes(monkeypatch):
    monkeypatch.setattr(installer.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout='active\n', returncode=0))
    with pytest.raises(ValueError, match='sudo systemctl stop'):
        installer.check_stopped(load_config(ROOT / 'config.example.toml'))


def test_supported_node_requires_supported_lts_version():
    assert installer.supported_node('v24.21.0\n')
    assert installer.supported_node('v24.15.0')
    assert not installer.supported_node('v24.14.0')
    assert not installer.supported_node('v22.23.3')
    assert not installer.supported_node('garbage')


def test_missing_packages_use_sudo_without_upgrading_other_services(monkeypatch):
    calls = []
    def query(command, **kwargs):
        missing = command[-1] == 'python3-venv'
        return SimpleNamespace(returncode=int(missing), stdout='' if missing else 'install ok installed')
    monkeypatch.setattr(installer.subprocess, 'run', query)
    monkeypatch.setattr(installer, 'run', lambda *args, **kwargs: calls.append(args))
    installer.install_packages()
    assert calls == [('sudo', 'apt-get', 'update'), ('sudo', 'apt-get', 'install', '-y', 'python3-venv')]


def test_invalid_config_prevents_prerequisite_install(simulated_install, monkeypatch):
    root, calls, _ = simulated_install
    (root / 'config.toml').write_text('broken = [')
    touched = []
    monkeypatch.setattr(installer, 'install_packages', lambda: touched.append(True))
    assert installer.main() == 1
    assert not calls and not touched


def test_node_is_installed_locally_and_reused_without_system_changes(tmp_path, monkeypatch):
    import hashlib
    import io
    import tarfile
    name = f'node-v{installer.NODE_VERSION}-linux-x64'
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w:xz') as tar:
        data = b'fixture node binary'
        info = tarfile.TarInfo(f'{name}/bin/node')
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    payload = archive.getvalue()
    downloads, commands = [], []
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    monkeypatch.setattr(installer.shutil, 'which', lambda _: None)
    monkeypatch.setattr(installer.platform, 'machine', lambda: 'x86_64')
    monkeypatch.setattr(installer, 'NODE_HASHES', {'x64': hashlib.sha256(payload).hexdigest()})
    def download(url, **kwargs):
        downloads.append(url)
        return io.BytesIO(payload)
    monkeypatch.setattr(installer.urllib.request, 'urlopen', download)
    monkeypatch.setattr(installer, 'run', lambda *args: commands.append(args))
    path = installer.prepare_node()
    assert path == tmp_path / '.tools' / name / 'bin'
    assert installer.prepare_node() == path
    assert len(downloads) == 1 and downloads[0].startswith('https://nodejs.org/dist/')
    assert all(command == (str(path / 'node'), '--version') for command in commands)


def test_node_download_failure_does_not_install_unverified_runtime(tmp_path, monkeypatch):
    import io
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    monkeypatch.setattr(installer.shutil, 'which', lambda _: None)
    monkeypatch.setattr(installer.platform, 'machine', lambda: 'x86_64')
    monkeypatch.setattr(installer.urllib.request, 'urlopen', lambda *args, **kwargs: io.BytesIO(b'corrupt download'))
    with pytest.raises(ValueError, match='integrity validation'):
        installer.prepare_node()
    assert list((tmp_path / '.tools').iterdir()) == []
