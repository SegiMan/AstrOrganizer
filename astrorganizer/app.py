from __future__ import annotations
import os
import sys
from pathlib import Path
from .qt_compat import QtGui, QtWidgets, API
from .main_window import MainWindow
from . import __app_name__, __version__


def _find_icon() -> str | None:
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "assets" / "astrorganizer.png",
        Path.home() / ".local/share/icons/hicolor/256x256/apps/astrorganizer.png",
        Path.home() / ".local/share/icons/astrorganizer.png",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    app = QtWidgets.QApplication(argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    icon = _find_icon()
    if icon:
        app.setWindowIcon(QtGui.QIcon(icon))
    win = MainWindow()
    win.show()
    return app.exec()
