#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
py=${PYTHON:-python3}
echo "== msp parser tests =="
"$py" tests/test_msp.py
echo "== end to end pty sim =="
"$py" tests/test_tui.py
echo "all good"
