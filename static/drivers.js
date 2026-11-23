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
let raceStart = 0;
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
  const sign = t < 0 ? '-' : '';
  const s = Math.floor(Math.abs(t));
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
  updateLeaderboard(t);
  timeLabel.textContent = formatTime(t - raceStart);

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
  timeLabel.textContent = formatTime(now - raceStart);
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
  raceStart = info.race_start || 0;
}

slider.addEventListener('input', () => showTime(parseFloat(slider.value)));

// Leaderboard
let positionsByDriver = {};   
let lastOrder = '';          

async function loadPositions() {
  try {
    const res = await fetch(`/api/positions/${sessionKey}`);
    if (!res.ok) return;                                   // no position data: keep the plain driver list
    const changes = await res.json();                      // [[t, driver_number, position], ...]
    for (const [t, number, position] of changes) {
      const key = String(number);
      if (!positionsByDriver[key]) positionsByDriver[key] = [];
      positionsByDriver[key].push({ t: t, p: position });
    }
    for (const list of Object.values(positionsByDriver)) {
      list.sort((a, b) => a.t - b.t);
    }
  } catch (err) {
    console.error(err);
  }
}

// A driver's position at time t is the last update at or before t (binary search).
function positionOf(list, t) {
  if (list[0].t > t) return list[0].p;        // before the first update: use the first known position
  let lo = 0;
  let hi = list.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (list[mid].t <= t) lo = mid;
    else hi = mid - 1;
  }
  return list[lo].p;
}

function renderLeaderboard(rows) {
  driverListEl.textContent = '';
  for (const row of rows) {
    const d = row.driver;
    const li = document.createElement('li');
    li.className = 'flex items-center gap-2';
    li.dataset.driver = d.driver_number;

    const pos = document.createElement('span');
    pos.className = 'w-5 text-right text-slate-500';
    pos.textContent = row.position === 99 ? '-' : row.position;

    const swatch = document.createElement('span');
    swatch.className = 'inline-block w-2 h-2 rounded-full';
    swatch.style.background = '#' + d.team_colour;

    const code = document.createElement('span');
    code.className = 'font-bold text-slate-200';
    code.textContent = d.acronym;

    const team = document.createElement('span');
    team.className = 'text-slate-500';
    team.textContent = d.team;

    li.append(pos, swatch, code, team);
    driverListEl.appendChild(li);
  }
}

function updateLeaderboard(t) {
  if (Object.keys(positionsByDriver).length === 0) return;
  const rows = drivers.map((d) => {
    const list = positionsByDriver[String(d.driver_number)];
    return { driver: d, position: list ? positionOf(list, t) : 99 };
  });
  rows.sort((a, b) => a.position - b.position || a.driver.driver_number - b.driver.driver_number);

  const order = rows.map((r) => r.driver.driver_number + ':' + r.position).join(',');
  if (order === lastOrder) return;                         // nothing changed, skip redrawing
  lastOrder = order;
  renderLeaderboard(rows);
}  

function startTime() {
    return Math.max(0, raceStart - 20);
}

// Play/Pause
const playBtn = document.getElementById('playBtn');
const speedSelect = document.getElementById('speedSelect');
let playing = false;
let playTime = 0;        // the current time in seconds, kept separately so slow speeds still move smoothly
let lastFrame = null;    // timestamp of the previous animation frame

function frame(now) {
  if (!playing) return;
  if (lastFrame !== null) {
    const dt = Math.min((now - lastFrame) / 1000, 0.1);   // seconds since the last frame (capped)
    playTime += dt * parseFloat(speedSelect.value);
  }
  lastFrame = now;

  if (playTime >= totalTime) {                            // reached the end of the race
    playTime = totalTime;
    setPlaying(false);
  }
  slider.value = playTime;
  showTime(playTime);
  if (playing) requestAnimationFrame(frame);
}

function setPlaying(on) {
  playing = on;
  playBtn.textContent = on ? 'Pause' : 'Play';
  if (on) {
    if (playTime >= totalTime) playTime = startTime();    // press Play again to replay from the start
    lastFrame = null;
    requestAnimationFrame(frame);
  }
}

playBtn.addEventListener('click', () => setPlaying(!playing));
// If you drag the slider yourself, continue from where you dropped it.
slider.addEventListener('input', () => { playTime = parseFloat(slider.value); });

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
  slider.step = 'any';
  renderDriverList();
  await loadPositions();
  playTime = startTime();
  slider.value = playTime;
  showTime(playTime);
}
init();