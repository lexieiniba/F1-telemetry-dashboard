"""One-off: compress the plain .json files in data/ into .json.gz.
Each file is checked after compressing, and only then is the plain file removed.
"""
import gzip
import json
import os

from src.lib.cache import DATA_DIR


def compress(folder: str = DATA_DIR):
    before = after = count = 0
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(folder, name)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        gz_path = path + ".gz"
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            if json.load(f) != data:
                os.remove(gz_path)
                raise RuntimeError(f"Check failed for {name}, nothing was removed")
        before += os.path.getsize(path)
        after += os.path.getsize(gz_path)
        os.remove(path)
        count += 1
    if count:
        print(f"Compressed {count} files: {before / 1e6:.2f} MB -> {after / 1e6:.2f} MB")
    else:
        print("Nothing to compress")


if __name__ == "__main__":
    compress()