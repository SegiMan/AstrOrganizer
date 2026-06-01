#!/usr/bin/env bash
set -u
APP_ID="astrorganizer"
APP_CMD="astrorganizer"
INSTALL_ROOT="$HOME/.local/share/$APP_ID"
BIN="$HOME/.local/bin/$APP_CMD"
DESKTOP="$HOME/.local/share/applications/astrorganizer.desktop"
ICON="$HOME/.local/share/icons/hicolor/256x256/apps/astrorganizer.png"
CONFIG="$HOME/.config/$APP_ID"
DATA="$HOME/.local/share/$APP_ID"
CACHE="$HOME/.cache/$APP_ID"

echo "This will remove the AstrOrganizer app installation."
read -r -p "Also remove user settings, bookmarks and tags? [y/N] " remove_data
rm -f "$BIN" "$DESKTOP" "$ICON"
if [[ "$remove_data" =~ ^[Yy]$ ]]; then
  rm -rf "$CONFIG" "$DATA" "$CACHE"
  echo "Removed app and user data."
else
  rm -rf "$INSTALL_ROOT/app" "$INSTALL_ROOT/venv"
  echo "Removed app and environment, kept user config/data where possible."
fi
