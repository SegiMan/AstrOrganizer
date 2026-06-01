from __future__ import annotations
from pathlib import Path
from .qt_compat import QtCore, QtGui, QtWidgets, Qt
from .operations import file_users

class PropertiesDialog(QtWidgets.QDialog):
    def __init__(self, paths: list[Path], tags: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Properties")
        self.resize(520, 320)
        layout = QtWidgets.QVBoxLayout(self)
        text = QtWidgets.QTextEdit(readOnly=True)
        lines: list[str] = []
        if len(paths) == 1:
            p = paths[0]
            lines += [
                f"Name: {p.name}",
                f"Path: {p}",
                f"Type: {'Folder' if p.is_dir() else 'File'}",
                f"Exists: {p.exists()}",
            ]
            try:
                st = p.stat()
                lines += [f"Size: {st.st_size:,} bytes", f"Modified: {QtCore.QDateTime.fromSecsSinceEpoch(int(st.st_mtime)).toString(Qt.DateFormat.SystemLocaleLongDate)}"]
            except Exception as e:
                lines.append(f"Could not read stat info: {e}")
            if tags is not None:
                lines.append(f"Tags: {' '.join(tags) if tags else '(none)'}")
        else:
            total = 0
            files = folders = 0
            for p in paths:
                try:
                    if p.is_dir():
                        folders += 1
                    else:
                        files += 1
                        total += p.stat().st_size
                except Exception:
                    pass
            lines += [f"Selected items: {len(paths)}", f"Files: {files}", f"Folders: {folders}", f"Known file size total: {total:,} bytes"]
        text.setPlainText("\n".join(lines))
        layout.addWidget(text)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

class TagDialog(QtWidgets.QDialog):
    def __init__(self, current: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit tags")
        self.resize(420, 120)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Tags, separated by spaces or commas. Example: #work #latex #important"))
        self.edit = QtWidgets.QLineEdit(" ".join(current))
        layout.addWidget(self.edit)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def tags(self) -> list[str]:
        raw = self.edit.text().replace(",", " ").split()
        return [x.strip() for x in raw if x.strip()]

class BatchRenameDialog(QtWidgets.QDialog):
    def __init__(self, count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Batch rename {count} items")
        self.resize(480, 260)
        form = QtWidgets.QFormLayout(self)
        self.prefix = QtWidgets.QLineEdit()
        self.suffix = QtWidgets.QLineEdit()
        self.remove_prefix = QtWidgets.QLineEdit()
        self.remove_suffix = QtWidgets.QLineEdit()
        form.addRow("Insert prefix:", self.prefix)
        form.addRow("Insert suffix before extension:", self.suffix)
        form.addRow("Remove prefix:", self.remove_prefix)
        form.addRow("Remove suffix before extension:", self.remove_suffix)
        note = QtWidgets.QLabel("Before renaming, AstrOrganizer will do a best-effort check for open files and name conflicts.")
        note.setWordWrap(True)
        form.addRow(note)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
    def values(self):
        return self.prefix.text(), self.suffix.text(), self.remove_prefix.text(), self.remove_suffix.text()

class SearchDialog(QtWidgets.QDialog):
    open_path_requested = QtCore.Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search")
        self.resize(760, 520)
        layout = QtWidgets.QVBoxLayout(self)
        row = QtWidgets.QHBoxLayout()
        self.query = QtWidgets.QLineEdit()
        self.query.setPlaceholderText("Name, exact name, #tag, or text inside files")
        self.case = QtWidgets.QToolButton(text="Cc", checkable=True)
        self.content = QtWidgets.QCheckBox("Search inside text files")
        self.exact = QtWidgets.QCheckBox("Exact filename")
        self.recursive = QtWidgets.QCheckBox("Subfolders")
        self.recursive.setChecked(True)
        self.button = QtWidgets.QPushButton("Search")
        row.addWidget(self.query, 1); row.addWidget(self.case); row.addWidget(self.content); row.addWidget(self.exact); row.addWidget(self.recursive); row.addWidget(self.button)
        layout.addLayout(row)
        self.results = QtWidgets.QListWidget()
        self.results.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.results, 1)
        self.status = QtWidgets.QLabel("Ready.")
        layout.addWidget(self.status)
        self.button.clicked.connect(self.start_search)
        self.results.itemDoubleClicked.connect(lambda item: self.open_path_requested.emit(item.data(Qt.ItemDataRole.UserRole)))
        self._search_callback = None
    def set_callback(self, callback):
        self._search_callback = callback
    def start_search(self):
        if self._search_callback:
            self._search_callback(self)
    def add_result(self, path: str, note: str = ""):
        item = QtWidgets.QListWidgetItem(path if not note else f"{path} — {note}")
        item.setData(Qt.ItemDataRole.UserRole, path)
        self.results.addItem(item)
