"""Isolated production entry-point server for browser checks. UDP is never enabled."""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--radio', action='store_true')
args = parser.parse_args()

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='wsjtx-step0-browser-') as directory:
    config = Path(directory) / 'config.toml'
    source = (root / 'config.example.toml').read_text().replace('8787', '8792' if args.radio else '8791')
    if args.radio:
        source = source.replace('enabled = false', 'enabled = true').replace('group = "239.255.0.73"', 'group = ""').replace('listen = "0.0.0.0"', 'listen = "127.0.0.1"').replace('port = 2238', 'port = 18238').replace('retention = 200', 'retention = 50')
    config.write_text(source)
    child = subprocess.Popen([sys.executable, '-m', 'backend.server', '--config', str(config)], cwd=root)
    try:
        sys.exit(child.wait())
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=15)
