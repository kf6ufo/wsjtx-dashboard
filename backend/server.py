"""Installed server entry point: configuration file, built frontend, one worker."""
import argparse
from pathlib import Path
import sys
from .config import load_config

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='WSJT-X Dashboard server')
    parser.add_argument('--config', type=Path, default=ROOT / 'config.toml')
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if config.receiver.enabled:
            raise ValueError('Step 0 requires wsjtx.enabled = false. Preserve old station configuration separately; no receiver is started.')
        if not (ROOT / 'dist/index.html').is_file():
            raise ValueError('Built frontend missing; run ./install.sh before starting.')
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    import uvicorn
    from .app import create_app
    from .foundation import FoundationState
    state = FoundationState(args.config.resolve().parent / 'data' / 'workspace.sqlite3')
    uvicorn.run(create_app(config.receiver, state), host=config.host, port=config.port, workers=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
