#!/usr/bin/env bash
#
# Build the CardioXNet macOS desktop app (CardioXNet.app) with PyInstaller.
#
# IMPORTANT: PyInstaller does not cross-compile. Run this ON a Mac.
# For an Apple-silicon native build run it on an arm64 Mac; for Intel, an
# x86_64 Mac (or a Rosetta x86_64 Python). To pin, set target_arch in
# cardioxnet-macos.spec.
#
# Usage:
#   ./build_macos.sh           # build CardioXNet.app
#   ./build_macos.sh --dmg     # also wrap it in a distributable .dmg
#
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERROR: this build must run on macOS (PyInstaller cannot cross-compile)." >&2
  exit 1
fi

PY="${PYTHON:-python3}"

echo "[1/3] Installing dependencies into the current environment…"
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r requirements.txt -r requirements-desktop.txt

echo "[2/3] Running PyInstaller…"
"$PY" -m PyInstaller cardioxnet-macos.spec --clean --noconfirm

if [[ ! -d "dist/CardioXNet.app" ]]; then
  echo "ERROR: build failed — dist/CardioXNet.app was not produced." >&2
  exit 1
fi
echo "    Built dist/CardioXNet.app"

if [[ "${1:-}" == "--dmg" ]]; then
  echo "[3/3] Creating dist/CardioXNet.dmg…"
  rm -f dist/CardioXNet.dmg
  hdiutil create -volname "CardioXNet" -srcfolder "dist/CardioXNet.app" \
    -ov -format UDZO "dist/CardioXNet.dmg"
  echo "    Built dist/CardioXNet.dmg"
else
  echo "[3/3] Skipping DMG (pass --dmg to create one)."
fi

cat <<'EOF'

Done.

  Run it:        open dist/CardioXNet.app
  Outputs + log: written next to the .app (CardioXNet.log, outputs/)

Notes
  * Gatekeeper: the app is unsigned. First launch needs a right-click → Open,
    or:  xattr -dr com.apple.quarantine dist/CardioXNet.app
  * To sign/notarize, set codesign_identity in cardioxnet-macos.spec and run
    codesign/notarytool afterwards.
EOF
