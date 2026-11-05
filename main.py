from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from src.f1_data import load_session, load_driver_telemetry, get_available_sessions
from src.interfaces.race_selection import get_races_html

app = FastAPI(title="F1 Telemetry Dashboard")

TELEMETRY_CACHE = []

@app.on_event('startup')
def startup_event():
    #testing bridge with OpenF1 data
    global TELEMETRY_CACHE

    year = 2024
    gp_name = "Bahrain"
    session_type = "Race"
    driver_number = 1

    #test for session data
    print(f'finding session data for {year} {gp_name} {session_type}')
    try:
        session = load_session(grand_prix= gp_name, session_type=session_type, year=year)
        session_key = session['session_key']
    except Exception as e:
        print(f'Error loading session: {e}')
        return

    #test for driver telemetry
    print(f'Fetching telemetry for Driver {driver_number}')
    try:
        telemetry = load_driver_telemetry(session_key=session_key, driver_number=driver_number)
        if telemetry.empty:
            print("No telemetry")
            return

        TELEMETRY_CACHE = telemetry.to_dict(orient='records')
        print(f"Successfully loaded telemetry records")
        print(telemetry[['Time', 'Speed', 'Throttle', 'Brake', 'Gear']].head())

    except Exception as e:
        print(f'Error loading telemetry {e}')

@app.get("/api/telemetry")
def get_telemetry():
    if not TELEMETRY_CACHE:
        raise HTTPException(status_code=404, detail="Telemetry data not loaded")
    return TELEMETRY_CACHE


@app.get("/", response_class=HTMLResponse)
def list_races():
    sessions = get_available_sessions()
    return get_races_html(sessions)
    
