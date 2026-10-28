"""Unprivileged source installer shared by macOS and Ubuntu. Never manages services."""
from pathlib import Path
from contextlib import contextmanager
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.config import load_config
from backend.private_storage import private_file

# Official https://nodejs.org/dist/v24.21.0/SHASUMS256.txt, verified October 27.
# Pin both version and checksums so a downloaded tool is verified before execution.
NODE_VERSION = '24.21.0'
NODE_SHA256 = {
    ('darwin', 'arm64'): 'bed7eea5325e1108f32ce5228ddd6a5f0f08a499ee42aa7442aea583702f6057',
    ('darwin', 'x64'): '1462cb3b3046b815cf8ea436d3da450ec1a9f11dac7e5a46b0ada5305d7e8097',
    ('linux', 'arm64'): '724282c3b43aec998aa9527380465b45d229e021b58035f5f4f63095eabfe5d5',
    ('linux', 'x64'): '6e1db87ef58b8819e5d5402eff1536491b18edd8eb7bee5ef7897876e88dc5ff',
}


def node_target():
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {'x86_64':'x64', 'amd64':'x64', 'arm64':'arm64', 'aarch64':'arm64'}.get(machine)
    if (system, arch) not in NODE_SHA256:
        raise ValueError(f'Automatic Node setup does not support {system}/{machine}. Install Node 24.15+ within 24.x and npm manually.')
    return system, arch


def download_node(url, target):
    deadline = time.monotonic() + 300
    with urllib.request.urlopen(url, timeout=30) as response, target.open('wb') as output:
        if response.geturl() != url:
            raise ValueError('Unexpected Node download redirect')
        total = 0
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > 120 * 1024 * 1024 or time.monotonic() > deadline:
                raise ValueError('Node download exceeded its size or time limit')
            output.write(chunk)


@contextmanager
def node_environment():
    environment = dict(os.environ)
    node = shutil.which('node')
    compatible = False
    if node and shutil.which('npm'):
        try:
            version = subprocess.check_output([node, '--version'], text=True, timeout=10).strip()
            match = re.fullmatch(r'v24\.(\d+)\.\d+', version)
            compatible = bool(match and int(match[1]) >= 15)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
    if compatible:
        print(f'Using existing Node {version}', flush=True)
        yield environment
        return
    system, arch = node_target()
    name = f'node-v{NODE_VERSION}-{system}-{arch}'
    print(f'Downloading temporary Node {NODE_VERSION} for {system}/{arch} (removed after installation)', flush=True)
    with tempfile.TemporaryDirectory(prefix='wsjtx-dashboard-node-') as directory:
        archive = Path(directory) / (name + '.tar.gz')
        download_node(f'https://nodejs.org/dist/v{NODE_VERSION}/{archive.name}', archive)
        with archive.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != NODE_SHA256[system, arch]:
                raise ValueError('Node checksum verification failed; downloaded tools were not executed')
        with tarfile.open(archive, 'r:gz') as bundle:
            bundle.extractall(directory, filter='data')
        binary = Path(directory) / name / 'bin'
        environment['PATH'] = str(binary) + os.pathsep + environment.get('PATH', '')
        if not (binary / 'node').is_file() or not (binary / 'npm').is_file():
            raise ValueError('Node archive is missing node/npm')
        version = subprocess.check_output([str(binary / 'node'), '--version'], text=True, timeout=10, env=environment).strip()
        if version != f'v{NODE_VERSION}':
            raise ValueError('Downloaded Node version does not match the pinned version')
        yield environment


def main():
    try:
        if not (3, 12) <= sys.version_info[:2] < (3, 15):
            raise ValueError('Use Python 3.12–3.14')
        config = ROOT / 'config.toml'
        if not config.exists():
            # Exclusive creation prevents replacement of an operator file.
            with os.fdopen(private_file(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL), 'w') as target:
                target.write((ROOT / 'config.example.toml').read_text())
            print('Created config.toml from example', flush=True)
        else:
            os.close(private_file(config))
        settings = load_config(config)
        with node_environment() as environment:
            for command in ([sys.executable, '-m', 'venv', '.venv'],
                            [str(ROOT / '.venv/bin/python'), '-m', 'pip', 'install', '-r', 'requirements.lock'],
                            ['npm', 'ci'], ['npm', 'run', 'build']):
                print('Running:', ' '.join(command), flush=True)
                subprocess.run(command, cwd=ROOT, check=True, env=environment)
        print(f'Installation complete. Configuration preserved: {config}')
        print('Start: .venv/bin/python -m backend.server')
        print(f'Browser: http://{settings.host}:{settings.port}/')
        return 0
    except (ValueError, OSError, tarfile.TarError, subprocess.SubprocessError) as exc:
        print(f'Installation failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
