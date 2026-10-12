#!/bin/sh
# Run as your ordinary Ubuntu user; the installer requests sudo where needed.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Python 3.12+ is required. On Ubuntu 24.04: sudo apt install python3 python3-venv' >&2
    exit 1
fi
exec python3 scripts/install-ubuntu.py
