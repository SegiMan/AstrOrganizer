#!/usr/bin/env bash
set -u

APP_NAME="AstrOrganizer"
APP_CMD="astrorganizer"
APP_ID="astrorganizer"
INSTALL_ROOT="$HOME/.local/share/$APP_ID"
APP_DIR="$INSTALL_ROOT/app"
VENV_DIR="$INSTALL_ROOT/venv"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$INSTALL_ROOT/install.log"

mkdir -p "$INSTALL_ROOT" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
exec > >(tee -a "$LOG") 2>&1

echo "==> Installing $APP_NAME"
echo "Repository/source: $SCRIPT_DIR"
echo "Install root: $INSTALL_ROOT"

have() { command -v "$1" >/dev/null 2>&1; }
try_apt_install() {
  if have apt-get && have sudo; then
    echo "==> Trying to install missing system packages with apt..."
    sudo apt-get update || true
    sudo apt-get install -y python3 python3-venv python3-pip python3-dev build-essential xdg-utils || true
  fi
}

if ! have python3; then
  echo "Python 3 is missing."
  try_apt_install
fi
if ! have python3; then
  echo "ERROR: python3 is still missing. Install it and run ./install.sh again."
  exit 1
fi

PYVER="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
echo "==> Python version: $PYVER"
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("ERROR: AstrOrganizer requires Python 3.10 or newer.")
PY
if [ $? -ne 0 ]; then exit 1; fi

if [ ! -d "$VENV_DIR" ]; then
  echo "==> Creating virtual environment..."
  python3 -m venv --system-site-packages "$VENV_DIR" || { try_apt_install; python3 -m venv --system-site-packages "$VENV_DIR"; }
fi

PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"
"$PYTHON" -m ensurepip --upgrade || true
"$PYTHON" -m pip install --upgrade pip setuptools wheel || true

echo "==> Installing Python dependencies..."
if "$PIP" install -r "$SCRIPT_DIR/requirements.txt"; then
  echo "Installed preferred dependencies from requirements.txt"
else
  echo "WARNING: Preferred dependency install failed. Trying fallback with PyQt6 instead of PySide6..."
  if "$PIP" install -r "$SCRIPT_DIR/requirements-pyqt6-fallback.txt"; then
    echo "Fallback dependencies installed."
  else
    echo "WARNING: Fallback dependency install failed. Trying Ubuntu Qt packages as a last resort..."
    try_apt_install
    if have apt-get && have sudo; then
      sudo apt-get install -y python3-pyqt6 python3-psutil || true
    fi
    "$PIP" install send2trash platformdirs psutil || true
  fi
fi

echo "==> Copying application files..."
mkdir -p "$APP_DIR"
rsync -a --delete --exclude 'venv' --exclude '__pycache__' "$SCRIPT_DIR/" "$APP_DIR/" 2>/dev/null || {
  rm -rf "$APP_DIR"
  mkdir -p "$APP_DIR"
  cp -a "$SCRIPT_DIR/." "$APP_DIR/"
}

if [ -f "$APP_DIR/assets/astrorganizer.png" ]; then
  cp "$APP_DIR/assets/astrorganizer.png" "$ICON_DIR/astrorganizer.png"
fi

cat > "$BIN_DIR/$APP_CMD" <<EOF2
#!/usr/bin/env bash
cd "$APP_DIR" || exit 1
exec "$VENV_DIR/bin/python" -m astrorganizer "\$@"
EOF2
chmod +x "$BIN_DIR/$APP_CMD"

sed "s#__EXEC__#$BIN_DIR/$APP_CMD#g" "$APP_DIR/desktop/astrorganizer.desktop.in" > "$DESKTOP_DIR/astrorganizer.desktop"
chmod +x "$DESKTOP_DIR/astrorganizer.desktop"

if have update-desktop-database; then update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true; fi
if have gtk-update-icon-cache; then gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true; fi

echo "==> Verifying installation..."
cd "$APP_DIR" || exit 1
if "$PYTHON" - <<'PY'
import astrorganizer
from astrorganizer.qt_compat import API
from astrorganizer.tags import TagStore
print("AstrOrganizer import OK")
print("Qt binding:", API)
TagStore()
print("Tag database OK")
PY
then
  echo "==> Installation verified."
else
  echo "ERROR: Verification failed. See $LOG"
  exit 1
fi

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "NOTE: $BIN_DIR is not in PATH. Log out/in, or add this to ~/.bashrc: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

echo ""
echo "Installed. Start it with: $APP_CMD"
echo "Or find AstrOrganizer in your app launcher."
