# AstrOrganizer

AstrOrganizer is an experimental Linux/Ubuntu file organizer and file manager. It is designed as a first real foundation for a future bundle of Astro-themed desktop tools.

Version **0.1.0** is intentionally a starting point: it already has a usable file-browser core, but it is not yet a Dolphin/Nautilus/Krusader replacement. File managers are safety-critical applications, so this version favors simple and visible behavior over clever hidden automation.

## Current features

- Tabbed file browsing
- Optional split view
- Location/path bar
- Parent-folder navigation
- Multi-selection
- Hidden-file toggle
- Folders-first preference placeholder
- File sorting through the file table headers
- Open files with the default application through `xdg-open`
- Right-click context menu with **Open with** first
- Cut/copy/paste file operations
- Clipboard also exposes copied file paths as plain text, so pasting into many text editors should paste paths
- Rename
- Move to Trash through `send2trash`
- File/folder properties dialog
- Bookmarks
- Remember tabs from the previous session
- Middle-click folder to open it in a new tab
- Ctrl+mouse-wheel icon-size scaling for the file view
- Batch rename: add/remove prefix and suffix
- Best-effort file-in-use check using `psutil`
- SQLite-based tags for files/folders
- Status-bar tag display for one selected item
- Search by partial filename, exact filename, tag, and text contents of text-like files
- Case-sensitive `Cc` search toggle
- Ubuntu `.desktop` launcher
- Separate Python virtual environment
- GitHub-friendly installer, updater and uninstaller scripts

## Important limitations in v0.1

- Linux does not have a universal reliable “file is currently used by another app” check. AstrOrganizer uses a best-effort `psutil` scan.
- Drag-and-drop is enabled through Qt's file model, but browser upload-field behavior may need testing on Chrome/Firefox.
- “Open with” currently supports the default app and a custom command. A polished installed-application picker is planned later.
- Proper thumbnails, network locations, archive browsing, undo, mounted device sidebar, Git integration and admin helper actions are not implemented yet.
- The details/list view is currently Qt's file table/tree view. Dedicated icon/grid/list mode switching is planned.

## Install from a cloned GitHub repository

After uploading this repository to GitHub, install it on a machine like this:

```bash
git clone https://github.com/YOUR_USERNAME/AstrOrganizer.git
cd AstrOrganizer
chmod +x install.sh update.sh uninstall.sh
./install.sh
```

Start it with:

```bash
astrorganizer
```

Or open it from your application launcher.

If `~/.local/bin` is not in your PATH, log out and back in, or add this to `~/.bashrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Update after committing changes to GitHub

If you installed from a real git clone, AstrOrganizer keeps a git-enabled installed copy in:

```bash
~/.local/share/astrorganizer/app
```

To update:

```bash
~/.local/share/astrorganizer/app/update.sh
```

or from your local clone:

```bash
cd AstrOrganizer
git pull
./install.sh
```

## Uninstall

```bash
~/.local/share/astrorganizer/app/uninstall.sh
```

The uninstaller asks whether to remove user settings and tag data.

## Where data is stored

Application installation:

```bash
~/.local/share/astrorganizer/app
~/.local/share/astrorganizer/venv
```

User settings and tags:

```bash
~/.config/astrorganizer/settings.json
~/.local/share/astrorganizer/tags.sqlite3
```

Logs/cache:

```bash
~/.cache/astrorganizer/
```

## Development

Run directly from the repository:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m astrorganizer
```

If PySide6 fails to install on your Python version, try:

```bash
pip install -r requirements-pyqt6-fallback.txt
python -m astrorganizer
```

## Safety note

AstrOrganizer does not run as administrator by default. If you start it with `sudo`, it will have administrator rights and will warn you. For ordinary use, run it as your normal user.
