#!/usr/bin/env python3
"""Install an explicit GitHub release in this dedicated Ubuntu checkout."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPO = 'kf6ufo/wsjtx-dashboard'


def extract_frontend(archive: Path, destination: Path, commit: str):
    """Reject links/path traversal and require a frontend matching the source."""
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        for member in members:
            path = Path(member.name)
            if (path.is_absolute() or '..' in path.parts or not path.parts
                    or path.parts[0] != 'dist' or not (member.isdir() or member.isfile())):
                raise ValueError('Unsafe frontend archive member')
        tar.extractall(destination, members=members, filter='data')
    dist = destination / 'dist'
    if not (dist / 'index.html').is_file():
        raise ValueError('Missing built dashboard')
    if json.loads((dist / 'frontend.json').read_text())['commit'] != commit:
        raise ValueError('Frontend/source commit mismatch')
    return dist


def run(*args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def main():
    if sys.platform != 'linux' or len(sys.argv) != 2 or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', sys.argv[1]):
        raise SystemExit('Usage on Ubuntu: python3 scripts/install-ubuntu.py RELEASE_TAG')
    for command in ('git', 'gh'):
        if not shutil.which(command):
            raise SystemExit(f'Install {command} before continuing.')
    origin = run('git', 'remote', 'get-url', 'origin', capture_output=True, text=True).stdout.strip()
    if origin not in (f'https://github.com/{REPO}.git', f'git@github.com:{REPO}.git'):
        raise SystemExit('Unexpected origin; refusing to modify this checkout.')
    if run('git', 'status', '--porcelain', '--untracked-files=normal', capture_output=True, text=True).stdout.strip():
        raise SystemExit('Checkout has local changes; preserve them before installing. No reset/clean is performed.')
    # Do not replace files while a manual validation server is still running.
    for address in ('10.176.1.6', '127.0.0.1'):
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex((address, 8000)) == 0:
                raise SystemExit('TCP 8000 is occupied. Stop only the dashboard before installing; do not stop other services.')
    tag = sys.argv[1]
    run('git', 'fetch', 'origin', f'refs/tags/{tag}:refs/tags/{tag}')
    commit = run('git', 'rev-parse', f'refs/tags/{tag}^{{commit}}', capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='.frontend-install-', dir=ROOT) as folder:
        staging = Path(folder)
        run('gh', 'release', 'download', tag, '--repo', REPO, '--pattern', 'frontend.tar.gz*', '--dir', str(staging))
        archive = staging / 'frontend.tar.gz'
        checksum = (staging / 'frontend.tar.gz.sha256').read_text().split()
        if len(checksum) != 2 or checksum[1] != 'frontend.tar.gz' or hashlib.sha256(archive.read_bytes()).hexdigest() != checksum[0]:
            raise SystemExit('Frontend checksum failed; source and installation were not changed.')
        dist = extract_frontend(archive, staging, commit)
        run('git', 'checkout', '--detach', commit)
        if not (ROOT / '.venv/bin/python').exists():
            run('python3', '-m', 'venv', '.venv')
        run(str(ROOT / '.venv/bin/python'), '-m', 'pip', 'install', '-r', 'requirements.txt')
        target = ROOT / 'dist'
        if target.is_symlink():
            raise SystemExit('Refusing to replace a linked dist directory.')
        if target.exists():
            shutil.move(str(target), str(staging / 'previous-dist'))
        shutil.move(str(dist), str(target))
    print(f'Installed {tag} at {commit}. Start manually: ./scripts/start-station.sh')


if __name__ == '__main__':
    main()
