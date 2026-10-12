#!/usr/bin/env python3
"""Repeatable Ubuntu source installation. Never starts or stops a service."""
import grp
import hashlib
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

if sys.version_info < (3, 12):
    raise SystemExit('Installer requires Python 3.12+ on Ubuntu 24.04 or newer.')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.config import load_config

UNIT_PATH = Path('/etc/systemd/system/wsjtx-dashboard.service')
NODE_VERSION = '24.21.0'
# Official nodejs.org SHASUMS256 values; no release assets or checksum downloads.
NODE_HASHES = {
    'x64': 'fd8e59d5a511510f6a298afb548f18c7d2b1be404d8b4a27d94fbe49f56cb2d6',
    'arm64': '6ad1325edbdb5649c379b75a237147a666c95d4f9ae8d340fef2d1575d289ad2',
}


def run(*args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def ensure_host():
    if sys.platform != 'linux' or sys.version_info < (3, 12):
        raise ValueError('Installer requires Ubuntu 24.04+ with Python 3.12+. Mac development is documented separately.')
    release = platform.freedesktop_os_release()
    if release.get('ID') != 'ubuntu' or tuple(map(int, release.get('VERSION_ID', '0').split('.'))) < (24, 4):
        raise ValueError('Installer supports Ubuntu 24.04 or newer.')
    if os.geteuid() == 0:
        raise ValueError('Run ./install.sh as your ordinary user, without sudo; it requests sudo only for system changes.')
    if not Path('/run/systemd/system').is_dir():
        raise ValueError('systemd must be running on the Ubuntu host.')
    if not shutil.which('sudo'):
        raise ValueError('sudo is required to install prerequisites and the service.')


def check_stopped(config):
    status = subprocess.run(['systemctl', 'is-active', 'wsjtx-dashboard.service'], capture_output=True, text=True)
    if status.stdout.strip() in ('active', 'activating', 'reloading', 'deactivating'):
        raise ValueError('Dashboard is running. Run sudo systemctl stop wsjtx-dashboard, then retry installation.')
    if status.returncode not in (0, 3, 4):
        raise ValueError(f'Cannot check dashboard service state: {status.stderr.strip()}')
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex((config.host, config.port)) == 0:
            raise ValueError(f'{config.host}:{config.port} is occupied. Identify the listener; stop only a confirmed old dashboard.')
    if UNIT_PATH.exists() and 'Managed by WSJT-X Dashboard installer' not in UNIT_PATH.read_text():
        raise ValueError(f'{UNIT_PATH} already exists and is not managed by this installer; preserve and inspect it first.')


def install_packages():
    packages = ['python3-venv', 'ca-certificates', 'git', 'xz-utils']
    missing = []
    for package in packages:
        result = subprocess.run(['dpkg-query', '-W', '-f=${Status}', package], capture_output=True, text=True)
        if result.returncode or result.stdout.strip() != 'install ok installed':
            missing.append(package)
    if missing:
        print(f'Installing Ubuntu prerequisites: {", ".join(missing)}', flush=True)
        run('sudo', 'apt-get', 'update')
        run('sudo', 'apt-get', 'install', '-y', *missing)


def supported_node(version):
    match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)', version.strip())
    return bool(match and int(match[1]) == 24 and int(match[2]) >= 15)


def prepare_node():
    node = shutil.which('node')
    if node and shutil.which('npm'):
        version = subprocess.run([node, '--version'], capture_output=True, text=True, check=True).stdout
        if supported_node(version):
            print(f'Using existing Node {version.strip()}', flush=True)
            return Path(node).parent
    architecture = {'x86_64': 'x64', 'aarch64': 'arm64'}.get(platform.machine())
    if architecture is None:
        raise ValueError('Automatic Node installation supports Ubuntu x86_64 and arm64 only. Install Node 24.15+ LTS and npm, then retry.')
    name = f'node-v{NODE_VERSION}-linux-{architecture}'
    tools = ROOT / '.tools'
    target = tools / name
    if not (target / 'bin/node').is_file():
        tools.mkdir(exist_ok=True)
        print(f'Installing local Node {NODE_VERSION} LTS in {target}; system Node is unchanged.', flush=True)
        with tempfile.TemporaryDirectory(dir=tools) as folder:
            staging = Path(folder)
            archive = staging / f'{name}.tar.xz'
            with urllib.request.urlopen(f'https://nodejs.org/dist/v{NODE_VERSION}/{name}.tar.xz', timeout=60) as source, archive.open('wb') as output:
                shutil.copyfileobj(source, output)
            if hashlib.sha256(archive.read_bytes()).hexdigest() != NODE_HASHES[architecture]:
                raise ValueError('Official Node download failed integrity validation; retry or inspect the network.')
            with tarfile.open(archive) as tar:
                tar.extractall(staging, filter='data')
            (staging / name).rename(target)
    run(str(target / 'bin/node'), '--version')
    return target / 'bin'


def unit_quote(value):
    if any(char in str(value) for char in '\n\r\0$'):
        raise ValueError('Installation path cannot contain control characters or dollar signs')
    return str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')


def render_service(root, username, group):
    if not re.fullmatch(r'[A-Za-z0-9_-]+\$?', username) or not re.fullmatch(r'[A-Za-z0-9_-]+\$?', group):
        raise ValueError('Unsupported service user/group name')
    text = (root / 'deploy/wsjtx-dashboard.service').read_text()
    for key, value in {'USER': username, 'GROUP': group, 'ROOT': root,
                       'PYTHON': root / '.venv/bin/python', 'CONFIG': root / 'config.toml'}.items():
        text = text.replace(f'@{key}@', unit_quote(value))
    return text


def install():
    ensure_host()
    config = load_config(ROOT / 'config.toml')  # Validate before any machine changes.
    check_stopped(config)
    user = pwd.getpwuid(os.geteuid())
    group = grp.getgrgid(user.pw_gid).gr_name
    print('Installing WSJT-X Dashboard. Configuration is preserved. No service will be started.', flush=True)
    install_packages()
    node_bin = prepare_node()
    env = os.environ.copy()
    env['PATH'] = str(node_bin) + os.pathsep + env.get('PATH', '')
    run('python3', '-m', 'venv', '.venv')
    run(str(ROOT / '.venv/bin/python'), '-m', 'pip', 'install', '-r', 'requirements.txt')
    run(str(ROOT / '.venv/bin/python'), '-m', 'pip', 'check')
    run('npm', 'ci', env=env)
    run('npm', 'run', 'build', env=env)
    if not (ROOT / 'dist/index.html').is_file():
        raise ValueError('Frontend build did not produce dist/index.html; service was not updated.')
    with tempfile.TemporaryDirectory(prefix='wsjtx-systemd-') as folder:
        unit = Path(folder) / 'wsjtx-dashboard.service'
        unit.write_text(render_service(ROOT, user.pw_name, group))
        run('systemd-analyze', 'verify', str(unit))
        run('sudo', 'install', '-m', '644', str(unit), str(UNIT_PATH))
    run('sudo', 'systemctl', 'daemon-reload')
    print(f'Installation complete. Configuration: {ROOT / "config.toml"}', flush=True)
    print('Start: sudo systemctl start wsjtx-dashboard', flush=True)
    print(f'Browser: http://{config.host}:{config.port}/?mode=live', flush=True)


def main():
    try:
        install()
    except (ValueError, OSError, tarfile.TarError, subprocess.CalledProcessError) as exc:
        print(f'Installation failed: {exc}\nFix the reported error and rerun ./install.sh. The installer does not start services.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
