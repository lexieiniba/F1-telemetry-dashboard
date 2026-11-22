"""Download a whole race once and save it in data/, so the app never needs OpenF1 at runtime.

Run from the project root with the venv active, while OpenF1 is open (not during a live session):

    python -m scripts.build_race 11234

It is safe to stop and run again: windows that are already saved are skipped.
"""
import glob
import os
import shutil
import sys
import time
from urllib.error import HTTPError

from src.f1_data import (
    WINDOW_SECONDS,
    get_driver_locations_window,
    get_session_drivers,
    get_session_duration,
    load_session,
)
from src.insights.track_position_window import get_track_visualization_payload
from src.lib.cache import DATA_DIR, load_json, save_json
from src.lib.settings import CACHE_DIR

PAUSE = 2.5   # seconds to wait between API requests (the free limit is about 30 per minute)
STEP = 3      # keep every 3rd location sample (about one point per second)


def call_api(label, fn, *args, **kwargs):
    """Run one API call. Retries when rate limited, stops if OpenF1 is locked."""
    for _ in range(4):
        try:
            return fn(*args, **kwargs)
        except HTTPError as e:
            if e.code == 429:
                print(f"  rate limited on {label}, waiting 30 seconds...")
                time.sleep(30)
            elif e.code == 401:
                print("OpenF1 is locked right now (a live session is in progress). Try again after it ends.")
                sys.exit(1)
            elif e.code == 404:
                return None   # no data for this request
            else:
                raise
    print(f"  giving up on {label} after several tries")
    return None


def build(session_key: int, pause: float = PAUSE):
    print(f"Building session {session_key}")

    try:
        session = load_session(session_key=session_key)
    except ValueError:
        print("Could not load the session. If the line above says 401, OpenF1 is locked; wait and retry.")
        sys.exit(1)
    save_json(f"session_{session_key}", session)   # make sure the session is saved for copy_to_data
    time.sleep(pause)

    duration = get_session_duration(session_key)
    windows = -(-duration // WINDOW_SECONDS)   # round up
    print(f"{session['country_name']} {session['year']}: {duration // 60} minutes, {windows} windows")

    print("Drivers...")
    call_api("drivers", get_session_drivers, session_key)
    time.sleep(pause)

    print("Track outline...")
    track = call_api("track", get_track_visualization_payload, session_key)
    time.sleep(pause)
    if not track or not track.get("has_real_track"):
        print("Could not build the track outline, stopping.")
        sys.exit(1)

    saved = skipped = empty = 0
    for i in range(windows):
        offset = i * WINDOW_SECONDS
        name = f"locations_{session_key}_{offset}_{WINDOW_SECONDS}"
        if load_json(name) is not None:
            skipped += 1
            continue
        result = call_api(f"window {i + 1}/{windows}", get_driver_locations_window,
                          session_key, offset, WINDOW_SECONDS, STEP)
        if result:
            saved += 1
        else:
            empty += 1
        print(f"  window {i + 1}/{windows} {'saved' if result else 'no data'}")
        time.sleep(pause)

    copy_to_data(session_key, f"track{session['circuit_key']}_{session['year']}")
    print(f"Done: {saved} windows downloaded, {skipped} already saved, {empty} with no data.")


def copy_to_data(session_key: int, track_name: str):
    os.makedirs(DATA_DIR, exist_ok=True)
    names = [f"session_{session_key}", f"driverinfo_{session_key}", track_name]
    files = [os.path.join(CACHE_DIR, f"{n}.json") for n in names]
    files += glob.glob(os.path.join(CACHE_DIR, f"locations_{session_key}_*.json"))
    total = 0
    for path in files:
        if os.path.exists(path):
            shutil.copy2(path, DATA_DIR)
            total += os.path.getsize(path)
    print(f"Copied {len(files)} files to {DATA_DIR}/ ({total / 1_000_000:.1f} MB)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.build_race <session_key>")
        sys.exit(1)
    build(int(sys.argv[1]))