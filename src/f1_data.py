
from urllib.request import Request, urlopen
import json
import pandas as pd
from src.lib.settings import setup_cache
from src.lib.season import get_season

setup_cache()

FPS = 25
DT = 1 / FPS

OPENF1_BASE = "https://api.openf1.org/v1"

HEADERS = {'User-Agent': 'Mozilla/5.0'}

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

def load_session(grand_prix: str | int, session_type: str, year: int = None):
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
        loc_url += f"&date>={start_time}&date<={end_time}"

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

def map_circuit_coordinates(session_key: int, driver_number: int | None = None):
    winner_num = driver_number if driver_number is not None else get_winning_driver(session_key)

    laps_url = f"{OPENF1_BASE}/laps?session_key={session_key}&driver_number={winner_num}"
    req_laps = Request(laps_url, headers = HEADERS)
    with urlopen(req_laps) as response:
        laps = json.loads(response.read().decode('utf-8'))

    start_time = laps[2]['date_start']
    end_time = laps[3]['date_start']

    return load_driver_location(session_key, winner_num, start_time, end_time)


def get_session_leaderboard(session_key: int, target_timestamp: str = None):
    drivers_url = f"{OPENF1_BASE}/drivers?session_key={session_key}"
    req = Request(drivers_url, headers=HEADERS)
    with urlopen(req) as response:
        drivers = json.loads(response.read().decode('utf-8'))

    # Sort and map drivers 
    leaderboard = [
        {
            "driver_number": d.get("driver_number"),
            "acronym": d.get("name_acronym", "---"),
            "team": d.get("team_name", "")
        }
        for d in drivers
    ]
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