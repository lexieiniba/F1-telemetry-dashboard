
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
    
    with urlopen(req) as response:
        data = json.loads(response.read().decode())
        
    if not data:
        raise ValueError(f"No session found for {year} {grand_prix} {session_type}")
        
    return data[0]

def load_driver_location(session_key: int, driver_number: int = 1):
    #fetch third lap and find time window
    laps_url = f"{OPENF1_BASE}/laps?session_key={session_key}&driver_number={driver_number}"
    req_laps = Request(laps_url, headers = HEADERS)

    with urlopen(req_laps) as response:
        laps = json.loads(response.read().decode('utf-8'))

    #grap lap 3 (index 2) asumming the driver completed at least 3 laps
    start_time = laps[2]['date_start']
    end_time = laps[3]['date_start']

    #fetch location coordinates (X, Y, Z) bounded by timestamps

    loc_url = f"{OPENF1_BASE}/location?session_key={session_key}&driver_number={driver_number}&date>={start_time}&date<={end_time}"
    req_loc = Request(loc_url, headers=HEADERS)

    with urlopen(req_loc) as response:
        raw_data = json.loads(response.read().decode('utf-8'))
    
    return [
            {'x': pt.get('x'), 'y': pt.get('y'), 'z': pt.get('z', 0)}
            for pt in raw_data if  pt.get('x') is not None and pt.get('y') is not None
        ]

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