const sessionKey = window.location.pathname.split('/').pop();
const slider = document.getElementById('timeSlider');
const timeLabel = document.getElementById('timeLabel');
const statusEl = document.getElementById('statusMsg');
const driverListEl = document.getElementById('driverList');


let drivers = [];
let locations = {};   

// The race is loaded in chunks ("windows") of windowSize seconds, only when needed.
let windowSize = 120;               // seconds per chunk
let totalTime = 120;                // length of the session in seconds
const loadedWindows = new Set();    // chunks already stored in `locations`
const failedWindows = new Set();    // chunks the server could not provide
const loadingWindows = new Set();   // chunks being fetched right now

// turn track coordinates into canvas pixels
function makeProjector(canvasEl) {
  const b = trackData.bounds;
  const padding = 50;
  const scaleX = (canvasEl.width - padding * 2) / ((b.max_x - b.min_x) || 1);
  const scaleY = (canvasEl.height - padding * 2) / ((b.max_y - b.min_y) || 1);
  const scale = Math.min(scaleX, scaleY);
  return function (x, y) {
    return {
      x: padding + (x - b.min_x) * scale,
      y: canvasEl.height - (padding + (y - b.min_y) * scale),
    };
  };
}
const project = makeProjector(canvas);

// Find where a driver is at time t.
// `points` is a list of {t, x, y} sorted by time. If t falls between two samples,
// blend between them (linear interpolation) so movement looks smooth.
// The list can hold a whole race, so use binary search to find the two samples fast.
function positionAt(points, t) {
  if (!points || points.length === 0) return null;
  if (t <= points[0].t) return points[0];
  const last = points[points.length - 1];
  if (t >= last.t) return last;

  let lo = 0;
  let hi = points.length - 1;
  while (hi - lo > 1) {                      // keep the range [lo, hi] around t
    const mid = (lo + hi) >> 1;
    if (points[mid].t <= t) lo = mid;
    else hi = mid;
  }
  const a = points[lo];
  const b = points[hi];
  const f = (t - a.t) / ((b.t - a.t) || 1); // 0 = at a, 1 = at b
  return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f };
}

// 4500 -> "1:15:00", 75 -> "1:15"
function formatTime(t) {
  const s = Math.floor(t);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
}

// Drawing
function drawDots(t) {
  renderMap();   // redraw the track first
  for (const d of drivers) {
    const pos = positionAt(locations[String(d.driver_number)], t);
    if (!pos) continue;
    const p = project(pos.x, pos.y);

    ctx.beginPath();
    ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
    ctx.fillStyle = '#' + d.team_colour;
    ctx.fill();

    ctx.fillStyle = '#e2e8f0';
    ctx.font = '10px monospace';
    ctx.fillText(d.acronym, p.x + 9, p.y + 3);
  }
}

function renderDriverList() {
  driverListEl.textContent = '';
  const sorted = [...drivers].sort((a, b) => a.team.localeCompare(b.team));
  for (const d of sorted) {
    const li = document.createElement('li');
    li.className = 'flex items-center gap-2';

    const swatch = document.createElement('span');
    swatch.className = 'inline-block w-2 h-2 rounded-full';
    swatch.style.background = '#' + d.team_colour;

    const code = document.createElement('span');
    code.className = 'font-bold text-slate-200';
    code.textContent = d.acronym;

    const team = document.createElement('span');
    team.className = 'text-slate-500';
    team.textContent = d.team;

    li.append(swatch, code, team);
    driverListEl.appendChild(li);
  }
}

// Fetch one chunk of the race from server and add it to `locations`.
async function loadWindow(i) {
  if (i < 0 || i * windowSize >= totalTime) return;
  if (loadedWindows.has(i) || failedWindows.has(i) || loadingWindows.has(i)) return;

  loadingWindows.add(i);
  try {
    const offset = i * windowSize;
    const res = await fetch(`/api/locations/${sessionKey}?offset=${offset}&duration=${windowSize}`);
    if (!res.ok) throw new Error('chunk unavailable');
    const data = await res.json();
    if (Object.keys(data).length === 0) throw new Error('chunk is empty');

    for (const [number, pts] of Object.entries(data)) {
      if (!locations[number]) locations[number] = [];
      for (const p of pts) {
        locations[number].push({ t: p.t + offset, x: p.x, y: p.y });
      }
      locations[number].sort((a, b) => a.t - b.t);
    }
    loadedWindows.add(i);
  } catch (err) {
    failedWindows.add(i);
  } finally {
    loadingWindows.delete(i);
  }
}

// Show the race at time t: load the chunk (and the next one), then draw.
async function showTime(t) {
  const i = Math.floor(t / windowSize);
  timeLabel.textContent = formatTime(t);

  if (loadedWindows.has(i)) {
    drawDots(t);
    statusEl.textContent = '';
  } else {
    renderMap();    // no data for this part yet, so show just the track
    statusEl.textContent = failedWindows.has(i)
      ? 'This part of the race is not available.'
      : 'Loading...';
  }

  await Promise.all([loadWindow(i), loadWindow(i + 1)]);   // the next chunk loads ahead of time


  const now = parseFloat(slider.value);
  const j = Math.floor(now / windowSize);
  timeLabel.textContent = formatTime(now);
  if (loadedWindows.has(j)) {
    drawDots(now);
    statusEl.textContent = '';
  } else if (failedWindows.has(j)) {
    renderMap();
    statusEl.textContent = 'This part of the race is not available.';
  }
}

async function loadSession() {
  const [driversRes, infoRes] = await Promise.all([
    fetch(`/api/drivers/${sessionKey}`),
    fetch(`/api/session/${sessionKey}`),
  ]);
  if (!driversRes.ok || !infoRes.ok) {
    throw new Error('Could not load session data');
  }
  drivers = await driversRes.json();
  const info = await infoRes.json();
  windowSize = info.window;
  totalTime = info.duration;
}

slider.addEventListener('input', () => showTime(parseFloat(slider.value)));

async function init() {
  if (!trackData.has_real_track) return;
  try {
    await loadSession();
  } catch (err) {
    console.error(err);
    driverListEl.textContent =
      'No driver data available. OpenF1 may be restricted during a live session, and this race is not saved yet.';
    return;
  }
  slider.max = totalTime;
  slider.step = 0.5;
  renderDriverList();
  showTime(0);
}
init();