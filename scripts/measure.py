"""Measure how long one dashboard load takes with and without saved data."""
import os
import shutil
import statistics
import sys
import time

from src import f1_data
from src.insights.track_position_window import get_track_visualization_payload

api_calls = 0
_original_urlopen = f1_data.urlopen


def _counting_urlopen(*args, **kwargs):
    global api_calls
    api_calls += 1
    return _original_urlopen(*args, **kwargs)


f1_data.urlopen = _counting_urlopen   # count every request that goes out to OpenF1


def dashboard_load(session_key: int):
    f1_data.load_session(session_key=session_key)
    get_track_visualization_payload(session_key)
    f1_data.get_session_drivers(session_key)
    f1_data.get_driver_locations_window(session_key, 0, f1_data.WINDOW_SECONDS)


def timed(session_key: int):
    global api_calls
    api_calls = 0
    start = time.perf_counter()
    dashboard_load(session_key)
    return time.perf_counter() - start, api_calls


def cold_run(session_key: int):
    folders = ("cache", "data")
    if any(os.path.exists(f + "_backup") for f in folders):
        print("A cache_backup or data_backup folder already exists. Rename or move it back first.")
        sys.exit(1)
    moved = [f for f in folders if os.path.isdir(f)]
    for f in moved:
        os.rename(f, f + "_backup")
    try:
        return timed(session_key)
    finally:
        for f in folders:                    # remove what the cold run created
            shutil.rmtree(f, ignore_errors=True)
        for f in moved:                      # put folders back
            os.rename(f + "_backup", f)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.measure <session_key>")
        sys.exit(1)
    key = int(sys.argv[1])

    cold_seconds, cold_calls = cold_run(key)
    print(f"Without saved data: {cold_seconds:.2f} s, {cold_calls} OpenF1 requests")

    runs = [timed(key) for _ in range(5)]
    warm_seconds = statistics.mean(r[0] for r in runs)
    warm_calls = max(r[1] for r in runs)
    print(f"With saved data (average of 5): {warm_seconds * 1000:.1f} ms, {warm_calls} OpenF1 requests")
    if warm_seconds > 0:
        print(f"About {cold_seconds / warm_seconds:.0f}x faster")   