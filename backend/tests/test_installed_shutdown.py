"""Regression for foreground shutdown while a browser holds an SSE connection."""
from pathlib import Path
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not (ROOT / 'dist/index.html').exists(), reason='Installed-server shutdown check requires npm run build')
def test_installed_server_stops_with_open_browser_stream(tmp_path):
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
    config = tmp_path / 'config.toml'
    config.write_text((ROOT / 'config.example.toml').read_text().replace('8787', str(port)))
    before = config.read_bytes()
    # Reuse the same configuration and databases across a real process restart.
    for _ in range(2):
        # Retired environment settings must not override or break the TOML install.
        environment = dict(os.environ, WSJTX_RECEIVER='retired-value', WSJTX_PORT='invalid')
        child = subprocess.Popen([sys.executable, '-m', 'backend.server', '--config', str(config)],
                                 cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stream = None
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/snapshot', timeout=.5) as response:
                        assert response.status == 200
                    break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        pytest.fail('Installed server did not start')
                    time.sleep(.05)
            stream = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/events', timeout=2)
            assert stream.readline() == b'event: snapshot\n'
            started = time.monotonic()
            child.terminate()
            child.wait(timeout=9)
            assert time.monotonic() - started < 8.5
            assert child.returncode in (0, -signal.SIGTERM)
            log = child.communicate(timeout=1)[0].decode()
            assert 'Application shutdown complete.' in log
        finally:
            if stream:
                stream.close()
            if child.poll() is None:
                child.kill()
                child.wait(timeout=3)
        assert config.read_bytes() == before
        assert config.stat().st_mode & 0o777 == 0o600
        assert (tmp_path / 'data').stat().st_mode & 0o777 == 0o700
        assert all(path.stat().st_mode & 0o777 == 0o600 for path in (tmp_path / 'data').glob('*.sqlite3'))
