"""Qt compatibility layer.

AstrOrganizer prefers PySide6, but the installer can fall back to PyQt6 if
PySide6 wheels are unavailable on a particular machine/Python combination.
"""
from __future__ import annotations

API = ""
try:  # preferred: LGPL, official Qt for Python
    from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
    Signal = QtCore.Signal
    Slot = QtCore.Slot
    API = "PySide6"
except Exception:  # fallback
    from PyQt6 import QtCore, QtGui, QtWidgets  # type: ignore
    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
    API = "PyQt6"

# Small enum helpers: PyQt6 and PySide6 both support QtCore.Qt.X namespaces,
# but keeping aliases short makes the rest of the code easier to read.
Qt = QtCore.Qt
QUrl = QtCore.QUrl
