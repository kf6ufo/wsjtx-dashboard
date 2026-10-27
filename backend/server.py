"""Installed server entry point: configuration file, built frontend, one worker."""
import argparse
import os
from pathlib import Path
import sys
from .config import load_config
from .private_storage import private_file

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='WSJT-X Dashboard server')
    parser.add_argument('--config', type=Path, default=ROOT / 'config.toml')
    args = parser.parse_args()
    try:
        os.close(private_file(args.config))
        config = load_config(args.config)
        if not (ROOT / 'dist/index.html').is_file():
            raise ValueError('Built frontend missing; run ./install.sh before starting.')
    except (ValueError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1
    import uvicorn
    from .app import create_app
    from .workspace import WorkspaceState
    state = WorkspaceState(args.config.resolve().parent / 'data' / 'workspace.sqlite3')
    uvicorn.run(create_app(config.receiver, state, config_path=args.config.resolve(), enrichment_settings=config.enrichment), host=config.host, port=config.port, workers=1, timeout_graceful_shutdown=5)
    return 0


if __name__ == '__main__':
    sys.exit(main())
