
def get_races_html(sessions: list) -> str:
    """Generates a minimal, low-distraction HTML page displaying all race sessions."""
    
    rows_html = ""
    
    for s in sessions:
        country = s.get('country_name', 'Grand Prix')
        circuit = s.get('circuit_short_name', s.get('location', 'Circuit'))
        session_name = s.get('session_name', 'Race')
        session_key = s.get('session_key')
        
        date_str = s.get('date_start', '')
        date_formatted = date_str.split('T')[0] if 'T' in date_str else date_str
        
        rows_html += f"""
        <tr class="border-b border-slate-900 hover:bg-slate-900/40 transition-colors">
            <td class="py-3 px-4 text-xs font-mono text-slate-400">{date_formatted}</td>
            <td class="py-3 px-4 text-sm font-medium text-slate-200">{country} — <span class="text-slate-400 font-normal">{circuit}</span></td>
            <td class="py-3 px-4 text-xs font-mono text-slate-500 uppercase">{session_name}</td>
            <td class="py-3 px-4 text-right">
                <a href="/dashboard/{session_key}" 
                   class="inline-block px-3 py-1 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-mono rounded border border-slate-800 transition-colors">
                    Load &rarr;
                </a>
            </td>
        </tr>
        """

    if not rows_html:
        rows_html = """
        <tr>
            <td colspan="4" class="py-8 text-center text-xs text-slate-600 font-mono">
                No session data available.
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>F1 Telemetry — Sessions</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{
                background-color: #030712;
                color: #f1f5f9;
                font-family: ui-sans-serif, system-ui, sans-serif;
            }}
        </style>
    </head>
    <body class="min-h-screen py-10 px-4">
        <div class="max-w-3xl mx-auto">
            <!-- Minimal Header -->
            <header class="mb-8 pb-4 border-b border-slate-900 flex justify-between items-baseline">
                <div>
                    <h1 class="text-sm font-bold font-mono tracking-wider text-slate-200 uppercase">F1 Telemetry Visualizer</h1>
                    <p class="text-xs font-mono text-slate-600 mt-1">Select session to compile geometry</p>
                </div>
                <span class="text-xs font-mono text-slate-700">OpenF1 API</span>
            </header>
            
            <!-- Clean Data Table -->
            <main class="border border-slate-900 rounded bg-slate-950/60 overflow-hidden">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="border-b border-slate-900 bg-slate-900/20 font-mono text-xs text-slate-500 uppercase tracking-wider">
                            <th class="py-3 px-4">Date</th>
                            <th class="py-3 px-4">Grand Prix / Circuit</th>
                            <th class="py-3 px-4">Session</th>
                            <th class="py-3 px-4 text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </main>
        </div>
    </body>
    </html>
    """