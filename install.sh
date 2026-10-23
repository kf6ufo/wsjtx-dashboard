#!/bin/sh
# Native source build; does not install packages globally or manage services.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec "${PYTHON:-python3}" scripts/install-native.py
