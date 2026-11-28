import math
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import quote
import json
import pandas as pd
from src.lib.settings import setup_cache
from src.lib.season import get_season
from src.lib.cache import load_json, save_json

setup_cache()


OPENF1_BASE = "https://api.openf1.org/v1"

HEADERS = {'User-Agent': 'Mozilla/5.0'}


FETCH_TIMEOUT = 15 # seconds to wait for OpenF1

class OpenF1Unavailable(Exception):
    # OpenF1 cannot be used right now: locked during a live session (401), rate limited (429),
    # having a server problem (5xx), too slow, or unreachable. `status` holds the HTTP code
    # when there is one. A 404 is not in this group: it means "no data for this request"
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status

class DataNotFound(ValueError):
    # OpenF1 is working, but has no data (unknown session, or a race
    # that has not happened yet)
    pass


def fetch_json(url: str):
    # Ask OpenF1 for a URL and return the parsed JSON
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=FETCH_TIMEOUT) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as e:
        if e.code == 401:
            raise OpenF1Unavailable("OpenF1 is locked during a live session", status=401) from e
        if e.code == 429:
            raise OpenF1Unavailable("OpenF1 rate limit reached", status=429) from e
        if e.code >= 500:
            raise OpenF1Unavailable(f"OpenF1 server error ({e.code})", status=e.code) from e
        if e.code == 404:
            return []
        raise    
    except OSError as e:    # timeouts, connection problems, no internet
        raise OpenF1Unavailable(f"Could not reach OpenF1: {e}") from e



def get_available_sessions(season: int):
    # Save the list of season's races
    # Raises OpenF1Unavailable if OpenF1 is locked or down.

    url = f"https://api.openf1.org/v1/sessions?year={season}&session_name=Race"
    sessions = fetch_json(url)
    if sessions:
        save_json(f"sessions_{season}", sessions)
    return sessions

def load_season_sessions(season: int):
    return load_json(f"sessions_{season}") or []

def get_available_sessions(season: int | None = None):
    if season is None:
        season = get_season()

    url = f"https://api.openf1.org/v1/sessions?year={season}&session_name=Race"

    try:
        return fetch_json(url)
    except Exception as e:
        print(f"Error fetching sessions: {e}")
    return []

def load_session(grand_prix: str | int = None, session_type: str = None, year: int = None, session_key: int = None):
    # Look up a session either by session_key, or by country + session type + year
    if session_key is not None:
        cached = load_json(f"session_{session_key}")
        if cached:
            return cached
        url = f"{OPENF1_BASE}/sessions?session_key={session_key}"
    else:
        if year is None:
            year = int(get_season())
        url = f"{OPENF1_BASE}/sessions?year={year}&country_name={grand_prix}&session_name={session_type}"

    try:
        data = fetch_json(url)
    except OpenF1Unavailable:
        raise
    except Exception as e:
        print(f"load_session error: {e}")
        data = []
        
    if not data:
        raise ValueError(f"No session found for {year} {grand_prix} {session_type}")

    if session_key is not None:
        save_json(f"session_{session_key}", data[0])
    return data[0]


def load_driver_location(session_key: int, driver_number: int, start_time: str = None, end_time: str = None):
    #fetch location coordinates (X, Y, Z) bounded by timestamps
    loc_url = f"{OPENF1_BASE}/location?session_key={session_key}&driver_number={driver_number}"
    if start_time and end_time:
        loc_url += f"&date>={quote(start_time, safe='')}&date<={quote(end_time, safe='')}"

    raw_data = fetch_json(loc_url)
    
    return [
        {
            'x': pt.get('x'), 
            'y': pt.get('y'), 
            'z': pt.get('z', 0.0),
            'date': pt.get('date'),
            'driver_number': driver_number
        }
        for pt in raw_data
        if pt.get('x') is not None and pt.get('y') is not None
    ]

def get_winning_driver(session_key: int):
    url = f"{OPENF1_BASE}/position?session_key={session_key}"
    positions = fetch_json(url)
    leaders = [p for p in positions if p.get('position') == 1]
    if not leaders:
        raise ValueError(f"No position data for session {session_key}, so the winner is unknown")
    return leaders[-1]['driver_number']

