from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from src.f1_data import  get_available_sessions, get_session_drivers, get_driver_locations_window, get_session_duration, WINDOW_SECONDS, get_session_positions, get_race_start, get_driver_activity, OpenF1Unavailable, DataNotFound, load_driver_telemetry, load_session, get_circuit_geometry
from src.interfaces.race_selection import get_races_html
from src.interfaces.dashboard import get_dashboard_html
import traceback

app = FastAPI(title="F1 Telemetry Dashboard")
app.mount("/static", StaticFiles(directory="static"), name="static")

def to_http_error(e: Exception) -> HTTPException:
    # The details stay in the server log. The browser only gets a short, safe message.
    if isinstance(e, DataNotFound):
        print(f"Not found: {e}")
        return HTTPException(status_code=404, detail="This race isn't available.")
    if isinstance(e, OpenF1Unavailable):
        print(f"OpenF1 unavailable: {e}")
        return HTTPException(status_code=503, detail="Race data is temporarily unavailable. Please try again later.")
    traceback.print_exc()    # anything else is unexpected, so keep the full traceback
    return HTTPException(status_code=500, detail="Something went wrong on the server.")


@app.get("/", response_class=HTMLResponse)
def list_races():
    sessions = get_available_sessions()
    return get_races_html(sessions)

@app.get("/dashboard/{session_key}", response_class=HTMLResponse)
async def dashboard_view(session_key: int):
    try:
        return get_dashboard_html(session_key)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drivers/{session_key}")
def drivers_endpoint(session_key: int):
    try:
        return get_session_drivers(session_key)
    except Exception as e:
        raise to_http_error(e)

@app.get("/api/locations/{session_key}")
def locations_enpoint(
    session_key: int,
    offset: int = Query(0, ge=0, le=21600),               # seconds after the session start, up to 6 hours
    duration: int = Query(WINDOW_SECONDS, ge=1, le=300),  # length of the chunk, up to 5 minutes
):
    try:
        return get_driver_locations_window(session_key, offset, duration)
    except Exception as e:
        raise to_http_error(e)


@app.get("/api/session/{session_key}")
def session_endpoint(session_key: int):
    try:
        session_data = load_session(session_key=session_key)

        return {"duration": get_session_duration(session_key), 
                "window": WINDOW_SECONDS,
                "race_start":get_race_start(session_key, allow_api=False),
                "active_until": get_driver_activity(session_key),
                "session_start": session_data["date_start"],
                }
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


@app.get("/api/telemetry/{session_key}/{driver_number}")
def telemetry_endpoint(session_key: int, driver_number: int):
    try:
        telemetry = load_driver_telemetry(session_key, driver_number)
        return telemetry.to_dict(orient="records")
    except Exception as e:
        raise to_http_error(e)

@app.get("/api/circuit-geometry/{session_key}")
def circuit_geometry_endpoint(session_key: int):
    try:
        return get_circuit_geometry(session_key)
    except Exception as e:
        raise to_http_error(e)