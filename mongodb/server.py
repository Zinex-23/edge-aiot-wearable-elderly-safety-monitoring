from datetime import datetime, timezone
from flask import Flask, request, jsonify, Response, stream_with_context
from pymongo import MongoClient, DESCENDING
import json
import time

# =========================
# CONFIG
# =========================
MONGO_URI = "mongodb+srv://dien572:dien562003@cluster0.smq9ywt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "elderly_aiot"
COLLECTION_NAME = "sensor_readings_new"

HOST = "0.0.0.0"
PORT = 5000

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
sensor_col = db[COLLECTION_NAME]

app = Flask(__name__)


# =========================
# HELPERS
# =========================
def parse_timestamp(ts_value):
    if not ts_value:
        return datetime.now(timezone.utc).replace(microsecond=0)

    try:
        ts_value = ts_value.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_value)
    except Exception:
        return datetime.now(timezone.utc).replace(microsecond=0)


def dt_to_iso(dt):
    if isinstance(dt, datetime):
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return None


def serialize_doc(doc):
    if not doc:
        return None

    hr = 0
    spo2 = 0

    if isinstance(doc.get("heart_rate"), list) and len(doc["heart_rate"]) > 0:
        hr = doc["heart_rate"][0].get("value", 0)

    if isinstance(doc.get("spo2"), list) and len(doc["spo2"]) > 0:
        spo2 = doc["spo2"][0].get("value", 0)

    return {
        "id": str(doc.get("_id", "")),
        "device_id": doc.get("device_id", ""),
        "user_id": doc.get("user_id", ""),
        "timestamp": dt_to_iso(doc.get("timestamp")),
        "heart_rate_value": float(hr),
        "spo2_value": float(spo2),
        "battery": int(doc.get("battery", 0)),
        "ax": float(doc.get("accel", {}).get("x", 0)),
        "ay": float(doc.get("accel", {}).get("y", 0)),
        "az": float(doc.get("accel", {}).get("z", 0)),
        "gx": float(doc.get("gyro", {}).get("x", 0)),
        "gy": float(doc.get("gyro", {}).get("y", 0)),
        "gz": float(doc.get("gyro", {}).get("z", 0)),
        "ir": int(doc.get("raw_ppg", {}).get("ir", 0)),
        "red": int(doc.get("raw_ppg", {}).get("red", 0)),
        "created_at": dt_to_iso(doc.get("created_at")),
    }


def get_latest_doc():
    doc = sensor_col.find_one(sort=[("timestamp", DESCENDING), ("_id", DESCENDING)])
    return serialize_doc(doc)


def get_history(limit=100):
    docs = list(
        sensor_col.find(
            {},
            {
                "_id": 1,
                "device_id": 1,
                "user_id": 1,
                "timestamp": 1,
                "heart_rate": 1,
                "spo2": 1,
                "battery": 1,
                "accel": 1,
                "gyro": 1,
                "raw_ppg": 1,
                "created_at": 1,
            },
        )
        .sort("timestamp", DESCENDING)
        .limit(limit)
    )
    docs.reverse()
    return [serialize_doc(doc) for doc in docs]