def get_fastest_clean_lap(session_key: int, driver_number: int):
    laps_url = f"{OPENF1_BASE}/laps?session_key={session_key}&driver_number={driver_number}"
    laps = fetch_json(laps_url)

    clean = [
        lap for lap in laps
        if lap.get('lap_duration') and lap.get('date_start') and not lap.get('is_pit_out_lap')
    ]

    if not clean:
        raise ValueError(f"No clean laps found for driver {driver_number}")
    return min(clean, key=lambda lap: lap['lap_duration'])

def map_circuit_coordinates(session_key: int, driver_number: int | None = None):
    driver = driver_number if driver_number is not None else get_winning_driver(session_key)
    
    lap = get_fastest_clean_lap(session_key, driver)
    start = pd.Timestamp(lap['date_start'])
    end = start + pd.Timedelta(seconds=lap["lap_duration"])

    return load_driver_location(session_key, driver, start.isoformat(), end.isoformat())

def get_session_drivers(session_key: int):
    cached = load_json(f"driverinfo_{session_key}")
    if cached:
        return cached

    url =f"{OPENF1_BASE}/drivers?session_key={session_key}"
    data = fetch_json(url)

    drivers = [
        {
            "driver_number": d.get("driver_number"),
            "acronym": d.get("name_acronym", "---"),
            "full_name": d.get("full_name", ""),
            "team": d.get("team_name", ""),
            "team_colour": d.get("team_colour") or "64748b",
            "headshot_url": d.get("headshot_url") or "",
        }
        for d in data if d.get("driver_number")
    ]

    if drivers:
        save_json(f"driverinfo_{session_key}", drivers)
    return drivers

def get_session_positions(session_key: int):
    #Every position change in the session as [seconds since session start, driver_number, position]
    #One request for the entire session
    cache_name = f"positions_{session_key}"
    cached = load_json(cache_name)
    if cached:
        return cached

    session = load_session(session_key=session_key)
    start = pd.Timestamp(session['date_start'])

    url = f"{OPENF1_BASE}/position?session_key={session_key}"
    raw = fetch_json(url)

    changes = []
    for row in raw:
        if row.get('date') is None or row.get('driver_number') is None or row.get('position') is None:
            continue
        seconds = (pd.Timestamp(row['date']) - start).total_seconds()
        changes.append([round(seconds, 1), row['driver_number'], row['position']])
    changes.sort()

    if changes:
        save_json(cache_name, changes)
    return changes

