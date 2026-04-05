#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"
if [[ -x "$HOME/miniforge3/bin/python3" ]]; then
  PYTHON_BIN="$HOME/miniforge3/bin/python3"
else
  PYTHON_BIN="python3"
fi
DASHBOARD_USE_CACHE_ONLY=1 "$PYTHON_BIN" dashboard/run_dashboard.py

PNG_PATH="$REPO_ROOT/dashboard/output/current_signal_latest.png"
open "$PNG_PATH" || open -a Preview "$PNG_PATH" || true
