import gzip
import json
import os
from src.lib.settings import CACHE_DIR, setup_cache

# data/ holds races that were pre-built with scripts/build_race.py and are committed to git.
# cache/ holds things saved while the app runs (not committed).
DATA_DIR = "data"


def _candidates(folder: str, name: str):
    # Files are saved compressed (.json.gz). A plain .json file is still read,
    # so data saved before compression was added keeps working.
    return (os.path.join(folder, f"{name}.json.gz"), os.path.join(folder, f"{name}.json"))


def load_json(name: str):
    # Returns the saved data, or None if there is no usable file.
    # Looks in cache/ first, then in data/.
    for folder in (CACHE_DIR, DATA_DIR):
        for path in _candidates(folder, name):
            try:
                if path.endswith(".gz"):
                    with gzip.open(path, "rt", encoding="utf-8") as f:
                        return json.load(f)
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, EOFError, gzip.BadGzipFile):
                continue
    return None


def save_json(name: str, data) -> None:
    setup_cache()
    path = os.path.join(CACHE_DIR, f"{name}.json.gz")
    tmp_path = path + ".tmp"
    with gzip.open(tmp_path, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    os.replace(tmp_path, path)   # a crash can never leave a half-written file behind