def get_race_start(session_key: int, allow_api: bool = True) -> float:
    # Seconds after the session start when the race itself begins (lap 1 starts at lights out).
    # The session starts earlier, with the formation lap. Take the middle lap-1 start time
    # across all drivers. Returns 0 when it is not known.
    cache_name = f"racestart_{session_key}"
    cached = load_json(cache_name)
    if cached is not None:
        return cached["offset"]
    if not allow_api:
        return 0.0

    session = load_session(session_key=session_key)
    if session.get('session_name') not in ('Race', 'Sprint'):
        return 0.0
    start = pd.Timestamp(session['date_start'])

    url = f"{OPENF1_BASE}/laps?session_key={session_key}&lap_number=1"
    laps = fetch_json(url)

    starts = sorted(pd.Timestamp(lap['date_start']) for lap in laps if lap.get('date_start'))
    if not starts:
        return 0.0
    offset = round((starts[len(starts) // 2] - start).total_seconds(), 1)
    save_json(cache_name, {"offset": offset})
    return offset

def _load_location_samples(session_key: int):
    # Every saved location sample for the whole session
    # Sort by time
    windows = -(-get_session_duration(session_key) // WINDOW_SECONDS)
    samples = {}
    for i in range(windows):
        offset = i * WINDOW_SECONDS
        chunk = load_json(f"locations_{session_key}_{offset}_{WINDOW_SECONDS}") or {}
        for number, points in chunk.items():
            if points:
                samples.setdefault(number, []).extend((p['t'] + offset, p['x'], p['y']) for p in points)
    for points in samples.values():
        points.sort()
    return samples

def _last_move_time(points, radius: float):
    # The last time the car was farther than `radius` from the spot where it finally stopped.
    # Returns -1 if it never was, which means the car never moved.
    _, final_x, final_y = points[-1]
    for t, x, y in reversed(points):
        if math.hypot(x - final_x, y - final_y) > radius:
            return round(t, 1)
    return -1

def build_driver_activity(session_key: int):
    # For each driver, the last time (seconds after the session start) the car moved.
    # After that moment the car is parked or retired, and the page stops drawing it.
    samples = _load_location_samples(session_key)
    if not samples:
        return {}

    xs = [x for points in samples.values() for _, x, _ in points]
    ys = [y for points in samples.values() for _, _, y in points]
    radius = 0.01 * max(max(xs) - min(xs), max(ys) - min(ys))   # 1% of the track size

    activity = {number: _last_move_time(points, radius) for number, points in samples.items()}
    save_json(f"activity_{session_key}", activity)
    return activity

def get_driver_activity(session_key: int):
    # The saved result of build_driver_activity, or an empty dict if there is none
    return load_json(f"activity_{session_key}") or {}

WINDOW_SECONDS = 120
def get_session_duration(session_key: int):
    saved = load_json(f"duration_{session_key}")
    if saved:
        return saved["duration"]
    session = load_session(session_key=session_key)
    start = pd.Timestamp(session['date_start'])
    end = pd.Timestamp(session['date_end'])
    return int((end - start).total_seconds())

def get_driver_locations_window(session_key: int, offset: int = 0, duration: int = 120, step: int = 2):
    # Positions of ALL drivers for a short time window, using a single API request
    # (the free API only allows ~30 requests per minute, so never loop over drivers).
    # offset = seconds after the session start, duration = length of the window in seconds.
    duration = min(duration, 300)  # keep the response a reasonable size
    cache_name = f"locations_{session_key}_{offset}_{duration}"
    cached = load_json(cache_name)
    if cached:
        return cached
    if load_json(f"duration_{session_key}") is not None:
        return {}
    

    session = load_session(session_key=session_key)
    start = pd.Timestamp(session['date_start']) + pd.Timedelta(seconds=offset)
    end = start + pd.Timedelta(seconds=duration)

    url = (
        f"{OPENF1_BASE}/location?session_key={session_key}"
        f"&date>={quote(start.isoformat(), safe='')}&date<={quote(end.isoformat(), safe='')}"
    )
    raw = fetch_json(url)

    by_driver = {}
    for pt in raw:
        if pt.get('x') is None or pt.get('y') is None or pt.get('driver_number') is None:
            continue
        seconds = (pd.Timestamp(pt['date']) - start).total_seconds()
        by_driver.setdefault(str(pt['driver_number']), []).append(
            {'t': round(seconds, 2), 'x': pt['x'], 'y': pt['y']}
        )

    # sort by time, then keep every `step`-th point to shrink the data
    result = {}
    for number, points in by_driver.items():
        points.sort(key=lambda p: p['t'])
        result[number] = points[::step]

    if result:
        save_json(cache_name, result)
    return result

def load_driver_telemetry(session_key: int, driver_number: int = 1) -> pd.DataFrame:
    url = f"{OPENF1_BASE}/car_data?session_key={session_key}&driver_number={driver_number}"
    raw_data = fetch_json(url)
        
    df = pd.DataFrame(raw_data)
    
    if not df.empty:
        df = df.rename(columns={
            'speed': 'Speed',
            'throttle': 'Throttle',
            'brake': 'Brake',
            'n_gear': 'Gear',
            'rpm': 'RPM',
            'date': 'Time'
        })
        
    return df

def get_circuit_geometry(session_key: int):
    session = load_session(session_key=session_key)

    circuit_key = session.get("circuit_key")
    year = session.get("year")

    if not circuit_key or not year:
        raise DataNotFound("Circuit information is unavailable")

    cache_name = f"circuit_geometry_{circuit_key}_{year}"

    cached = load_json(cache_name)
    if cached:
        return cached

    url = (
        f"https://api.multiviewer.app/api/v1/circuits/"
        f"{circuit_key}/{year}"
    )

    geometry = fetch_json(url)

    if not isinstance(geometry, dict) or not geometry.get("x") or not geometry.get("y"):
        raise DataNotFound("Circuit geometry is unavailable")

    save_json(cache_name, geometry)

    return geometry