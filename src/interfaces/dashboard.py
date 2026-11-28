def get_dashboard_html(session_key: int) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <title>F1 Telemetry Dashboard — Session {session_key}</title>

        <script src="https://cdn.tailwindcss.com"></script>

        <link
            rel="stylesheet"
            href="/static/css/dashboard.css"
        >
    </head>

    <body class="bg-[#0C0C0A] text-slate-100 font-sans min-h-screen p-4 md:p-6">

        <div class="max-w-7xl mx-auto">

            <!-- Header -->
            <header class="mb-5 pb-4 border-b border-slate-900 flex justify-between items-baseline">

                <div>
                    <h1 class="text-sm font-bold font-mono tracking-wider text-slate-200 uppercase">
                        Circuit Geometry & Telemetry Visualizer
                    </h1>

                    <p class="text-xs font-mono text-slate-600 mt-1">
                        Session Key: {session_key}
                    </p>
                </div>

                <a
                    href="/"
                    class="text-xs font-mono text-cyan-400 hover:underline"
                >
                    &larr; Back to Sessions
                </a>

            </header>


            <!-- Main Workspace -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">


                <!-- LEFT: Driver Leaderboard -->
                <aside class="lg:col-span-1 min-w-0 border border-slate-800 rounded-lg bg-slate-900/30 p-3">

                    <div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">

                        <h2 class="text-xs font-bold text-slate-300 uppercase tracking-wider">
                            Driver Standings
                        </h2>

                        <span class="text-[10px] text-slate-500 uppercase tracking-wider">
                            Session
                        </span>

                    </div>

                    <ul
                        id="driverList"
                        class="space-y-1 text-xs"
                    ></ul>

                </aside>


                <!-- RIGHT: Circuit and Driver Information -->
                <div class="lg:col-span-2 min-w-0 flex flex-col gap-4">


                    <!-- Circuit Panel -->
                    <main class="min-w-0 border border-slate-800 rounded-lg bg-slate-900/30 p-3 md:p-4">

                        <div class="flex items-center justify-between mb-3">

                            <h2 class="text-xs font-bold text-slate-300 uppercase tracking-wider">
                                Circuit Map
                            </h2>

                            <span class="text-[10px] font-mono text-slate-500">
                                SESSION POSITION DATA
                            </span>

                        </div>


                        <!-- Circuit Canvas -->
                        <div class="relative w-full flex justify-center">

                            <canvas
                                id="trackCanvas"
                                width="700"
                                height="600"
                                class="bg-slate-950 rounded border border-slate-800 max-w-full h-auto"
                            ></canvas>

                        </div>


                        <!-- Playback Controls -->
                        <div class="w-full mt-4 flex items-center gap-3 text-xs font-mono text-slate-400">

                            <button
                                id="playBtn"
                                class="w-16 px-2 py-1 rounded border border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800"
                            >
                                Play
                            </button>

                            <span
                                id="timeLabel"
                                class="w-14"
                            >
                                0:00
                            </span>

                            <input
                                id="timeSlider"
                                type="range"
                                min="0"
                                max="120"
                                step="0.5"
                                value="0"
                                class="flex-1 min-w-0"
                            >

                            <select
                                id="speedSelect"
                                class="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                            >
                                <option value="0.5">0.5x</option>
                                <option value="1">1x</option>
                                <option value="5" selected>5x</option>
                                <option value="20">20x</option>
                                <option value="60">60x</option>
                            </select>

                        </div>


                        <!-- Playback Status -->
                        <p
                            id="statusMsg"
                            class="w-full mt-2 text-xs font-mono text-slate-600 h-4"
                        ></p>

                    </main>


                    <!-- Selected Driver Telemetry Panel -->
                    <section class="min-w-0 border border-slate-800 rounded-lg bg-slate-900/30 p-4">

                        <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-800">

                            <h2 class="text-xs font-bold text-slate-300 uppercase tracking-wider">
                                Driver Telemetry
                            </h2>

                            <span class="text-[10px] text-slate-500 uppercase tracking-wider">
                                Selected Driver
                            </span>

                        </div>


                        <div
                            id="telemetryStats"
                            class="space-y-3 text-xs text-slate-300"
                        >

                            <p class="text-slate-600">
                                Select a driver to view their session telemetry.
                            </p>

                        </div>

                    </section>

                </div>

            </div>

        </div>

        <!-- Canvas initialization -->
        <script>
            const canvas = document.getElementById('trackCanvas');
            const ctx = canvas.getContext('2d');
        </script>

        <!-- Driver and Telemetry Logic -->
        <script src="/static/drivers.js"></script>

    </body>
    </html>
    """