# =========================
# UI
# =========================
@app.route("/", methods=["GET"])
def dashboard():
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Wearable Realtime Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #08101d;
      --bg2: #0f172a;
      --card: #111b31;
      --card2: #16233d;
      --text: #e5eefc;
      --muted: #9fb0d0;
      --border: rgba(255,255,255,0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Inter, Arial, sans-serif;
      color: var(--text);
      background: linear-gradient(180deg, var(--bg), var(--bg2));
    }

    .container {
      max-width: 1450px;
      margin: 0 auto;
      padding: 24px;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 20px;
    }

    .title h1 {
      margin: 0;
      font-size: 30px;
    }

    .title p {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 14px;
    }

    .chips {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .chip {
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.05);
      padding: 10px 14px;
      border-radius: 999px;
      font-size: 14px;
    }

    .grid-cards {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }

    .card, .chart-card {
      background: linear-gradient(180deg, var(--card), var(--card2));
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 12px 28px rgba(0,0,0,0.28);
    }

    .card {
      padding: 18px;
    }

    .metric-label {
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 8px;
    }

    .metric-value {
      font-size: 34px;
      font-weight: 700;
    }

    .metric-sub {
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }

    .grid-charts {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }

    .chart-card {
      padding: 18px;
      height: 420px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .chart-title {
      margin: 0 0 12px;
      font-size: 16px;
      font-weight: 600;
      flex: 0 0 auto;
    }

    .chart-wrap {
      position: relative;
      flex: 1 1 auto;
      min-height: 0;
      width: 100%;
    }

    .chart-wrap canvas {
      position: absolute !important;
      inset: 0;
      width: 100% !important;
      height: 100% !important;
    }

    @media (max-width: 1100px) {
      .grid-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid-charts { grid-template-columns: 1fr; }
    }

    @media (max-width: 640px) {
      .grid-cards { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title">
        <h1>Wearable Realtime Dashboard</h1>
        <p>Realtime monitoring from MongoDB</p>
      </div>
      <div class="chips">
        <div class="chip">Server: <span id="server-status">Connecting...</span></div>
        <div class="chip">Device: <span id="device-id">--</span></div>
        <div class="chip">Last update: <span id="last-update">--</span></div>
      </div>
    </div>

    <div class="grid-cards">
      <div class="card">
        <div class="metric-label">Heart Rate</div>
        <div class="metric-value" id="heart-rate">--</div>
        <div class="metric-sub">bpm</div>
      </div>
      <div class="card">
        <div class="metric-label">SpO2</div>
        <div class="metric-value" id="spo2">--</div>
        <div class="metric-sub">%</div>
      </div>
      <div class="card">
        <div class="metric-label">Battery</div>
        <div class="metric-value" id="battery">--</div>
        <div class="metric-sub">%</div>
      </div>
      <div class="card">
        <div class="metric-label">Raw PPG</div>
        <div class="metric-value" id="ppg">IR -- / RED --</div>
        <div class="metric-sub">latest optical reading</div>
      </div>
    </div>

    <div class="grid-charts">
      <div class="chart-card">
        <h3 class="chart-title">Heart Rate & SpO2</h3>
        <div class="chart-wrap"><canvas id="vitalChart"></canvas></div>
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Raw PPG</h3>
        <div class="chart-wrap"><canvas id="ppgChart"></canvas></div>
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Accelerometer XYZ Radar</h3>
        <div class="chart-wrap"><canvas id="accelRadarChart"></canvas></div>
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Gyroscope XYZ Radar</h3>
        <div class="chart-wrap"><canvas id="gyroRadarChart"></canvas></div>
      </div>
    </div>
  </div>

  <script>
    let latestId = null;
    const maxPoints = 120;

    function fmtTime(ts) {
      if (!ts) return "--";
      return new Date(ts).toLocaleTimeString();
    }

    function createLineChart(canvasId, datasets) {
      const ctx = document.getElementById(canvasId).getContext("2d");
      return new Chart(ctx, {
        type: "line",
        data: { labels: [], datasets: datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          parsing: false,
          normalized: true,
          interaction: { mode: "index", intersect: false },
          elements: {
            point: { radius: 1.5, hoverRadius: 3 },
            line: { borderWidth: 2, tension: 0.25 }
          },
          scales: {
            x: {
              ticks: { color: "#9fb0d0", maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
              grid: { color: "rgba(255,255,255,0.06)" }
            },
            y: {
              ticks: { color: "#9fb0d0" },
              grid: { color: "rgba(255,255,255,0.06)" }
            }
          },
          plugins: {
            legend: { labels: { color: "#e5eefc" } }
          }
        }
      });
    }

    function createRadarChart(canvasId, datasets, suggestedMin, suggestedMax) {
      const ctx = document.getElementById(canvasId).getContext("2d");
      return new Chart(ctx, {
        type: "radar",
        data: {
          labels: ["X", "Y", "Z"],
          datasets: datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          scales: {
            r: {
              suggestedMin: suggestedMin,
              suggestedMax: suggestedMax,
              ticks: {
                color: "#9fb0d0",
                backdropColor: "transparent"
              },
              grid: { color: "rgba(255,255,255,0.08)" },
              angleLines: { color: "rgba(255,255,255,0.08)" },
              pointLabels: {
                color: "#e5eefc",
                font: { size: 14, weight: "600" }
              }
            }
          },
          plugins: {
            legend: { labels: { color: "#e5eefc" } }
          }
        }
      });
    }

    const vitalChart = createLineChart("vitalChart", [
      { label: "Heart Rate", data: [], borderColor: "#60a5fa", backgroundColor: "rgba(96,165,250,0.18)" },
      { label: "SpO2", data: [], borderColor: "#22c55e", backgroundColor: "rgba(34,197,94,0.18)" }
    ]);

    const ppgChart = createLineChart("ppgChart", [
      { label: "IR", data: [], borderColor: "#f472b6", backgroundColor: "rgba(244,114,182,0.18)" },
      { label: "RED", data: [], borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.18)" }
    ]);

    const accelRadarChart = createRadarChart("accelRadarChart", [
      {
        label: "Current Accel",
        data: [0, 0, 0],
        borderColor: "#60a5fa",
        backgroundColor: "rgba(96,165,250,0.28)",
        pointBackgroundColor: "#60a5fa",
        borderWidth: 2
      }
    ], -2, 2);

    const gyroRadarChart = createRadarChart("gyroRadarChart", [
      {
        label: "Current Gyro",
        data: [0, 0, 0],
        borderColor: "#f59e0b",
        backgroundColor: "rgba(245,158,11,0.28)",
        pointBackgroundColor: "#f59e0b",
        borderWidth: 2
      }
    ], -500, 500);

    function trimLineChart(chart) {
      while (chart.data.labels.length > maxPoints) {
        chart.data.labels.shift();
        chart.data.datasets.forEach(ds => ds.data.shift());
      }
    }

    function updateSummary(doc) {
      document.getElementById("heart-rate").textContent = Number(doc.heart_rate_value || 0).toFixed(1);
      document.getElementById("spo2").textContent = Number(doc.spo2_value || 0).toFixed(1);
      document.getElementById("battery").textContent = String(doc.battery ?? 0);
      document.getElementById("ppg").textContent = `IR ${doc.ir ?? 0} / RED ${doc.red ?? 0}`;
      document.getElementById("device-id").textContent = doc.device_id || "--";
      document.getElementById("last-update").textContent = fmtTime(doc.timestamp);
    }

    function appendLineData(doc) {
      const label = fmtTime(doc.timestamp);

      vitalChart.data.labels.push(label);
      vitalChart.data.datasets[0].data.push(Number(doc.heart_rate_value ?? 0));
      vitalChart.data.datasets[1].data.push(Number(doc.spo2_value ?? 0));
      trimLineChart(vitalChart);
      vitalChart.update("none");

      ppgChart.data.labels.push(label);
      ppgChart.data.datasets[0].data.push(Number(doc.ir ?? 0));
      ppgChart.data.datasets[1].data.push(Number(doc.red ?? 0));
      trimLineChart(ppgChart);
      ppgChart.update("none");
    }

    function updateRadarCharts(doc) {
      accelRadarChart.data.datasets[0].data = [
        Number(doc.ax ?? 0),
        Number(doc.ay ?? 0),
        Number(doc.az ?? 0)
      ];
      accelRadarChart.update("none");

      gyroRadarChart.data.datasets[0].data = [
        Number(doc.gx ?? 0),
        Number(doc.gy ?? 0),
        Number(doc.gz ?? 0)
      ];
      gyroRadarChart.update("none");
    }

    function applyDoc(doc) {
      if (!doc) return;
      if (latestId === doc.id) return;

      latestId = doc.id;
      updateSummary(doc);
      appendLineData(doc);
      updateRadarCharts(doc);
    }

    async function loadHistory() {
      const res = await fetch("/api/history?limit=120");
      const data = await res.json();
      if (!data.ok) return;

      document.getElementById("server-status").textContent = "Online";

      for (const item of data.items) {
        updateSummary(item);
        appendLineData(item);
      }

      if (data.items.length > 0) {
        const last = data.items[data.items.length - 1];
        latestId = last.id;
        updateRadarCharts(last);
      }
    }

    function connectStream() {
      const evt = new EventSource("/stream");

      evt.onopen = () => {
        document.getElementById("server-status").textContent = "Online";
      };

      evt.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "new_data" && payload.item) {
            applyDoc(payload.item);
          }
        } catch (err) {
          console.error("SSE parse error:", err);
        }
      };

      evt.onerror = () => {
        document.getElementById("server-status").textContent = "Reconnecting...";
      };
    }

    loadHistory().then(() => connectStream());
  </script>
</body>
</html>
    """
    return Response(html, mimetype="text/html")


# =========================
# API
# =========================
@app.route("/api/health", methods=["GET"])
def health():
    try:
        client.admin.command("ping")
        return jsonify({"ok": True, "mongodb": "connected"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/latest", methods=["GET"])
def api_latest():
    try:
        return jsonify({"ok": True, "item": get_latest_doc()}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def api_history():
    try:
        limit = int(request.args.get("limit", 120))
        limit = max(1, min(limit, 500))
        items = get_history(limit=limit)
        return jsonify({"ok": True, "count": len(items), "items": items}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sensor", methods=["POST"])
def receive_sensor():
    try:
        data = request.get_json(force=True)
        sample_time = parse_timestamp(data.get("timestamp"))

        document = {
            "device_id": data.get("device_id", "wristband_001"),
            "user_id": data.get("user_id", "elder_001"),
            "timestamp": sample_time,
            "heart_rate": [{"timestamp": sample_time, "value": float(data.get("heart_rate_value", 0))}],
            "spo2": [{"timestamp": sample_time, "value": float(data.get("spo2_value", 0))}],
            "battery": int(data.get("battery", 0)),
            "accel": {
                "x": float(data.get("ax", 0)),
                "y": float(data.get("ay", 0)),
                "z": float(data.get("az", 0))
            },
            "gyro": {
                "x": float(data.get("gx", 0)),
                "y": float(data.get("gy", 0)),
                "z": float(data.get("gz", 0))
            },
            "raw_ppg": {
                "ir": int(data.get("ir", 0)),
                "red": int(data.get("red", 0))
            },
            "created_at": datetime.now(timezone.utc).replace(microsecond=0)
        }

        result = sensor_col.insert_one(document)

        return jsonify({
            "ok": True,
            "inserted_id": str(result.inserted_id)
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# =========================
# SSE REALTIME
# =========================
@app.route("/stream")
def stream():
    @stream_with_context
    def event_stream():
        last_id = None

        while True:
            try:
                latest = sensor_col.find_one(sort=[("timestamp", DESCENDING), ("_id", DESCENDING)])
                if latest:
                    current_id = str(latest["_id"])
                    if current_id != last_id:
                        last_id = current_id
                        payload = {
                            "type": "new_data",
                            "item": serialize_doc(latest)
                        }
                        yield f"data: {json.dumps(payload)}\\n\\n"
                    else:
                        yield ": keep-alive\\n\\n"

                time.sleep(0.2)

            except Exception as e:
                payload = {
                    "type": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(payload)}\\n\\n"
                time.sleep(1)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False, threaded=True)