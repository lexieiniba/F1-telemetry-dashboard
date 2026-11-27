from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from src.f1_data import  get_available_sessions, get_session_drivers, get_driver_locations_window, get_session_duration, WINDOW_SECONDS, get_session_positions, get_race_start, get_driver_activity
from src.interfaces.race_selection import get_races_html
from src.interfaces.dashboard import get_dashboard_html
from src.insights.track_position_window import get_track_visualization_payload
import traceback

app = FastAPI(title="F1 Telemetry Dashboard")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def list_races():
    sessions = get_available_sessions()
    return get_races_html(sessions)

@app.get("/dashboard/{session_key}", response_class=HTMLResponse)
async def dashboard_view(session_key: int, request: Request):
    try:
        track_data = get_track_visualization_payload(session_key, driver_number = None)
        return get_dashboard_html(session_key, track_data)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drivers/{session_key}")
def drivers_endpoint(session_key: int):
    return get_session_drivers(session_key)

@app.get("/api/locations/{session_key}")
def locations_enpoint(session_key: int, offset: int = 0, duration: int = 120):
    try:
        return get_driver_locations_window(session_key, offset, duration)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_key}")
def session_endpoint(session_key: int):
    try:
        return {"duration": get_session_duration(session_key), "window": WINDOW_SECONDS, "race_start":get_race_start(session_key, allow_api=False),"active_until": get_driver_activity(session_key),}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        
        
@app.get("/api/positions/{session_key}")
def positions_endpoint(session_key: int):
    try:
        return get_session_positions(session_key)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))