import os
import math
from urllib.request import Request, urlopen
from urllib.parse import quote
import json
import pandas as pd
from src.lib.settings import setup_cache
from src.lib.season import get_season

setup_cache()

FPS = 25
DT = 1 / FPS

OPENF1_BASE = "https://api.openf1.org/v1"

HEADERS = {'User-Agent': 'Mozilla/5.0'}

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def get_available_sessions(season: int | None = None):
    if season is None:
        season = get_season()

    url = f"https://api.openf1.org/v1/sessions?year={season}&session_name=Race"
    req = Request(url, headers=HEADERS)

    try:
        with urlopen(req) as response:
            if response.status == 200:
                data = response.read().decode('utf-8')
                return json.loads(data)
    except Exception as e:
        print(f"Error fetching sessions: {e}")
    return []

def load_session(grand_prix: str | int = None, session_type: str = None, year: int = None, session_key: int = None):
    # Look up a session either by session_key, or by country + session type + year
    if session_key is not None:
        url = f"{OPENF1_BASE}/sessions?session_key={session_key}"
    else:
        if year is None:
            year = int(get_season())
        url = f"{OPENF1_BASE}/sessions?year={year}&country_name={grand_prix}&session_name={session_type}"
    req = Request(url, headers=HEADERS)

    try:
        with urlopen(req) as response:
             data = json.loads(response.read().decode())
    except Exception:
        data = []
        
    if not data:
        raise ValueError(f"No session found for {year} {grand_prix} {session_type}")
        
    return data[0]


def load_driver_location(session_key: int, driver_number: int, start_time: str = None, end_time: str = None):
    #fetch location coordinates (X, Y, Z) bounded by timestamps
    loc_url = f"{OPENF1_BASE}/location?session_key={session_key}&driver_number={driver_number}"
    if start_time and end_time:
        loc_url += f"&date>={quote(start_time, safe='')}&date<={quote(end_time, safe='')}"

    req_loc = Request(loc_url, headers=HEADERS)
    with urlopen(req_loc) as response:
        raw_data = json.loads(response.read().decode('utf-8'))
    
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
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req) as response:
            positions = json.loads(response.read().decode('utf-8'))

        leaders = [p for p in positions if p.get('position') == 1]
        if leaders:
            return leaders[-1]['driver_number']
    except Exception:
        pass
    return 1

def get_fastest_clean_lap(session_key: int, driver_number: int):
    laps_url = f"{OPENF1_BASE}/laps?session_key={session_key}&driver_number={driver_number}"
    req = Request(laps_url, headers=HEADERS)
    with urlopen(req) as response:
        laps = json.loads(response.read().decode('utf-8'))

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


def get_session_leaderboard(session_key: int, start_time: str, end_time: str):
    from src.insights.track_position_window import TrackGeometryProcessor
    drivers_url = f"{OPENF1_BASE}/drivers?session_key={session_key}"
    req = Request(drivers_url, headers=HEADERS)
    with urlopen(req) as response:
        drivers = json.loads(response.read().decode('utf-8'))

        track_proc = TrackGeometryProcessor(session_key)

    # Sort and map drivers 
    leaderboard = []
    for d in drivers:
        num = d.get("driver_number")
        if not num:
            continue

        loc_data = load_driver_location(session_key, driver_number=num, start_time=start_time, end_time=end_time)
        track_fraction = 0.0 
        lap_number = 1
        
        if loc_data and track_proc.has_real_track:
            # Grab the latest coordinate sample in time window
            latest_pt = loc_data[-1]
            x, y = latest_pt.get('x'), latest_pt.get('y')

            if x is not None and y is not None:
                # Find closest index along the reference track
                closest_idx = min(
                    range(len(track_proc.center_xs)),
                    key=lambda i: math.hypot(track_proc.center_xs[i] - x, track_proc.center_ys[i] - y)
                )

                track_fraction = track_proc.cum_fracs[closest_idx]

        # Lap number takes precedence, track fraction as decimal offset
        total_progress = lap_number + track_fraction

        leaderboard.append({
            "driver_number": num, 
            "acronym": d.get("name_acronym", "---"),
            "team": d.get("team_name", ""),
            "color": f"#{d.get('team_colour', '64748b')}",
            "lap": lap_number, 
            "progress": total_progress
        })

    # Sort descending
    leaderboard.sort(key=lambda item: item["progress"], reverse = True)
    for pos, driver in enumerate(leaderboard, start=1):
        driver["position"] = pos 
    return leaderboard

def load_driver_telemetry(session_key: int, driver_number: int = 1) -> pd.DataFrame:
    url = f"{OPENF1_BASE}/car_data?session_key={session_key}&driver_number={driver_number}"
    req = Request(url, headers=HEADERS)
    with urlopen(req) as response:
        raw_data = json.loads(response.read().decode())
        
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

if __name__ == '__main__':
    session_key = 11245
    print(get_session_leaderboard(session_key))