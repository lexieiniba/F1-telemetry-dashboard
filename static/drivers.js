const sessionKey = window.location.pathname.split('/').pop();  
const slider = document.getElementById('timeSlider');
const timeLabel = document.getElementById('timeLabel');
const driverListEl = document.getElementById('driverList');


let drivers = [];    
let locations = {};   

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

// Find where driver is at time t
// list of {t, x, y} sorted by time. If t falls between two samples,
// blend between them (linear interpolation) so movement looks smooth.
function positionAt(points, t) {
  if (!points || points.length === 0) return null;
  if (t <= points[0].t) return points[0];
  const last = points[points.length - 1];
  if (t >= last.t) return last;

  let i = 0;
  while (points[i + 1].t < t) i++;          // find the sample just before t
  const a = points[i];
  const b = points[i + 1];
  const f = (t - a.t) / ((b.t - a.t) || 1); // 0 = at a, 1 = at b
  return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f };
}

function maxTime() {
  let m = 0;
  for (const pts of Object.values(locations)) {
    if (pts.length > 0) m = Math.max(m, pts[pts.length - 1].t);
  }
  return m;
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
  timeLabel.textContent = t.toFixed(1) + ' s';
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

async function loadData() {
  const [driversRes, locationsRes] = await Promise.all([
    fetch(`/api/drivers/${sessionKey}`),
    fetch(`/api/locations/${sessionKey}`),
  ]);
  if (!driversRes.ok || !locationsRes.ok) {
    throw new Error('Could not load driver data');
  }
  drivers = await driversRes.json();
  locations = await locationsRes.json();
}

slider.addEventListener('input', () => drawDots(parseFloat(slider.value)));

async function init() {
  if (!trackData.has_real_track) return;
  try {
    await loadData();
  } catch (err) {
    console.error(err);
    driverListEl.textContent =
      'No driver data available. OpenF1 may be restricted during a live session, and this race is not saved yet.';
    return;
  }
  slider.max = maxTime();
  renderDriverList();
  drawDots(0);
}
init();