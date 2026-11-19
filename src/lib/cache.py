import json
import os
from src.lib.settings import CACHE_DIR, setup_cache


def _path(name: str) -> str:
    return os.path.join(CACHE_DIR, f"{name}.json")


def load_json(name: str):
    # Returns the saved data, or None if there is no usable cache file
    try:
        with open(_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_json(name: str, data) -> None:
    setup_cache()
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f)