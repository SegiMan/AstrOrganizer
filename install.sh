#!/usr/bin/env bash
set -u

APP_NAME="AstrOrganizer"
APP_CMD="astrorganizer"
APP_ID="astrorganizer"
REQUIRED_PY="3.14"
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

have() { command -v "$1" >/dev/null 2>&1; }

try_apt_install_base() {
  if have apt-get && have sudo; then
    echo "==> Trying to install base system packages with apt..."
    sudo apt-get update || true
    sudo apt-get install -y ca-certificates curl wget git rsync build-essential xdg-utils || true
  fi
}

try_apt_install_python314() {
  if have apt-get && have sudo; then
    echo "==> Trying to install Python 3.14 system packages with apt..."
    sudo apt-get update || true
    sudo apt-get install -y python3.14 python3.14-venv python3.14-dev || true
  fi
}

try_apt_install_qt_runtime() {
  if have apt-get && have sudo; then
    echo "==> Trying to install common Qt runtime libraries with apt..."
    sudo apt-get update || true
    sudo apt-get install -y \
      libegl1 libgl1 libxkbcommon-x11-0 libxcb-cursor0 \
      libxcb-keysyms1 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
      libxcb-render-util0 libxcb-randr0 libxcb-shape0 libxcb-xfixes0 \
      xdg-utils || true
  fi
}

python_version_ok() {
  "$1" - <<PY >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[:2] == (${REQUIRED_PY%.*}, ${REQUIRED_PY#*.}) else 1)
PY
}

python_version_print() {
  "$1" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY
}

install_uv_if_needed() {
  if have uv; then
    return 0
  fi
  if [ -x "$HOME/.local/bin/uv" ]; then
    export PATH="$HOME/.local/bin:$PATH"
    return 0
  fi

  echo "==> uv is not installed. It is needed to bootstrap Python $REQUIRED_PY if the system package is unavailable."
  try_apt_install_base

  if have curl; then
    echo "==> Installing uv with the official standalone installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh || true
  elif have wget; then
    echo "==> Installing uv with the official standalone installer via wget..."
    wget -qO- https://astral.sh/uv/install.sh | sh || true
  fi

  export PATH="$HOME/.local/bin:$PATH"
  have uv
}

find_or_install_python314() {
  local candidate=""

  if have python3.14 && python_version_ok "$(command -v python3.14)"; then
    command -v python3.14
    return 0
  fi

  try_apt_install_python314
  if have python3.14 && python_version_ok "$(command -v python3.14)"; then
    command -v python3.14
    return 0
  fi

  if install_uv_if_needed; then
    echo "==> Installing managed Python $REQUIRED_PY with uv..."
    uv python install "$REQUIRED_PY" || true
    candidate="$(uv python find "$REQUIRED_PY" 2>/dev/null || true)"
    if [ -n "$candidate" ] && [ -x "$candidate" ] && python_version_ok "$candidate"; then
      echo "$candidate"
      return 0
    fi
  fi

  return 1
}

echo "==> Installing $APP_NAME"
echo "Repository/source: $SCRIPT_DIR"
echo "Install root: $INSTALL_ROOT"
echo "Required Python: $REQUIRED_PY.x"

PY_BOOTSTRAP="$(find_or_install_python314 || true)"
if [ -z "$PY_BOOTSTRAP" ]; then
  echo "ERROR: Could not find or install Python $REQUIRED_PY."
  echo "Try manually installing uv and Python $REQUIRED_PY:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  export PATH=\"$HOME/.local/bin:\$PATH\""
  echo "  uv python install $REQUIRED_PY"
  echo "Then run ./install.sh again."
  exit 1
fi

echo "==> Using Python: $PY_BOOTSTRAP"
echo "==> Python version: $(python_version_print "$PY_BOOTSTRAP")"

if [ -d "$VENV_DIR" ]; then
  CURRENT_VENV_VERSION="$($VENV_DIR/bin/python - <<'PY' 2>/dev/null || true
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
  if [ "$CURRENT_VENV_VERSION" != "$REQUIRED_PY" ]; then
    echo "==> Existing venv uses Python ${CURRENT_VENV_VERSION:-unknown}, not $REQUIRED_PY. Recreating venv."
    rm -rf "$VENV_DIR"
  fi
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "==> Creating isolated virtual environment at $VENV_DIR"
  if have uv; then
    uv venv --python "$PY_BOOTSTRAP" "$VENV_DIR" || "$PY_BOOTSTRAP" -m venv "$VENV_DIR"
  else
    "$PY_BOOTSTRAP" -m venv "$VENV_DIR"
  fi
fi

PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

"$PYTHON" -m ensurepip --upgrade || true
"$PYTHON" -m pip install --upgrade pip setuptools wheel || true

try_apt_install_qt_runtime

echo "==> Installing Python dependencies into AstrOrganizer's separate venv..."
if "$PIP" install -r "$SCRIPT_DIR/requirements.txt"; then
  echo "Installed preferred dependencies from requirements.txt"
else
  echo "WARNING: Preferred dependency install failed. Trying fallback with PyQt6 instead of PySide6..."
  if "$PIP" install -r "$SCRIPT_DIR/requirements-pyqt6-fallback.txt"; then
    echo "Fallback dependencies installed."
  else
    echo "ERROR: Could not install either PySide6 or PyQt6 into Python $REQUIRED_PY venv."
    echo "This usually means no compatible Qt wheel is available for this Python/platform combination, or system Qt runtime libraries are missing."
    echo "See $LOG for details."
    exit 1
  fi
fi

echo "==> Copying application files..."
mkdir -p "$APP_DIR"
if have rsync; then
  rsync -a --delete --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' "$SCRIPT_DIR/" "$APP_DIR/"
else
  rm -rf "$APP_DIR"
  mkdir -p "$APP_DIR"
  cp -a "$SCRIPT_DIR/." "$APP_DIR/"
  find "$APP_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + || true
  find "$APP_DIR" -type f -name '*.pyc' -delete || true
fi

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
import sys
import astrorganizer
from astrorganizer.qt_compat import API
from astrorganizer.tags import TagStore
print("AstrOrganizer import OK")
print("Python:", sys.version.split()[0])
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
