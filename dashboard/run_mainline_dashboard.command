#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"
python3 dashboard/run_dashboard.py

PNG_PATH="$REPO_ROOT/dashboard/output/current_signal_latest.png"
open "$PNG_PATH" || open -a Preview "$PNG_PATH" || true
