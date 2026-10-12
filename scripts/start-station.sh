#!/bin/sh
# Foreground validation only: Ctrl+C stops this dashboard, never other services.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ ! -x .venv/bin/python ] || [ ! -f dist/index.html ]; then
    echo 'Run the documented Ubuntu installer first.' >&2
    exit 1
fi
.venv/bin/python - <<'PY'
import json
from pathlib import Path
import subprocess
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
if json.loads(Path('dist/frontend.json').read_text())['commit'] != commit:
    raise SystemExit('Frontend/source commit mismatch; rerun the Ubuntu installer.')
PY
export WSJTX_RECEIVER=on WSJTX_GROUP=239.255.0.73 WSJTX_PORT=2238 WSJTX_INTERFACE=10.176.1.6
exec .venv/bin/python -m uvicorn backend.app:app --host 10.176.1.6 --port 8000 --workers 1
