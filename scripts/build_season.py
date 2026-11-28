"""Build every finished race of a season.
Races that are already built are skipped, newest races are built first, and if OpenF1 gets locked the script stops cleanly.
The same command will run again later and continue"""

import sys

import pandas as pd

from scripts.build_race import PAUSE, BuildFailed, build
from src.f1_data import DataNotFound, OpenF1Unavailable, load_season_sessions, refresh_season_sessions
from src.lib.cache import load_json
from src.lib.season import get_season


def is_built(session_key: int) -> bool:
    # build_race writes this file last, so it means the whole race was built
    return load_json(f"duration_{session_key}") is not None


def finished_races(sessions, now):
    # Races that have ended, newest first. Cancelled races are left out.
    races = [s for s in sessions if not s.get("is_cancelled") and pd.Timestamp(s["date_end"]) < now]
    return sorted(races, key=lambda s: s["date_start"], reverse=True)


def build_season(season: int, limit: int | None = None, pause: float = PAUSE, now=None):
    now = now if now is not None else pd.Timestamp.now(tz="UTC")
    summary = {"built": [], "failed": [], "already_built": 0, "stopped": False}

    try:
        sessions = refresh_season_sessions(season)
    except OpenF1Unavailable as e:
        print(f"{e}. Try again later (a live session may be in progress).")
        summary["stopped"] = True
        return summary
    if not sessions:
        sessions = load_season_sessions(season)

    races = finished_races(sessions, now)
    todo = [s for s in races if not is_built(s["session_key"])]
    summary["already_built"] = len(races) - len(todo)
    print(f"{season}: {len(races)} finished races, {summary['already_built']} already built, {len(todo)} to build")
    if limit is not None:
        todo = todo[:limit]

    for n, session in enumerate(todo, 1):
        label = f"{session.get('location') or session['country_name']} {session['year']}"
        print(f"\n[{n}/{len(todo)}] {label} (session {session['session_key']})")
        try:
            build(session["session_key"], pause)
            summary["built"].append(label)
        except (BuildFailed, DataNotFound) as e:
            print(f"  skipped: {e}")
            summary["failed"].append(label)
        except OpenF1Unavailable as e:
            print(f"\nStopped: {e}. Run the same command again later and it will continue.")
            summary["stopped"] = True
            break

    print(f"\nDone: {len(summary['built'])} built, {len(summary['failed'])} skipped, "
          f"{summary['already_built']} were already built" + (" (stopped early)" if summary["stopped"] else ""))
    return summary


if __name__ == "__main__":
    args = sys.argv[1:]
    limit = None
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i:i + 2]
    build_season(int(args[0]) if args else get_season(), limit)