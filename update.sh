#!/usr/bin/env bash
set -u
APP_ID="astrorganizer"
INSTALL_ROOT="$HOME/.local/share/$APP_ID"
APP_DIR="$INSTALL_ROOT/app"
VENV_DIR="$INSTALL_ROOT/venv"
LOG="$INSTALL_ROOT/update.log"
mkdir -p "$INSTALL_ROOT"
exec > >(tee -a "$LOG") 2>&1

echo "==> Updating AstrOrganizer"
if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: Installed app directory not found: $APP_DIR"
  echo "Run ./install.sh from the repository first."
  exit 1
fi
cd "$APP_DIR" || exit 1
if [ -d .git ]; then
  echo "==> Pulling latest changes from GitHub..."
  git pull --ff-only || { echo "git pull failed. Resolve conflicts or check connection."; exit 1; }
else
  echo "WARNING: Installed app is not a git clone. Updating dependencies only."
fi
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel || true
if ! "$VENV_DIR/bin/pip" install -r requirements.txt; then
  echo "Preferred dependencies failed; trying PyQt6 fallback."
  "$VENV_DIR/bin/pip" install -r requirements-pyqt6-fallback.txt || true
fi
"$VENV_DIR/bin/python" - <<'PY'
import astrorganizer
from astrorganizer.qt_compat import API
print("AstrOrganizer update verification OK; Qt binding:", API)
PY
