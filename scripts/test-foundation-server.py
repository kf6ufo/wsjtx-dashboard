"""Isolated production entry-point server for browser checks. UDP is never enabled."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='wsjtx-step0-browser-') as directory:
    config = Path(directory) / 'config.toml'
    config.write_text((root / 'config.example.toml').read_text().replace('8787', '8791'))
    child = subprocess.Popen([sys.executable, '-m', 'backend.server', '--config', str(config)], cwd=root)
    try:
        sys.exit(child.wait())
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=15)
