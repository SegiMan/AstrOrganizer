from __future__ import annotations
import os
import shutil
from pathlib import Path
from .qt_compat import QtCore, QtGui, QtWidgets, Qt, QUrl
from .settings import Settings
from .tags import TagStore
from .file_panel import FilePanel
from .dialogs import PropertiesDialog, TagDialog, BatchRenameDialog, SearchDialog
from .operations import (
    open_default, copy_paths, move_paths, trash_paths, delete_paths_permanently,
    batch_rename, file_users, is_text_file
)
from . import __app_name__, __version__

class Workspace(QtWidgets.QSplitter):
    active_panel_changed = QtCore.Signal(object)
    def __init__(self, path: str, settings: Settings, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.settings = settings
        self.left = FilePanel(path, settings)
        self.right = FilePanel(path, settings)
        self.addWidget(self.left)
        self.addWidget(self.right)
        self.right.setVisible(bool(settings.get("split_view", False)))
        self.active = self.left
        for p in (self.left, self.right):
            p.view.clicked.connect(lambda _idx, panel=p: self.set_active(panel))
            p.path_bar.focusInEvent = self._focus_wrapper(p.path_bar.focusInEvent, p)
    def _focus_wrapper(self, old, panel):
        def wrapped(event):
            self.set_active(panel)
            old(event)
        return wrapped
    def set_active(self, panel):
        self.active = panel
        self.active_panel_changed.emit(panel)
    def set_split(self, enabled: bool):
        self.right.setVisible(enabled)
    def paths(self) -> list[str]:
        return [str(self.left.current_path), str(self.right.current_path)]

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.tags = TagStore()
        self.clipboard_mode: str | None = None
        self.clipboard_paths: list[Path] = []
        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.resize(1120, 720)
        self.tabs = QtWidgets.QTabWidget(movable=True, tabsClosable=True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        self.status = self.statusBar()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._load_tabs()
        if os.geteuid() == 0:
            QtWidgets.QMessageBox.warning(self, "Running as administrator", "AstrOrganizer is running with administrator/root rights. Be careful: file operations can affect system files.")

    def _build_actions(self):
        self.act_new_tab = QtGui.QAction("New tab", self, shortcut="Ctrl+T", triggered=lambda: self.add_tab(Path.home()))
        self.act_close_tab = QtGui.QAction("Close tab", self, shortcut="Ctrl+W", triggered=lambda: self.close_tab(self.tabs.currentIndex()))
        self.act_split = QtGui.QAction("Split view", self, checkable=True, checked=bool(self.settings.get("split_view", False)), triggered=self.toggle_split)
        self.act_hidden = QtGui.QAction("Show hidden files", self, shortcut="Ctrl+H", checkable=True, checked=bool(self.settings.get("show_hidden", False)), triggered=self.toggle_hidden)
        self.act_folders_first = QtGui.QAction("Folders first", self, checkable=True, checked=bool(self.settings.get("folders_first", True)), triggered=lambda v: self.settings.set("folders_first", bool(v)))
        self.act_search = QtGui.QAction("Search", self, shortcut="Ctrl+F", triggered=self.show_search)
        self.act_bookmark = QtGui.QAction("Bookmark current folder", self, shortcut="Ctrl+D", triggered=self.bookmark_current)
        self.act_quit = QtGui.QAction("Quit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.act_copy = QtGui.QAction("Copy", self, shortcut="Ctrl+C", triggered=lambda: self.copy_selected(False))
        self.act_cut = QtGui.QAction("Cut", self, shortcut="Ctrl+X", triggered=lambda: self.copy_selected(True))
        self.act_paste = QtGui.QAction("Paste", self, shortcut="Ctrl+V", triggered=self.paste_into_active)
        self.act_rename = QtGui.QAction("Rename", self, shortcut="F2", triggered=self.rename_selected)
        self.act_delete = QtGui.QAction("Move to Trash", self, shortcut="Delete", triggered=self.trash_selected)
        self.act_props = QtGui.QAction("Properties", self, shortcut="Alt+Return", triggered=self.properties_selected)
        self.act_tags = QtGui.QAction("Edit tags", self, triggered=self.edit_tags_selected)
        self.act_batch = QtGui.QAction("Batch rename", self, triggered=self.batch_rename_selected)

    def _build_menus(self):
        m = self.menuBar()
        filem = m.addMenu("File"); filem.addAction(self.act_new_tab); filem.addAction(self.act_close_tab); filem.addSeparator(); filem.addAction(self.act_quit)
        edit = m.addMenu("Edit"); [edit.addAction(a) for a in (self.act_cut, self.act_copy, self.act_paste, self.act_rename, self.act_delete, self.act_batch, self.act_tags, self.act_props)]
        view = m.addMenu("View"); [view.addAction(a) for a in (self.act_split, self.act_hidden, self.act_folders_first)]
        tools = m.addMenu("Tools"); tools.addAction(self.act_search); tools.addAction(self.act_bookmark)
        self.bookmarks_menu = m.addMenu("Bookmarks"); self.rebuild_bookmarks()

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        for a in (self.act_new_tab, self.act_split, self.act_hidden, self.act_search, self.act_bookmark):
            tb.addAction(a)

    def _load_tabs(self):
        restored = self.settings.get("tabs", []) if self.settings.get("restore_tabs", True) else []
        if not restored:
            restored = [str(Path.home())]
        for entry in restored:
            path = entry[0] if isinstance(entry, list) else entry
            self.add_tab(path)

    def add_tab(self, path: str | Path):
        ws = Workspace(str(path), self.settings)
        ws.left.context_menu_requested.connect(self.show_context_menu)
        ws.right.context_menu_requested.connect(self.show_context_menu)
        ws.left.open_folder_in_new_tab.connect(self.add_tab)
        ws.right.open_folder_in_new_tab.connect(self.add_tab)
        ws.left.selection_changed.connect(self.update_selection_status)
        ws.right.selection_changed.connect(self.update_selection_status)
        idx = self.tabs.addTab(ws, Path(path).name or str(path))
        self.tabs.setCurrentIndex(idx)
        ws.left.path_changed.connect(lambda p, w=ws: self._tab_path_changed(w, p))
        ws.right.path_changed.connect(lambda p, w=ws: self._tab_path_changed(w, p))
        return ws

    def _tab_path_changed(self, ws, path: str):
        idx = self.tabs.indexOf(ws)
        if idx >= 0:
            self.tabs.setTabText(idx, Path(path).name or path)

    def close_tab(self, idx: int):
        if self.tabs.count() <= 1:
            return
        self.tabs.removeTab(idx)

    def active_workspace(self) -> Workspace:
        return self.tabs.currentWidget()

    def active_panel(self) -> FilePanel:
        return self.active_workspace().active

    def selected_paths(self) -> list[Path]:
        return self.active_panel().selected_paths()

    def toggle_split(self, enabled: bool):
        self.settings.set("split_view", bool(enabled))
        for i in range(self.tabs.count()):
            self.tabs.widget(i).set_split(enabled)

    def toggle_hidden(self, enabled: bool):
        self.settings.set("show_hidden", bool(enabled))
        for i in range(self.tabs.count()):
            ws = self.tabs.widget(i); ws.left.apply_settings(); ws.right.apply_settings()

    def update_selection_status(self, paths: list[str]):
        if not paths:
            self.status.showMessage("Ready")
        elif len(paths) == 1:
            tags = self.tags.get_tags(paths[0])
            self.status.showMessage(f"{paths[0]}    {' '.join(tags)}")
        else:
            total = 0
            for p in map(Path, paths):
                try:
                    if p.is_file(): total += p.stat().st_size
                except Exception: pass
            self.status.showMessage(f"{len(paths)} items selected — known file size total: {total:,} bytes")

    def show_context_menu(self, panel: FilePanel, global_pos):
        panel.parent().set_active(panel)
        paths = panel.selected_paths()
        menu = QtWidgets.QMenu(self)
        open_with = menu.addMenu("Open with")
        open_default_action = open_with.addAction("Default application")
        open_default_action.triggered.connect(lambda: [open_default(p) for p in paths[:10]])
        custom = open_with.addAction("Custom command…")
        custom.triggered.connect(lambda: self.open_with_custom(paths))
        menu.addSeparator()
        for act in (self.act_cut, self.act_copy, self.act_paste, self.act_rename, self.act_delete, self.act_batch, self.act_tags, self.act_props):
            menu.addAction(act)
        menu.exec(global_pos)

    def open_with_custom(self, paths: list[Path]):
        if not paths: return
        cmd, ok = QtWidgets.QInputDialog.getText(self, "Open with command", "Command:")
        if ok and cmd.strip():
            import subprocess, shlex
            for p in paths:
                subprocess.Popen(shlex.split(cmd) + [str(p)])

    def copy_selected(self, cut: bool):
        paths = self.selected_paths()
        if not paths: return
        self.clipboard_paths = paths
        self.clipboard_mode = "cut" if cut else "copy"
        cb = QtWidgets.QApplication.clipboard()
        mime = QtCore.QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
        mime.setText("\n".join(str(p) for p in paths))
        cb.setMimeData(mime)
        self.status.showMessage(("Cut" if cut else "Copied") + f" {len(paths)} item(s)")

    def paste_into_active(self):
        dest = self.active_panel().current_path
        paths = self.clipboard_paths
        if not paths:
            urls = QtWidgets.QApplication.clipboard().mimeData().urls()
            paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        if not paths: return
        try:
            if self.clipboard_mode == "cut":
                move_paths(paths, dest)
                self.clipboard_paths = []; self.clipboard_mode = None
            else:
                copy_paths(paths, dest)
            self.active_panel().refresh()
        except FileExistsError as e:
            QtWidgets.QMessageBox.warning(self, "Name conflict", f"Destination already exists:\n{e}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Paste failed", str(e))

    def rename_selected(self):
        paths = self.selected_paths()
        if len(paths) != 1: return
        p = paths[0]
        new, ok = QtWidgets.QInputDialog.getText(self, "Rename", "New name:", text=p.name)
        if ok and new and new != p.name:
            target = p.with_name(new)
            if target.exists():
                QtWidgets.QMessageBox.warning(self, "Name conflict", f"{target} already exists."); return
            users = file_users(p)
            if users and QtWidgets.QMessageBox.question(self, "File in use", f"This file appears to be open by:\n{chr(10).join(users)}\n\nProceed anyway?") != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            try: p.rename(target); self.active_panel().refresh()
            except Exception as e: QtWidgets.QMessageBox.critical(self, "Rename failed", str(e))

    def trash_selected(self):
        paths = self.selected_paths()
        if not paths: return
        if QtWidgets.QMessageBox.question(self, "Move to Trash", f"Move {len(paths)} item(s) to Trash?") != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try: trash_paths(paths); self.active_panel().refresh()
        except Exception as e: QtWidgets.QMessageBox.critical(self, "Trash failed", str(e))

    def properties_selected(self):
        paths = self.selected_paths()
        if not paths: return
        tags = self.tags.get_tags(paths[0]) if len(paths) == 1 else None
        PropertiesDialog(paths, tags, self).exec()

    def edit_tags_selected(self):
        paths = self.selected_paths()
        if not paths: return
        current = self.tags.get_tags(paths[0]) if len(paths) == 1 else []
        dlg = TagDialog(current, self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            for p in paths: self.tags.set_tags(p, dlg.tags())
            self.update_selection_status([str(p) for p in paths])

    def batch_rename_selected(self):
        paths = self.selected_paths()
        if not paths: return
        dlg = BatchRenameDialog(len(paths), self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted: return
        prefix, suffix, rp, rs = dlg.values()
        busy = []
        for p in paths:
            busy.extend([f"{p}: {u}" for u in file_users(p)])
        if busy and QtWidgets.QMessageBox.question(self, "Some files appear open", "\n".join(busy[:20]) + "\n\nProceed anyway?") != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try:
            changes = batch_rename(paths, prefix, suffix, rp, rs)
            self.status.showMessage(f"Renamed {len(changes)} item(s)")
            self.active_panel().refresh()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Batch rename failed", str(e))

    def bookmark_current(self):
        p = str(self.active_panel().current_path)
        marks = list(self.settings.get("bookmarks", []))
        if p not in marks:
            marks.append(p); self.settings.set("bookmarks", marks); self.rebuild_bookmarks()

    def rebuild_bookmarks(self):
        self.bookmarks_menu.clear()
        for p in self.settings.get("bookmarks", []):
            act = self.bookmarks_menu.addAction(p)
            act.triggered.connect(lambda _=False, path=p: self.active_panel().set_path(path))

    def show_search(self):
        dlg = SearchDialog(self)
        dlg.set_callback(self.perform_search)
        dlg.open_path_requested.connect(lambda p: self.add_tab(Path(p).parent if Path(p).is_file() else p))
        dlg.exec()

    def perform_search(self, dlg: SearchDialog):
        base = self.active_panel().current_path
        q = dlg.query.text()
        dlg.results.clear()
        if not q.strip(): return
        case = dlg.case.isChecked()
        recursive = dlg.recursive.isChecked()
        exact = dlg.exact.isChecked()
        content = dlg.content.isChecked()
        found = 0
        if q.strip().startswith("#") and not content:
            for p in self.tags.search_tag(q.strip()):
                if str(p).startswith(str(base)):
                    dlg.add_result(p, "tag") ; found += 1
            dlg.status.setText(f"Found {found} result(s).")
            return
        it = base.rglob("*") if recursive else base.iterdir()
        needle = q if case else q.lower()
        for p in it:
            try:
                name = p.name if case else p.name.lower()
                match = (name == needle) if exact else (needle in name)
                if match:
                    dlg.add_result(str(p), "name"); found += 1
                elif content and p.is_file() and is_text_file(p):
                    try:
                        txt = p.read_text(encoding="utf-8", errors="ignore")
                        hay = txt if case else txt.lower()
                        if needle in hay:
                            dlg.add_result(str(p), "content"); found += 1
                    except Exception: pass
                if found % 50 == 0:
                    QtWidgets.QApplication.processEvents()
            except Exception:
                continue
        dlg.status.setText(f"Found {found} result(s).")

    def closeEvent(self, event):
        tabs = []
        for i in range(self.tabs.count()):
            ws = self.tabs.widget(i)
            tabs.append(ws.paths())
        self.settings.set("tabs", tabs)
        super().closeEvent(event)
