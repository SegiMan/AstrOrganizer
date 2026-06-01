from __future__ import annotations
import sqlite3
from pathlib import Path
from .paths import TAGS_DB

class TagStore:
    def __init__(self) -> None:
        self.db = sqlite3.connect(TAGS_DB)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS file_tags (path TEXT NOT NULL, tag TEXT NOT NULL, PRIMARY KEY(path, tag))"
        )
        self.db.commit()

    @staticmethod
    def norm_path(path: str | Path) -> str:
        return str(Path(path).expanduser().resolve(strict=False))

    @staticmethod
    def norm_tag(tag: str) -> str:
        tag = tag.strip()
        if not tag:
            return ""
        return tag if tag.startswith("#") else f"#{tag}"

    def get_tags(self, path: str | Path) -> list[str]:
        p = self.norm_path(path)
        cur = self.db.execute("SELECT tag FROM file_tags WHERE path=? ORDER BY tag COLLATE NOCASE", (p,))
        return [r[0] for r in cur.fetchall()]

    def set_tags(self, path: str | Path, tags: list[str]) -> None:
        p = self.norm_path(path)
        clean = sorted({self.norm_tag(t) for t in tags if self.norm_tag(t)})
        with self.db:
            self.db.execute("DELETE FROM file_tags WHERE path=?", (p,))
            self.db.executemany("INSERT OR IGNORE INTO file_tags(path, tag) VALUES (?, ?)", [(p, t) for t in clean])

    def add_tags(self, path: str | Path, tags: list[str]) -> None:
        p = self.norm_path(path)
        clean = sorted({self.norm_tag(t) for t in tags if self.norm_tag(t)})
        with self.db:
            self.db.executemany("INSERT OR IGNORE INTO file_tags(path, tag) VALUES (?, ?)", [(p, t) for t in clean])

    def search_tag(self, tag: str) -> list[str]:
        t = self.norm_tag(tag)
        cur = self.db.execute("SELECT path FROM file_tags WHERE tag=? ORDER BY path COLLATE NOCASE", (t,))
        return [r[0] for r in cur.fetchall() if Path(r[0]).exists()]

    def tags_for_many(self, paths: list[str | Path]) -> dict[str, list[str]]:
        return {self.norm_path(p): self.get_tags(p) for p in paths}
