from flask import Flask, request, jsonify, render_template_string
from collections import deque
import time

app = Flask(__name__)

# Store the last 200 swings in memory
swing_history = deque(maxlen=200)

# Simple HTML dashboard (phone-friendly)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Golf Swing Coach</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 1rem; background: #111; color: #f5f5f5; }
    h1 { font-size: 1.4rem; margin-bottom: 0.5rem; }
    .status { margin-bottom: 1rem; padding: 0.8rem; border-radius: 8px; background: #222; }
    .label { font-size: 0.8rem; opacity: 0.7; }
    .value { font-size: 1.2rem; font-weight: 600; }
    .good { color: #4caf50; }
    .bad  { color: #ff5252; }
    table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 0.8rem; }
    th, td { padding: 0.4rem; border-bottom: 1px solid #333; text-align: left; }
    tr:nth-child(even) { background: #181818; }
    .chip { display: inline-block; padding: 0.15rem 0.4rem; border-radius: 12px; font-size: 0.7rem; background: #333; }
  </style>
</head>
<body>
  <h1>Golf Swing Coach</h1>

  <div class="status">
    <div class="label">Connection</div>
    <div id="connection" class="value bad">Waiting for data...</div>
  </div>

  <div class="status">
    <div class="label">Last swing angle (plane)</div>
    <div id="angle" class="value">–</div>
    <div class="label">Status: <span id="planeStatus" class="chip">–</span></div>
  </div>

  <div class="status">
    <div class="label">Recent swings</div>
    <table id="historyTable">
      <thead>
        <tr>
          <th>Time</th>
          <th>Angle</th>
          <th>Mode</th>
          <th>Quality</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <script>
    async function fetchData() {
      try {
        const res = await fetch('/recent-data');
        if (!res.ok) throw new Error('Request failed');
        const data = await res.json();

        const conn = document.getElementById('connection');
        if (data.history.length === 0) {
          conn.textContent = 'No data yet';
          conn.className = 'value bad';
          return;
        } else {
          conn.textContent = 'Receiving data ✓';
          conn.className = 'value good';
        }

        const last = data.history[0];
        document.getElementById('angle').textContent = last.angle.toFixed(3);

        const planeStatus = document.getElementById('planeStatus');
        planeStatus.textContent = last.coaching;
        planeStatus.className = 'chip ' + (last.on_plane ? 'good' : 'bad');

        const tbody = document.querySelector('#historyTable tbody');
        tbody.innerHTML = '';
        data.history.slice(0, 20).forEach(item => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${new Date(item.timestamp * 1000).toLocaleTimeString()}</td>
            <td>${item.angle.toFixed(3)}</td>
            <td>${item.mode}</td>
            <td>${item.coaching}</td>
          `;
          tbody.appendChild(tr);
        });

      } catch (e) {
        const conn = document.getElementById('connection');
        conn.textContent = 'Error talking to server';
        conn.className = 'value bad';
      }
    }

    // Refresh every 1.5 seconds
    setInterval(fetchData, 1500);
    fetchData();
  </script>
</body>
</html>
"""

# Route: dashboard page
@app.route("/")
@app.route("/dashboard")
def dashboard():
  return render_template_string(DASHBOARD_HTML)

# Route: device POSTs data here
@app.route("/swing-data", methods=["POST"])
def swing_data():
  payload = request.get_json(force=True, silent=True) or {}

  angle = float(payload.get("angle", 0.0))
  mode = payload.get("mode", "continuous")
  ts   = int(time.time())

  # Define "on plane" range – this should match your ESP32 logic
  PLANE_TARGET = -0.30
  PLANE_TOLERANCE = 0.15
  diff = abs(angle - PLANE_TARGET)
  on_plane = diff <= PLANE_TOLERANCE

  coaching = "On plane"
  if not on_plane:
    if angle < PLANE_TARGET:
      coaching = "Too bowed / low"
    else:
      coaching = "Too cupped / high"

  record = {
    "timestamp": ts,
    "angle": angle,
    "mode": mode,
    "on_plane": on_plane,
    "coaching": coaching,
  }

  swing_history.appendleft(record)

  return jsonify({"status": "ok", "recorded": record})

# Route: dashboard pulls JSON history
@app.route("/recent-data", methods=["GET"])
def recent_data():
  return jsonify({
    "count": len(swing_history),
    "history": list(swing_history)
  })

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
