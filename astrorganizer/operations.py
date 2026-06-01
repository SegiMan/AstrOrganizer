from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

try:
    from send2trash import send2trash
except Exception:  # pragma: no cover
    send2trash = None

TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".sh", ".bash", ".zsh", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".tex", ".bib", ".csv", ".tsv", ".xml", ".html", ".css", ".js", ".ts", ".java", ".c", ".cpp", ".h",
    ".hpp", ".rs", ".go", ".php", ".rb", ".lua", ".sql", ".desktop", ".log"
}

def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    try:
        with path.open("rb") as f:
            chunk = f.read(4096)
        if b"\0" in chunk:
            return False
        return True
    except Exception:
        return False

def open_default(path: str | Path) -> None:
    subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def reveal_in_parent(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_dir() else p.parent

def file_users(path: str | Path) -> list[str]:
    """Best-effort list of processes using a file.

    Linux does not provide a universal Windows-style mandatory file-in-use check.
    This uses psutil if available and is deliberately best-effort.
    """
    if psutil is None:
        return []
    target = str(Path(path).resolve(strict=False))
    users: list[str] = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            for opened in proc.open_files() or []:
                if opened.path == target:
                    users.append(f"{proc.info.get('name') or 'process'} ({proc.info.get('pid')})")
                    break
        except Exception:
            continue
    return users

def copy_paths(paths: Iterable[Path], destination: Path) -> list[Path]:
    out: list[Path] = []
    destination.mkdir(parents=True, exist_ok=True)
    for src in paths:
        dest = destination / src.name
        if src.resolve(strict=False) == dest.resolve(strict=False):
            continue
        if src.is_dir():
            if dest.exists():
                raise FileExistsError(str(dest))
            shutil.copytree(src, dest)
        else:
            if dest.exists():
                raise FileExistsError(str(dest))
            shutil.copy2(src, dest)
        out.append(dest)
    return out

def move_paths(paths: Iterable[Path], destination: Path) -> list[Path]:
    out: list[Path] = []
    destination.mkdir(parents=True, exist_ok=True)
    for src in paths:
        dest = destination / src.name
        if src.resolve(strict=False) == dest.resolve(strict=False):
            continue
        if dest.exists():
            raise FileExistsError(str(dest))
        out.append(Path(shutil.move(str(src), str(dest))))
    return out

def trash_paths(paths: Iterable[Path]) -> None:
    if send2trash is None:
        raise RuntimeError("send2trash is unavailable")
    for p in paths:
        send2trash(str(p))

def delete_paths_permanently(paths: Iterable[Path]) -> None:
    for p in paths:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink(missing_ok=True)

def batch_rename(paths: list[Path], prefix: str = "", suffix: str = "", remove_prefix: str = "", remove_suffix: str = "") -> list[tuple[Path, Path]]:
    changes: list[tuple[Path, Path]] = []
    for p in paths:
        stem = p.stem
        ext = p.suffix
        name = p.name
        if p.is_dir():
            stem, ext = name, ""
        if remove_prefix and stem.startswith(remove_prefix):
            stem = stem[len(remove_prefix):]
        if remove_suffix and stem.endswith(remove_suffix):
            stem = stem[: -len(remove_suffix)]
        new_name = f"{prefix}{stem}{suffix}{ext}"
        new_path = p.with_name(new_name)
        if new_path != p:
            if new_path.exists():
                raise FileExistsError(str(new_path))
            changes.append((p, new_path))
    for old, new in changes:
        old.rename(new)
    return changes
