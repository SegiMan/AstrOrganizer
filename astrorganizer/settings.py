from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .paths import SETTINGS_FILE

DEFAULTS: dict[str, Any] = {
    "show_hidden": False,
    "folders_first": True,
    "hover_tags": True,
    "restore_tabs": True,
    "tabs": [],
    "bookmarks": [str(Path.home())],
    "split_view": False,
    "icon_size": 32,
}

class Settings:
    def __init__(self) -> None:
        self.data = DEFAULTS.copy()
        self.load()

    def load(self) -> None:
        if SETTINGS_FILE.exists():
            try:
                loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data.update(loaded)
            except Exception:
                pass

    def save(self) -> None:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()
