from __future__ import annotations
from pathlib import Path
from .qt_compat import QtCore, QtGui, QtWidgets, Qt, QUrl
from .operations import open_default

class FilePanel(QtWidgets.QWidget):
    path_changed = QtCore.Signal(str)
    selection_changed = QtCore.Signal(list)
    open_folder_in_new_tab = QtCore.Signal(str)
    context_menu_requested = QtCore.Signal(object, object)

    def __init__(self, start_path: str | Path, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.current_path = Path(start_path).expanduser()
        self.clipboard_mode: str | None = None
        self.clipboard_paths: list[Path] = []

        self.model = QtWidgets.QFileSystemModel(self)
        self.model.setRootPath(str(Path.home()))
        self.model.setFilter(self._make_filters())

        self.view = QtWidgets.QTreeView()
        self.view.setModel(self.model)
        self.view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.setDragEnabled(True)
        self.view.setAcceptDrops(True)
        self.view.setDropIndicatorShown(True)
        self.view.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.view.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.view.doubleClicked.connect(self.on_double_clicked)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._context_menu)
        self.view.selectionModel().selectionChanged.connect(self._selection_changed)
        self.view.viewport().installEventFilter(self)
        self.view.setIconSize(QtCore.QSize(int(settings.get("icon_size", 32)), int(settings.get("icon_size", 32))))

        self.path_bar = QtWidgets.QLineEdit()
        self.path_bar.returnPressed.connect(self.go_to_bar_path)
        up = QtWidgets.QToolButton(text="↑")
        up.setToolTip("Parent folder")
        up.clicked.connect(self.go_up)
        refresh = QtWidgets.QToolButton(text="⟳")
        refresh.clicked.connect(self.refresh)
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0,0,0,0)
        row.addWidget(up); row.addWidget(refresh); row.addWidget(self.path_bar, 1)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2,2,2,2)
        layout.addLayout(row)
        layout.addWidget(self.view, 1)
        self.set_path(self.current_path)

    def _make_filters(self):
        f = QtCore.QDir.Filter.AllEntries | QtCore.QDir.Filter.NoDotAndDotDot | QtCore.QDir.Filter.AllDirs
        if self.settings.get("show_hidden", False):
            f |= QtCore.QDir.Filter.Hidden
        return f

    def apply_settings(self):
        self.model.setFilter(self._make_filters())
        s = int(self.settings.get("icon_size", 32))
        self.view.setIconSize(QtCore.QSize(s, s))

    def selected_paths(self) -> list[Path]:
        rows = self.view.selectionModel().selectedRows(0)
        return [Path(self.model.filePath(idx)) for idx in rows]

    def _selection_changed(self):
        self.selection_changed.emit([str(p) for p in self.selected_paths()])

    def set_path(self, path: str | Path) -> None:
        p = Path(path).expanduser().resolve(strict=False)
        if not p.exists():
            p = Path.home()
        if p.is_file():
            p = p.parent
        self.current_path = p
        self.path_bar.setText(str(p))
        idx = self.model.setRootPath(str(p))
        self.view.setRootIndex(idx)
        self.path_changed.emit(str(p))

    def go_to_bar_path(self):
        self.set_path(self.path_bar.text().strip())

    def go_up(self):
        self.set_path(self.current_path.parent)

    def refresh(self):
        self.model.setRootPath("")
        self.set_path(self.current_path)

    def on_double_clicked(self, index):
        p = Path(self.model.filePath(index))
        if p.is_dir():
            self.set_path(p)
        else:
            open_default(p)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            size = int(self.settings.get("icon_size", 32))
            delta = 8 if event.angleDelta().y() > 0 else -8
            size = max(16, min(128, size + delta))
            self.settings.set("icon_size", size)
            self.apply_settings()
            event.accept()
        else:
            super().wheelEvent(event)

    def eventFilter(self, watched, event):
        if watched is self.view.viewport() and event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.MiddleButton:
                idx = self.view.indexAt(event.pos())
                if idx.isValid():
                    p = Path(self.model.filePath(idx))
                    if p.is_dir():
                        self.open_folder_in_new_tab.emit(str(p))
                        return True
        return super().eventFilter(watched, event)

    def _context_menu(self, pos):
        self.context_menu_requested.emit(self, self.view.viewport().mapToGlobal(pos))
