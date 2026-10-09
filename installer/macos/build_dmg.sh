#!/usr/bin/env bash
# Packages dist/AntennaTracker.app into dist/AntennaTracker-<version>.dmg.
# Uses create-dmg (brew install create-dmg) when available, otherwise hdiutil.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-0.1.0}"
APP="$ROOT/dist/AntennaTracker.app"
DMG="$ROOT/dist/AntennaTracker-$VERSION.dmg"
VOLNAME="antenaa"

[[ -d "$APP" ]] || { echo "Missing $APP - run the PyInstaller build first" >&2; exit 1; }
rm -f "$DMG"

if command -v create-dmg >/dev/null 2>&1; then
  create-dmg \
    --volname "$VOLNAME" \
    --window-size 540 360 \
    --icon-size 96 \
    --icon "AntennaTracker.app" 140 170 \
    --app-drop-link 400 170 \
    --hide-extension "AntennaTracker.app" \
    --no-internet-enable \
    "$DMG" "$APP"
else
  echo "create-dmg not found, falling back to hdiutil"
  STAGE="$(mktemp -d)"
  trap 'rm -rf "$STAGE"' EXIT
  cp -R "$APP" "$STAGE/"
  ln -s /Applications "$STAGE/Applications"
  hdiutil create -volname "$VOLNAME" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
fi

echo "Built $DMG"
