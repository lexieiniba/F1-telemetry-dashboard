import math
from src.f1_data import map_circuit_coordinates, load_session
from src.lib.cache import load_json, save_json

class TrackGeometryProcessor:
    #Process location coordinates into vectors

    def __init__(self, session_key: int, driver_number: int = 1):
        self.session_key = session_key
        self.driver_number = driver_number
        self.center_xs: list[float] = []
        self.center_ys: list[float] = []
        self.cum_fracs: list[float] = []
        self.has_real_track: bool = False
        self._load_and_process()

    def _load_and_process(self, rotation_deg: float = 0.0):
        from src.f1_data import map_circuit_coordinates
        raw_locations = map_circuit_coordinates(self.session_key, self.driver_number)
        if not raw_locations:
            return

        # Extract valid x, y points
        x_center = [pt['x'] for pt in raw_locations if pt.get('x') is not None and pt.get('y') is not None]
        y_center = [pt['y'] for pt in raw_locations if pt.get('x') is not None and pt.get('y') is not None]

        if len(x_center) < 3:
            return

        # Center and align bounding box
        cx = (min(x_center) + max(x_center)) / 2
        cy = (min(y_center) + max(y_center)) / 2
        rad = math.radians(rotation_deg)
        cos_r, sin_r = math.cos(rad), math.sin(rad)

        rxs, rys = [], []
        for x, y in zip(x_center, y_center):
            dx, dy = x - cx, y - cy
            rxs.append(cx + dx * cos_r - dy * sin_r)
            rys.append(cy + dx * sin_r + dy * cos_r)

        self.center_xs = rxs
        self.center_ys = rys

        # Compute cumulative fractional distances along the track [0.0 ... 1.0]
        cum = [0.0]
        for i in range(1, len(self.center_xs)):
            seg = math.hypot(
                self.center_xs[i] - self.center_xs[i - 1],
                self.center_ys[i] - self.center_ys[i - 1],
            )
            cum.append(cum[-1] + seg)

        total = cum[-1] if cum[-1] > 0 else 1.0
        self.cum_fracs = [d / total for d in cum]
        self.has_real_track = True

    def get_payload(self):
        return {
            "has_real_track": self.has_real_track,
            "center_xs": self.center_xs,
            "center_ys": self.center_ys,
            "cum_fracs": self.cum_fracs,
            "bounds": {
                "min_x": min(self.center_xs) if self.center_xs else 0,
                "max_x": max(self.center_xs) if self.center_xs else 1,
                "min_y": min(self.center_ys) if self.center_ys else 0,
                "max_y": max(self.center_ys) if self.center_ys else 1,
            }
        }

def get_track_visualization_payload(session_key: int, driver_number: int | None = None):
    session = load_session(session_key=session_key)
    cache_name = f"track{session['circuit_key']}_{session['year']}"
    cached = load_json(cache_name)
    if cached:
        return cached

    payload = TrackGeometryProcessor(session_key, driver_number).get_payload()
    if payload["has_real_track"]:
        save_json(cache_name, payload)
    return payload