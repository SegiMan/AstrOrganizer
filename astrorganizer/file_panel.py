from __future__ import annotations
from pathlib import Path
from .qt_compat import QtCore, QtGui, QtWidgets, Qt, QUrl
from .operations import open_default


class LeftDragTreeView(QtWidgets.QTreeView):
    """QTreeView variant that only starts drags from the left mouse button.

    Some mice report their side buttons as mouse-button events that Qt's item
    view can otherwise treat like normal presses/moves. For a file manager that
    is dangerous and annoying: Back/Forward mouse buttons should navigate, not
    start a drag/drop operation. This subclass records whether the current drag
    gesture began with the left button and refuses to start a Qt drag otherwise.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._left_drag_started = False

    def mousePressEvent(self, event):
        self._left_drag_started = event.button() == Qt.MouseButton.LeftButton
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._left_drag_started = False

    def startDrag(self, supported_actions):
        if self._left_drag_started:
            super().startDrag(supported_actions)


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

        self._history: list[Path] = []
        self._history_index = -1
        self._middle_pressed_index = QtCore.QPersistentModelIndex()

        self.model = QtWidgets.QFileSystemModel(self)
        self.model.setRootPath(str(Path.home()))
        self.model.setFilter(self._make_filters())

        self.view = LeftDragTreeView()
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

        self.back_button = QtWidgets.QToolButton(text="←")
        self.back_button.setToolTip("Back")
        self.back_button.clicked.connect(self.go_back)

        self.forward_button = QtWidgets.QToolButton(text="→")
        self.forward_button.setToolTip("Forward")
        self.forward_button.clicked.connect(self.go_forward)

        up = QtWidgets.QToolButton(text="↑")
        up.setToolTip("Parent folder")
        up.clicked.connect(self.go_up)

        refresh = QtWidgets.QToolButton(text="⟳")
        refresh.setToolTip("Refresh")
        refresh.clicked.connect(self.refresh)

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.back_button)
        row.addWidget(self.forward_button)
        row.addWidget(up)
        row.addWidget(refresh)
        row.addWidget(self.path_bar, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
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

    def _normalise_path(self, path: str | Path) -> Path:
        p = Path(path).expanduser().resolve(strict=False)
        if not p.exists():
            p = Path.home()
        if p.is_file():
            p = p.parent
        return p

    def _push_history(self, path: Path) -> None:
        if self._history_index >= 0 and self._history and self._history[self._history_index] == path:
            self._update_history_buttons()
            return

        if self._history_index < len(self._history) - 1:
            self._history = self._history[: self._history_index + 1]

        self._history.append(path)
        self._history_index = len(self._history) - 1
        self._update_history_buttons()

    def _update_history_buttons(self) -> None:
        self.back_button.setEnabled(self._history_index > 0)
        self.forward_button.setEnabled(0 <= self._history_index < len(self._history) - 1)

    def set_path(self, path: str | Path, add_history: bool = True) -> None:
        p = self._normalise_path(path)
        self.current_path = p
        self.path_bar.setText(str(p))
        idx = self.model.setRootPath(str(p))
        self.view.setRootIndex(idx)
        if add_history:
            self._push_history(p)
        else:
            self._update_history_buttons()
        self.path_changed.emit(str(p))

    def can_go_back(self) -> bool:
        return self._history_index > 0

    def can_go_forward(self) -> bool:
        return 0 <= self._history_index < len(self._history) - 1

    def go_back(self):
        if not self.can_go_back():
            return
        self._history_index -= 1
        self.set_path(self._history[self._history_index], add_history=False)

    def go_forward(self):
        if not self.can_go_forward():
            return
        self._history_index += 1
        self.set_path(self._history[self._history_index], add_history=False)

    def go_to_bar_path(self):
        self.set_path(self.path_bar.text().strip())

    def go_up(self):
        self.set_path(self.current_path.parent)

    def refresh(self):
        self.model.setRootPath("")
        self.set_path(self.current_path, add_history=False)

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

    def _mouse_back_button(self):
        return getattr(Qt.MouseButton, "BackButton", None) or getattr(Qt.MouseButton, "XButton1", None)

    def _mouse_forward_button(self):
        return getattr(Qt.MouseButton, "ForwardButton", None) or getattr(Qt.MouseButton, "XButton2", None)

    def eventFilter(self, watched, event):
        if watched is self.view.viewport():
            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                back_button = self._mouse_back_button()
                forward_button = self._mouse_forward_button()

                if back_button is not None and event.button() == back_button:
                    self.go_back()
                    return True
                if forward_button is not None and event.button() == forward_button:
                    self.go_forward()
                    return True

                # Middle-click is reserved for opening folders in new tabs. Do not
                # let Qt's item view treat it like a drag/select gesture.
                if event.button() == Qt.MouseButton.MiddleButton:
                    self._middle_pressed_index = QtCore.QPersistentModelIndex(self.view.indexAt(event.pos()))
                    return True

            elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                back_button = self._mouse_back_button()
                forward_button = self._mouse_forward_button()

                if back_button is not None and event.button() == back_button:
                    return True
                if forward_button is not None and event.button() == forward_button:
                    return True

                if event.button() == Qt.MouseButton.MiddleButton:
                    idx = self.view.indexAt(event.pos())
                    if idx.isValid():
                        p = Path(self.model.filePath(idx))
                        if p.is_dir():
                            self.open_folder_in_new_tab.emit(str(p))
                    self._middle_pressed_index = QtCore.QPersistentModelIndex()
                    return True

            elif event.type() == QtCore.QEvent.Type.MouseMove:
                # Dragging files should only start while the left mouse button is
                # held. Side-button movement must not become a file drag.
                if not (event.buttons() & Qt.MouseButton.LeftButton):
                    return True

        return super().eventFilter(watched, event)

    def _context_menu(self, pos):
        self.context_menu_requested.emit(self, self.view.viewport().mapToGlobal(pos))
