"""Unprivileged source installer shared by macOS and Ubuntu. Never manages services."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.config import load_config


def main():
    try:
        if not (3, 12) <= sys.version_info[:2] < (3, 15):
            raise ValueError('Use Python 3.12–3.14')
        node = shutil.which('node')
        if not node or not shutil.which('npm'):
            raise ValueError('Install Node 24 LTS (24.15+) and npm, then rerun ./install.sh')
        version = subprocess.check_output([node, '--version'], text=True).strip().lstrip('v').split('.')
        if int(version[0]) != 24 or int(version[1]) < 15:
            raise ValueError('Use Node 24 LTS, version 24.15 or newer')
        config = ROOT / 'config.toml'
        if not config.exists():
            # Exclusive creation prevents replacement of an operator file.
            with config.open('x') as target:
                target.write((ROOT / 'config.example.toml').read_text())
            print('Created config.toml from example', flush=True)
        settings = load_config(config)
        for command in ([sys.executable, '-m', 'venv', '.venv'],
                        [str(ROOT / '.venv/bin/python'), '-m', 'pip', 'install', '-r', 'requirements.lock'],
                        ['npm', 'ci'], ['npm', 'run', 'build']):
            print('Running:', ' '.join(command), flush=True)
            subprocess.run(command, cwd=ROOT, check=True)
        print(f'Installation complete. Configuration preserved: {config}')
        print('Start: .venv/bin/python -m backend.server')
        print(f'Browser: http://{settings.host}:{settings.port}/')
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Installation failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
