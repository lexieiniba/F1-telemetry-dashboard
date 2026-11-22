import json
import os
from src.lib.settings import CACHE_DIR, setup_cache

DATA_DIR = "data"


def _path(folder: str, name: str) -> str:
    return os.path.join(folder, f"{name}.json")


def load_json(name: str):
    # Returns the saved data, or None if there is no usable file
    # Looks in cache/ first, then in data/
    for folder in (CACHE_DIR, DATA_DIR):
        try:
            with open(_path(folder, name), encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return None


def save_json(name: str, data) -> None:
    setup_cache()
    with open(_path(CACHE_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f)