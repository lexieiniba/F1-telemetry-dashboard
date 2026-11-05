
def get_dashboard_html():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>F1 Telemetry HUD</title>
        <!-- Tailwind CSS CDN -->
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 font-sans min-h-screen flex flex-col items-center justify-center p-6">

        <div class="max-w-4xl w-full bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-8">
            <!-- Header -->
            <div class="flex justify-between items-center border-b border-slate-800 pb-4 mb-8">
                <div>
                    <h1 class="text-2xl font-black tracking-wider text-cyan-400">F1 TELEMETRY HUD</h1>
                    <p class="text-xs text-slate-400">2024 Bahrain Grand Prix | Driver #1 (Max Verstappen)</p>
                </div>
                <div id="status-badge" class="px-3 py-1 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 text-xs font-bold rounded-full animate-pulse">
                    LOADING DATA...
                </div>
            </div>

            <!-- Main Gauges Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <!-- Speed Card -->
                <div class="bg-slate-950/50 border border-slate-800/80 rounded-xl p-6 flex flex-col justify-between">
                    <span class="text-xs font-semibold tracking-widest text-slate-500">SPEED</span>
                    <div class="flex items-baseline space-x-2 my-4">
                        <span id="speed-val" class="text-6xl font-black tracking-tight text-cyan-300">0</span>
                        <span class="text-lg font-bold text-slate-400">KM/H</span>
                    </div>
                </div>

                <!-- Gear Card -->
                <div class="bg-slate-950/50 border border-slate-800/80 rounded-xl p-6 flex flex-col justify-between">
                    <span class="text-xs font-semibold tracking-widest text-slate-500">GEAR</span>
                    <div class="my-4">
                        <span id="gear-val" class="text-6xl font-black tracking-tight text-white">N</span>
                    </div>
                </div>
            </div>

            <!-- Telemetry Bars -->
            <div class="space-y-6 bg-slate-950/50 border border-slate-800/80 rounded-xl p-6">
                <!-- Throttle -->
                <div>
                    <div class="flex justify-between text-xs font-bold mb-2">
                        <span class="text-slate-400">THROTTLE</span>
                        <span id="throttle-text" class="text-emerald-400">0%</span>
                    </div>
                    <div class="w-full bg-slate-800 h-4 rounded-full overflow-hidden p-0.5">
                        <div id="throttle-bar" class="bg-emerald-500 h-full rounded-full transition-all duration-75" style="width: 0%"></div>
                    </div>
                </div>

                <!-- Brake -->
                <div>
                    <div class="flex justify-between text-xs font-bold mb-2">
                        <span class="text-slate-400">BRAKE</span>
                        <span id="brake-text" class="text-rose-400">OFF</span>
                    </div>
                    <div class="w-full bg-slate-800 h-4 rounded-full overflow-hidden p-0.5">
                        <div id="brake-bar" class="bg-rose-500 h-full rounded-full transition-all duration-75" style="width: 0%"></div>
                    </div>
                </div>
            </div>

            <!-- Playback Controls -->
            <div class="flex justify-center mt-8 space-x-4">
                <button onclick="togglePlayback()" id="play-btn" class="px-6 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-xl transition-all shadow-lg shadow-cyan-500/20">
                    Play Dashboard
                </button>
            </div>
        </div>

        <script>
            let telemetryData = [];
            let currentIndex = 0;
            let isPlaying = false;
            let timer = null;

            async function fetchTelemetry() {
                try {
                    let response = await fetch('/api/telemetry');
                    telemetryData = await response.json();
                    document.getElementById('status-badge').innerText = "LIVE READY";
                    document.getElementById('status-badge').className = "px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold rounded-full";
                } catch (err) {
                    console.error("Failed to load telemetry:", err);
                    document.getElementById('status-badge').innerText = "ERROR";
                }
            }

            function updateHUD() {
                if (telemetryData.length === 0) return;

                if (currentIndex >= telemetryData.length) {
                    currentIndex = 0; // Loop playback when finished
                }

                let row = telemetryData[currentIndex];
                
                // Read fields safely supporting both lowercase OpenF1 keys and capitalized variants
                let speed = Math.round(row.speed ?? row.Speed ?? 0);
                let throttle = Math.round(row.throttle ?? row.Throttle ?? 0);
                
                let rawBrake = row.brake ?? row.Brake ?? 0;
                let isBraking = rawBrake > 0;
                
                let gearVal = row.n_gear ?? row.gear ?? row.Gear ?? 0;
                let gear = gearVal === 0 ? 'N' : gearVal;

                // Apply updates to DOM elements
                document.getElementById('speed-val').innerText = speed;
                document.getElementById('gear-val').innerText = gear;
                
                document.getElementById('throttle-text').innerText = throttle + '%';
                document.getElementById('throttle-bar').style.width = throttle + '%';
                
                document.getElementById('brake-text').innerText = isBraking ? 'ACTIVE' : 'OFF';
                document.getElementById('brake-bar').style.width = (isBraking ? 100 : 0) + '%';

                currentIndex++;
            }

            function togglePlayback() {
                isPlaying = !isPlaying;
                let btn = document.getElementById('play-btn');
                if (isPlaying) {
                    btn.innerText = "Pause";
                    btn.className = "px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl transition-all shadow-lg shadow-amber-500/20";
                    timer = setInterval(updateHUD, 40); // ~25 FPS telemetry loop
                } else {
                    btn.innerText = "Resume";
                    btn.className = "px-6 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-xl transition-all shadow-lg shadow-cyan-500/20";
                    clearInterval(timer);
                }
            }

            fetchTelemetry();
        </script>
    </body>
    </html>
    """