#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
elif command -v py >/dev/null 2>&1; then
  PYTHON_BIN=py
else
  echo 'ERROR: Python 3 was not found in PATH.' >&2
  exit 2
fi
"$PYTHON_BIN" scripts/e2e_check.py
