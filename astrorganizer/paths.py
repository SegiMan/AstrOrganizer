from __future__ import annotations
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir, user_cache_dir
from . import __app_name__

APP_ID = "astrorganizer"
CONFIG_DIR = Path(user_config_dir(APP_ID, appauthor=False))
DATA_DIR = Path(user_data_dir(APP_ID, appauthor=False))
CACHE_DIR = Path(user_cache_dir(APP_ID, appauthor=False))

for _p in (CONFIG_DIR, DATA_DIR, CACHE_DIR):
    _p.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = CONFIG_DIR / "settings.json"
TAGS_DB = DATA_DIR / "tags.sqlite3"
LOG_FILE = CACHE_DIR / "astrorganizer.log"
