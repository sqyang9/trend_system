#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$SCRIPT_DIR/launchd/com.trend-system.mainline-dashboard.plist.template"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/com.trend-system.mainline-dashboard.plist"

mkdir -p "$TARGET_DIR"
mkdir -p "$REPO_ROOT/dashboard/output"
sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$TEMPLATE" > "$TARGET_PLIST"
launchctl unload "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl load "$TARGET_PLIST"
echo "Installed: $TARGET_PLIST"
