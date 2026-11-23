import json

def get_dashboard_html(session_key: int, track_data: dict) -> str:
    track_json = json.dumps(track_data)

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>F1 Telemetry Dashboard — Session {session_key}</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class= "bg-[#0C0C0A] text-slate-100 font-sans min-h-screen p-6">
        <div class="max-w-6xl mx-auto">
            <!-- Header -->
            <header class="mb-6 pb-4 border-b border-slate-900 flex justify-between items-baseline">
                <div>
                    <h1 class="text-sm font-bold font-mono tracking-wider text-slate-200 uppercase">Circuit Geometry & Telemetry Visualizer</h1>
                    <p class="text-xs font-mono text-slate-600 mt-1">Session Key: {session_key}</p>
                </div>
                <a href="/" class="text-xs font-mono text-cyan-400 hover:underline">&larr; Back to Sessions</a>
            </header>

            <!-- Main Workspace Layout -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Track Canvas Viewport -->
                <main class="lg:col-span-2 border border-slate-900 rounded bg-slate-900/20 p-4 flex flex-col items-center justify-center">
                    <div class="relative">
                        <canvas id="trackCanvas" width="700" height="600" class="bg-slate-950 rounded border border-slate-900 max-w-full h-auto"></canvas>
                    </div>
                    <div class="w-full mt-4 flex items-center gap-3 text-xs font-mono text-slate-400">
                        <button id="playBtn" class="w-16 px-2 py-1 rounded border border-slate-700 bg-slate-900 text-slate-200">Play</button>
                        <span id="timeLabel" class="w-14">0:00</span>
                        <input id="timeSlider" type="range" min="0" max="120" step="0.5" value="0" class="flex-1">
                        <select id="speedSelect" class="bg-slate-900 border border-slate-700 rounded px-1 py-1 text-slate-200">
                            <option value="0.5">0.5x</option>
                            <option value="1">1x</option>
                            <option value="5" selected>5x</option>
                            <option value="20">20x</option>
                            <option value="60">60x</option>
                        </select>
                    </div>
                    <p id="statusMsg" class="w-full mt-2 text-xs font-mono text-slate-600 h-4"></p>
                </main>

                <!-- Telemetry Control / Info Panel -->
                <aside class="border border-slate-900 rounded bg-slate-900/20 p-4 flex flex-col justify-between font-mono">
                    <div class="mb-4">
                        <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 border-b border-slate-900 pb-2">Drivers</h2>
                        <ul id="driverList" class="space y-1 test-xs"></ul?
                    <div>
                        <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-900 pb-2">Session Telemetry</h2>
                        <div id="telemetryStats" class="space-y-3 text-xs text-slate-300">
                            <p class="text-slate-600">Waiting for telemetry stream...</p>
                        </div>
                    </div>
                    <div class="mt-6 pt-4 border-t border-slate-900 text-xs text-slate-600">
                        OpenF1 Live Stream &bull; Canvas Engine Active
                    </div>
                </aside>
            </div>
        </div>

        <script>
            // Injected track geometry payload from Python backend
            const trackData = {track_json};

            const canvas = document.getElementById('trackCanvas');
            const ctx = canvas.getContext('2d');

            function renderMap() {{
                if (!trackData.has_real_track) {{
                    ctx.fillStyle = '#64748b';
                    ctx.font = '14px monospace';
                    ctx.fillText('No track geometry available for this session.', 40, 50);
                    return;
                }}

                const bounds = trackData.bounds;
                const minX = bounds.min_x, maxX = bounds.max_x;
                const minY = bounds.min_y, maxY = bounds.max_y;

                const trackWidth = maxX - minX;
                const trackHeight = maxY - minY;

                const padding = 50;
                const scaleX = (canvas.width - padding * 2) / (trackWidth || 1);
                const scaleY = (canvas.height - padding * 2) / (trackHeight || 1);
                const scale = Math.min(scaleX, scaleY);

                function toScreen(x, y) {{
                    return {{
                        x: padding + (x - minX) * scale,
                        y: canvas.height - (padding + (y - minY) * scale)
                    }};
                }}

                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // Helper to draw polylines
                function drawPolyline(xs, ys, color, lineWidth) {{
                    if (!xs || xs.length === 0) return;
                    ctx.beginPath();
                    for (let i = 0; i < xs.length; i++) {{
                        const pt = toScreen(xs[i], ys[i]);
                        if (i === 0) ctx.moveTo(pt.x, pt.y);
                        else ctx.lineTo(pt.x, pt.y);
                    }}
                    ctx.closePath();
                    ctx.strokeStyle = color;
                    ctx.lineWidth = lineWidth;
                    ctx.stroke();
                }}

                // Draw outer boundary wall
                drawPolyline(trackData.outer_xs, trackData.outer_ys, '#334155', 2);

                // Draw inner boundary wall
                drawPolyline(trackData.inner_xs, trackData.inner_ys, '#334155', 2);

                // Draw center line
                drawPolyline(trackData.center_xs, trackData.center_ys, '#0891b2', 1);
            }}

            // Initial render call
            renderMap();
        </script>
        <script src="/static/drivers.js"></script>
    </body>
    </html>
    """