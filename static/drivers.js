const sessionKey = window.location.pathname.split('/').pop();
const slider = document.getElementById('timeSlider');
const timeLabel = document.getElementById('timeLabel');
const statusEl = document.getElementById('statusMsg');
const driverListEl = document.getElementById('driverList');
const telemetryStatsEl = document.getElementById('telemetryStats');

let sessionStartMs = null;
let telemetryByDriver = {};
let telemetryLoading = new Set();
let telemetryErrors = {};
let lastTelemetryRenderKey = null;


let drivers = [];
let locations = {};   

// The race is loaded in chunks ("windows") of windowSize seconds, only when needed.
let windowSize = 120;               // seconds per chunk
let totalTime = 120;                // length of the session in seconds
let raceStart = 0;
let activateUntil = {};
let selectedDriverNumber = null;
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
  return sign + (h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`);
}

// Drawing

function drawDots(t) {
  renderMap();   // redraw the track first

  // Draw unselected drivers first, selected driver last
  const orderedDrivers = [
    ...drivers.filter(
      d => String(d.driver_number) !== String(selectedDriverNumber)
    ),
    ...drivers.filter(
      d => String(d.driver_number) === String(selectedDriverNumber)
    )
  ];

  for (const d of orderedDrivers) {
    const until = activateUntil[String(d.driver_number)];

    if (until !== undefined && t > until + 5) continue;

    const pos = positionAt(locations[String(d.driver_number)], t);
    if (!pos) continue;

    const p = project(pos.x, pos.y);

    const isSelected =
      String(d.driver_number) === String(selectedDriverNumber);

    // Selected driver's glow and outer ring
    if (isSelected) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
      ctx.shadowColor = '#FFFFFF';
      ctx.shadowBlur = 12;
      ctx.fillStyle = '#' + d.team_colour;
      ctx.fill();
      ctx.shadowBlur = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, 11, 0, Math.PI * 2);
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Draw the actual driver dot
    ctx.beginPath();
    ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
    ctx.fillStyle = '#' + d.team_colour;
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 1;
    ctx.fill();
    ctx.stroke();
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
    renderTelemetry(t);
    
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
  activateUntil = info.active_until || {};
  sessionStartMs = Date.parse(info.session_start);
}

// Fetch and prepare telemetry for one driver.
async function loadDriverTelemetry(driverNumber) {
  const key = String(driverNumber);

  // Already loaded: reuse the cached data.
  if (Object.hasOwn(telemetryByDriver, key)) {
    renderTelemetry(playTime);
    return;
  }

  // Avoid duplicate requests.
  if (telemetryLoading.has(key)) return;

  telemetryLoading.add(key);
  renderTelemetry(playTime);

  try {
    const res = await fetch(
      `/api/telemetry/${sessionKey}/${driverNumber}`
    );

    if (!res.ok) {
      throw new Error('Could not load driver telemetry.');
    }

    const records = await res.json();

    const samples = records
      .map(record => {
        const timestamp = Date.parse(record.Time);

        return {
          ...record,
          t: (timestamp - sessionStartMs) / 1000
        };
      })
      .filter(sample =>
        Number.isFinite(sample.t) &&
        sample.t >= 0 &&
        sample.t <= totalTime
      )
      .sort((a, b) => a.t - b.t);

    telemetryByDriver[key] = samples;

  } catch (err) {
    console.error('Telemetry loading failed:', err);
    telemetryErrors[key] = 'Could not load telemetry.';
  } finally {
    telemetryLoading.delete(key);
    renderTelemetry(playTime);
  }
}


// Find the latest telemetry sample at or before playback time.
function telemetryAt(samples, t) {
  if (!samples || samples.length === 0) return null;

  let lo = 0;
  let hi = samples.length;

  while (lo < hi) {
    const mid = (lo + hi) >> 1;

    if (samples[mid].t <= t) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }

  const sample = samples[lo - 1];

  if (!sample || t - sample.t > 2) {
    return null;
  }

  return sample;
}


// Render the selected driver's telemetry.
function renderTelemetry(t) {
  if (!telemetryStatsEl) return;

  if (selectedDriverNumber === null) {
    telemetryStatsEl.textContent = 'Select a driver to view their telemetry.';
    lastTelemetryRenderKey = null;
    return;
  }

  const key = String(selectedDriverNumber);
  const driver = drivers.find(
    d => String(d.driver_number) === key
  );

  if (telemetryLoading.has(key)) {
    telemetryStatsEl.textContent = 'Loading telemetry...';
    lastTelemetryRenderKey = null;
    return;
  }

  if (telemetryErrors[key]) {
    telemetryStatsEl.textContent = telemetryErrors[key];
    lastTelemetryRenderKey = null;
    return;
  }

  if (!Object.hasOwn(telemetryByDriver, key)) {
    telemetryStatsEl.textContent = 'Loading telemetry...';
    lastTelemetryRenderKey = null;
    return;
  }

  const samples = telemetryByDriver[key];
  const sample = telemetryAt(samples, t);

  if (!sample) {
    telemetryStatsEl.textContent =
      'No telemetry available at this playback time.';
    lastTelemetryRenderKey = null;
    return;
  }

  // Avoid rebuilding the panel every animation frame
  // when the telemetry sample hasn't changed.
  const renderKey = `${key}:${sample.t}`;

  if (renderKey === lastTelemetryRenderKey) return;

  lastTelemetryRenderKey = renderKey;

  telemetryStatsEl.replaceChildren();

  const heading = document.createElement('div');
  heading.className = 'text-sm font-bold text-white mb-3';
  heading.textContent =
    `${driver.full_name || driver.acronym} · ${driver.team}`;

  const grid = document.createElement('div');
  grid.className = 'grid grid-cols-2 sm:grid-cols-3 gap-3';

  const metrics = [
    {
      label: 'Speed',
      value: `${Math.round(Number(sample.Speed))} km/h`
    },
    {
      label: 'Throttle',
      value: `${Math.round(Number(sample.Throttle))}%`
    },
    {
      label: 'Brake',
      value: Number(sample.Brake) > 0 ? 'ON' : 'OFF'
    },
    {
      label: 'Gear',
      value: sample.Gear ?? '—'
    },
    {
      label: 'RPM',
      value: sample.RPM == null
        ? '—'
        : Math.round(Number(sample.RPM)).toLocaleString()
    },
    {
      label: 'DRS',
      value: sample.drs ?? '—'
    }
  ];

  for (const metric of metrics) {
    const card = document.createElement('div');
    card.className = 'bg-slate-800 rounded-lg p-3';

    const label = document.createElement('div');
    label.className =
      'text-xs text-slate-400 uppercase tracking-wider';
    label.textContent = metric.label;

    const value = document.createElement('div');
    value.className = 'text-xl font-bold text-white mt-1';
    value.textContent = metric.value;

    card.append(label, value);
    grid.appendChild(card);
  }

  telemetryStatsEl.append(heading, grid);
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

    const isSelected =
      String(d.driver_number) === String(selectedDriverNumber);

    const li = document.createElement('li');
    li.className =
      'rounded-lg overflow-hidden cursor-pointer transition-all duration-300';
    li.dataset.driver = d.driver_number;

    if (isSelected) {
      li.classList.add('bg-slate-800', 'border', 'border-slate-500');
    } else {
      li.classList.add('hover:bg-slate-800/70');
    }

    li.addEventListener('click', () => {
      selectedDriverNumber = d.driver_number;
      renderLeaderboard(rows);
      drawDots(playTime);

      loadDriverTelemetry(selectedDriverNumber);
      renderTelemetry(playTime);
    });

    // Leaderboard row
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
    team.className = 'text-slate-500 text-xs truncate flex-1';
    team.textContent = d.team;

    const header = document.createElement('div');
    header.className = 'flex items-center gap-2 px-2 py-3';

    header.append(pos, swatch, code, team);
    li.appendChild(header);

    // Expanded driver profile
    if (isSelected) {
      const profile = document.createElement('div');
      profile.className = 'relative overflow-hidden';

      // Full team-colored gradient
      profile.style.background =
        `linear-gradient(120deg, #${d.team_colour} 0%, #0f172a 100%)`;

      const content = document.createElement('div');
      content.className = 'flex items-center gap-3 px-3 py-2';

      // Driver information
      const info = document.createElement('div');
      info.className = 'min-w-0 flex-1';

      const number = document.createElement('div');
      number.className = 'text-xs text-slate-300 font-semibold';
      number.textContent = `CAR ${d.driver_number}`;

      const name = document.createElement('div');
      name.className = 'text-sm font-extrabold text-white leading-tight mt-1 break-words';
      name.textContent = d.full_name || d.acronym;

      const teamName = document.createElement('div');
      teamName.className = 'text-xs text-slate-300 mt-1';
      teamName.textContent = d.team;

      info.append(number, name, teamName);
      content.appendChild(info);

      // Actual driver photo — no box or container
      if (d.headshot_url) {
        const img = document.createElement('img');
        img.src = d.headshot_url;
        img.alt = d.full_name || d.acronym;
        img.className =
          'w-[72px] h-[72px] object-contain flex-shrink-0';
        img.loading = 'lazy';

        content.appendChild(img);
      profile.appendChild(content);
      li.appendChild(profile);
      }

      // Driver statistics
      const stats = document.createElement('div');
      stats.className = 'grid grid-cols-2 gap-2 px-2 pb-2';

      const positionStat = document.createElement('div');
      positionStat.className = 'bg-black/20 rounded-lg p-2';

      const positionLabel = document.createElement('div');
      positionLabel.className =
        'text-[9px] text-slate-400 uppercase tracking-wider';
      positionLabel.textContent = 'Position';

      const positionValue = document.createElement('div');
      positionValue.className = 'text-sm font-bold text-white';
      positionValue.textContent =
        row.position === 99 ? '-' : `P${row.position}`;

      const numberStat = document.createElement('div');
      numberStat.className = 'bg-black/20 rounded-lg p-2';

      const numberLabel = document.createElement('div');
      numberLabel.className =
        'text-[9px] text-slate-400 uppercase tracking-wider';
      numberLabel.textContent = 'Driver Number';

      const numberValue = document.createElement('div');
      numberValue.className = 'text-sm font-bold text-white';
      numberValue.textContent = `#${d.driver_number}`;

      positionStat.append(positionLabel, positionValue);
      numberStat.append(numberLabel, numberValue);
      stats.append(positionStat, numberStat);

      profile.append(content, stats);
      li.appendChild(profile);
    }

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