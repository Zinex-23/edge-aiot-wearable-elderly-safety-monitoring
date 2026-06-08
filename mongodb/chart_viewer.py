"""
chart_viewer.py — Web chart viewer cho vitals từ MongoDB, giống UI app Android
Chạy:  python chart_viewer.py
Mở:    http://localhost:3000
"""

from flask import Flask, jsonify, render_template_string, request
from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

MONGO_URI = (
    "mongodb+srv://dien572:dien562003@cluster0.smq9ywt.mongodb.net/"
    "?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME = "elderly_aiot"

client = MongoClient(MONGO_URI)
col    = client[DB_NAME]["vitals"]


# ─── Bucketing — giống hệt Android MonitoringViewModel.bucketCloud() ─────────

def bucket_cloud(items: list, slot_count: int, slot_ms: int, now_ms: int):
    current_slot = (now_ms // slot_ms) * slot_ms
    oldest_slot  = current_slot - (slot_count - 1) * slot_ms

    hr_sum   = [0.0] * slot_count
    hr_count = [0]   * slot_count
    sp_sum   = [0.0] * slot_count
    sp_count = [0]   * slot_count
    bat_sum  = [0.0] * slot_count
    bat_count= [0]   * slot_count

    for item in items:
        ts = item.get("timestamp")
        if isinstance(ts, datetime):
            # Naive datetime từ MongoDB → luôn là UTC, gắn tzinfo để tránh local-time misinterpret
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts_ms = int(ts.timestamp() * 1000)
        else:
            try:
                dt = datetime.strptime(str(ts), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                ts_ms = int(dt.timestamp() * 1000)
            except Exception:
                continue

        if ts_ms < oldest_slot or ts_ms > current_slot + slot_ms:
            continue

        idx = int((ts_ms - oldest_slot) / slot_ms)
        idx = max(0, min(idx, slot_count - 1))

        hr  = item.get("heartRate")
        sp  = item.get("spo2")
        bat = item.get("battery")
        if hr is not None and int(hr) > 0:
            hr_sum[idx]   += int(hr)
            hr_count[idx] += 1
        if sp is not None and int(sp) > 0:
            sp_sum[idx]   += int(sp)
            sp_count[idx] += 1
        if bat is not None and int(bat) > 0:
            bat_sum[idx]   += int(bat)
            bat_count[idx] += 1

    hr_out  = [round(hr_sum[i] / hr_count[i])  if hr_count[i]  > 0 else None for i in range(slot_count)]
    sp_out  = [round(sp_sum[i] / sp_count[i])  if sp_count[i]  > 0 else None for i in range(slot_count)]
    bat_out = [round(bat_sum[i] / bat_count[i]) if bat_count[i] > 0 else None for i in range(slot_count)]
    return hr_out, sp_out, bat_out


def slot_labels(slot_count: int, slot_ms: int, now_ms: int) -> list[str]:
    current_slot = (now_ms // slot_ms) * slot_ms
    oldest_slot  = current_slot - (slot_count - 1) * slot_ms
    out = []
    for i in range(slot_count):
        dt = datetime.fromtimestamp((oldest_slot + i * slot_ms) / 1000, tz=timezone.utc)
        if slot_ms >= 86_400_000:
            out.append(dt.strftime("%m/%d"))
        elif slot_ms < 3_600_000:
            out.append(dt.strftime("%H:%M"))
        else:
            out.append(dt.strftime("%m/%d %H:00"))
    return out


def make_stats(vals: list) -> dict:
    good = [v for v in vals if v is not None and v > 0]
    current = next((v for v in reversed(vals) if v and v > 0), None)
    return {
        "current": current,
        "min":  min(good)  if good else None,
        "max":  max(good)  if good else None,
        "avg":  round(sum(good) / len(good), 1) if good else None,
    }


# ─── API: list users ──────────────────────────────────────────────────────────

@app.route("/api/users")
def api_users():
    users = col.distinct("userId")
    return jsonify({"users": users})


# ─── API: vitals data ─────────────────────────────────────────────────────────

@app.route("/api/vitals")
def api_vitals():
    range_str = request.args.get("range", "1h")
    user_id   = request.args.get("userId", "")
    now       = datetime.now(timezone.utc)
    now_ms    = int(now.timestamp() * 1000)

    # ── LIVE: last 5 min, individual readings, line chart ────────────────
    if range_str == "5m":
        since = now - timedelta(minutes=5)
        docs  = list(col.find(
            {"userId": user_id, "timestamp": {"$gte": since}},
            {"_id": 0, "timestamp": 1, "heartRate": 1, "spo2": 1, "battery": 1}
        ).sort("timestamp", ASCENDING).limit(100))

        labels   = []
        hr_vals  = []
        sp_vals  = []
        bat_vals = []
        for d in docs:
            ts = d.get("timestamp")
            if isinstance(ts, datetime) and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            labels.append(ts.strftime("%H:%M:%S") if isinstance(ts, datetime) else str(ts))
            hr_vals.append(d.get("heartRate"))
            sp_vals.append(d.get("spo2"))
            bat_vals.append(d.get("battery"))

        # Stats từ 1h gần nhất (cho mini stats row)
        since_1h = now - timedelta(hours=1)
        docs_1h  = list(col.find(
            {"userId": user_id, "timestamp": {"$gte": since_1h}},
            {"_id": 0, "heartRate": 1, "spo2": 1, "battery": 1}
        ))
        hr_1h = [d["heartRate"] for d in docs_1h if d.get("heartRate") and d["heartRate"] > 0]
        sp_1h = [d["spo2"]      for d in docs_1h if d.get("spo2")      and d["spo2"]      > 0]
        bat_1h= [d["battery"]   for d in docs_1h if d.get("battery")   and d["battery"]   > 0]

        return jsonify({
            "labels":    labels,
            "hr":        hr_vals,
            "spo2":      sp_vals,
            "battery":   bat_vals,
            "stats": {
                "hr":   {"current": hr_vals[-1] if hr_vals else None,
                         "min": min(hr_1h) if hr_1h else None,
                         "max": max(hr_1h) if hr_1h else None,
                         "avg": round(sum(hr_1h) / len(hr_1h), 1) if hr_1h else None},
                "spo2": {"current": sp_vals[-1] if sp_vals else None,
                         "min": min(sp_1h) if sp_1h else None,
                         "max": max(sp_1h) if sp_1h else None,
                         "avg": round(sum(sp_1h) / len(sp_1h), 1) if sp_1h else None},
                "battery": {"current": bat_vals[-1] if bat_vals else None,
                            "min": min(bat_1h) if bat_1h else None,
                            "max": max(bat_1h) if bat_1h else None,
                            "avg": round(sum(bat_1h) / len(bat_1h), 1) if bat_1h else None},
            },
            "chartType": "line",
            "count":     len(labels),
        })

    # ── 1H: 12 slots × 5 min, bar chart ──────────────────────────────────
    elif range_str == "1h":
        since = now - timedelta(hours=1)
        docs  = list(col.find(
            {"userId": user_id, "timestamp": {"$gte": since}},
            {"_id": 0, "timestamp": 1, "heartRate": 1, "spo2": 1, "battery": 1}
        ).sort("timestamp", DESCENDING).limit(300))
        docs.reverse()

        hr_buckets, sp_buckets, bat_buckets = bucket_cloud(docs, 12, 5 * 60_000, now_ms)
        labels = slot_labels(12, 5 * 60_000, now_ms)

        return jsonify({
            "labels":    labels,
            "hr":        hr_buckets,
            "spo2":      sp_buckets,
            "battery":   bat_buckets,
            "stats":     {"hr": make_stats(hr_buckets), "spo2": make_stats(sp_buckets), "battery": make_stats(bat_buckets)},
            "chartType": "bar",
            "count":     len(docs),
        })

    # ── 24H: hourly aggregation server-side, 24 slots × 1h, bar chart ────
    elif range_str == "24h":
        since    = now - timedelta(hours=24)
        pipeline = [
            {"$match": {"userId": user_id, "timestamp": {"$gte": since, "$lte": now}}},
            {"$group": {
                "_id":     {"$dateToString": {"format": "%Y-%m-%dT%H:00:00Z", "date": "$timestamp"}},
                "avgHR":   {"$avg": "$heartRate"},
                "avgSpo2": {"$avg": "$spo2"},
                "avgBat":  {"$avg": "$battery"},
                "count":   {"$sum": 1},
            }},
            {"$sort":  {"_id": 1}},
            {"$limit": 24},
        ]
        agg_items = [
            {
                "timestamp": b["_id"],
                "heartRate": round(b["avgHR"])   if b.get("avgHR")   is not None else None,
                "spo2":      round(b["avgSpo2"]) if b.get("avgSpo2") is not None else None,
                "battery":   round(b["avgBat"])  if b.get("avgBat")  is not None else None,
            }
            for b in col.aggregate(pipeline)
        ]

        hr_buckets, sp_buckets, bat_buckets = bucket_cloud(agg_items, 24, 60 * 60_000, now_ms)
        labels = slot_labels(24, 60 * 60_000, now_ms)
        raw_count = sum(
            b.get("count", 0)
            for b in col.aggregate([
                {"$match": {"userId": user_id, "timestamp": {"$gte": since, "$lte": now}}},
                {"$count": "count"}
            ])
        )

        return jsonify({
            "labels":    labels,
            "hr":        hr_buckets,
            "spo2":      sp_buckets,
            "battery":   bat_buckets,
            "stats":     {"hr": make_stats(hr_buckets), "spo2": make_stats(sp_buckets), "battery": make_stats(bat_buckets)},
            "chartType": "bar",
            "count":     raw_count,
        })

    # ── 3D: hourly aggregation server-side, 72 slots × 1h, bar chart ────
    elif range_str == "3d":
        since    = now - timedelta(days=3)
        pipeline = [
            {"$match": {"userId": user_id, "timestamp": {"$gte": since, "$lte": now}}},
            {"$group": {
                "_id":     {"$dateToString": {"format": "%Y-%m-%dT%H:00:00Z", "date": "$timestamp"}},
                "avgHR":   {"$avg": "$heartRate"},
                "avgSpo2": {"$avg": "$spo2"},
                "avgBat":  {"$avg": "$battery"},
                "count":   {"$sum": 1},
            }},
            {"$sort":  {"_id": 1}},
        ]
        agg_items = [
            {
                "timestamp": b["_id"],
                "heartRate": round(b["avgHR"])   if b.get("avgHR")   is not None else None,
                "spo2":      round(b["avgSpo2"]) if b.get("avgSpo2") is not None else None,
                "battery":   round(b["avgBat"])  if b.get("avgBat")  is not None else None,
            }
            for b in col.aggregate(pipeline)
        ]

        hr_buckets, sp_buckets, bat_buckets = bucket_cloud(agg_items, 72, 60 * 60_000, now_ms)
        labels = slot_labels(72, 60 * 60_000, now_ms)
        raw_count = sum(
            b.get("count", 0)
            for b in col.aggregate([
                {"$match": {"userId": user_id, "timestamp": {"$gte": since, "$lte": now}}},
                {"$count": "count"}
            ])
        )

        return jsonify({
            "labels":    labels,
            "hr":        hr_buckets,
            "spo2":      sp_buckets,
            "battery":   bat_buckets,
            "stats":     {"hr": make_stats(hr_buckets), "spo2": make_stats(sp_buckets), "battery": make_stats(bat_buckets)},
            "chartType": "bar",
            "count":     raw_count,
        })

    # ── 7D: hourly aggregation server-side, 168 slots × 1h, line chart ────
    elif range_str == "7d":
        since    = now - timedelta(days=7)
        pipeline = [
            {"$match": {"userId": user_id, "timestamp": {"$gte": since, "$lte": now}}},
            {"$group": {
                "_id":     {"$dateToString": {"format": "%Y-%m-%dT%H:00:00Z", "date": "$timestamp"}},
                "avgHR":   {"$avg": "$heartRate"},
                "avgSpo2": {"$avg": "$spo2"},
                "avgBat":  {"$avg": "$battery"},
                "count":   {"$sum": 1},
            }},
            {"$sort":  {"_id": 1}},
        ]
        agg_items = [
            {
                "timestamp": b["_id"],
                "heartRate": round(b["avgHR"])   if b.get("avgHR")   is not None else None,
                "spo2":      round(b["avgSpo2"]) if b.get("avgSpo2") is not None else None,
                "battery":   round(b["avgBat"])  if b.get("avgBat")  is not None else None,
            }
            for b in col.aggregate(pipeline)
        ]

        hr_buckets, sp_buckets, bat_buckets = bucket_cloud(agg_items, 168, 60 * 60_000, now_ms)
        labels = slot_labels(168, 60 * 60_000, now_ms)
        raw_count = sum(
            b.get("count", 0)
            for b in col.aggregate([
                {"$match": {"userId": user_id, "timestamp": {"$gte": since, "$lte": now}}},
                {"$count": "count"}
            ])
        )

        return jsonify({
            "labels":    labels,
            "hr":        hr_buckets,
            "spo2":      sp_buckets,
            "battery":   bat_buckets,
            "stats":     {"hr": make_stats(hr_buckets), "spo2": make_stats(sp_buckets), "battery": make_stats(bat_buckets)},
            "chartType": "line",
            "count":     raw_count,
        })

    return jsonify({"error": "invalid range"}), 400


# ─── HTML ─────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AIFD Vitals Viewer</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;padding:16px 12px}

.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.header h1{font-size:18px;font-weight:700;color:#58a6ff;display:flex;align-items:center;gap:6px}
.user-select{background:#161b22;border:1px solid #30363d;color:#e6edf3;padding:6px 10px;border-radius:8px;font-size:13px;cursor:pointer;outline:none}
.user-select:focus{border-color:#58a6ff}

.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:18px;margin-bottom:14px}

/* Metric tabs */
.metric-tabs{display:flex;gap:8px;margin-bottom:16px}
.mtab{flex:1;padding:10px 6px;border-radius:10px;border:2px solid #30363d;background:#0d1117;color:#8b949e;font-size:13px;font-weight:600;cursor:pointer;text-align:center;transition:all .2s}
.mtab.hr-on{border-color:#58a6ff;color:#58a6ff;background:rgba(88,166,255,.1)}
.mtab.sp-on{border-color:#3fb950;color:#3fb950;background:rgba(63,185,80,.1)}
.mtab.bat-on{border-color:#d29922;color:#d29922;background:rgba(210,153,34,.1)}

/* Big value */
.bigval{text-align:center;margin-bottom:16px}
.bigval .num{font-size:60px;font-weight:700;line-height:1;letter-spacing:-2px}
.bigval .unit{font-size:20px;color:#8b949e;margin-left:2px}
.bigval .lbl{font-size:12px;color:#8b949e;margin-top:4px;text-transform:uppercase;letter-spacing:.8px}
.hr-color{color:#58a6ff}.sp-color{color:#3fb950}.bat-color{color:#d29922}

/* Chart */
.chart-wrap{position:relative;height:210px;margin-bottom:14px}

/* Range tabs */
.rtabs{display:flex;background:#0d1117;border-radius:10px;padding:4px;gap:3px;margin-bottom:16px}
.rtab{flex:1;padding:8px 4px;border-radius:7px;border:none;background:transparent;color:#8b949e;font-size:13px;font-weight:600;cursor:pointer;transition:all .2s;text-align:center}
.rtab.on{background:#21262d;color:#e6edf3;box-shadow:0 1px 4px rgba(0,0,0,.4)}

/* Stats */
.stats{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px}
.scard{background:#0d1117;border-radius:8px;padding:10px 6px;text-align:center}
.scard .slbl{font-size:10px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.scard .sval{font-size:17px;font-weight:700}

/* Status */
.statusbar{display:flex;align-items:center;justify-content:space-between;margin-top:14px;font-size:11px;color:#8b949e}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:4px;vertical-align:middle}
.dot-g{background:#3fb950;animation:blink 2s infinite}
.dot-y{background:#d29922}
.dot-r{background:#f85149}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

.rbtn{background:#21262d;border:1px solid #30363d;color:#c9d1d9;padding:5px 12px;border-radius:6px;font-size:12px;cursor:pointer}
.rbtn:hover{background:#30363d}

.spinner{display:inline-block;width:12px;height:12px;border:2px solid #30363d;border-top-color:#58a6ff;border-radius:50%;animation:spin .7s linear infinite;margin-right:5px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}

.nodata{text-align:center;color:#8b949e;padding:30px 0;font-size:14px}

/* Second card — raw data table */
.data-card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px}
.data-card h3{font-size:14px;color:#8b949e;margin-bottom:10px;font-weight:600}
.data-table{width:100%;border-collapse:collapse;font-size:12px}
.data-table th{color:#8b949e;text-align:left;padding:4px 8px;border-bottom:1px solid #21262d;font-weight:500}
.data-table td{padding:5px 8px;border-bottom:1px solid #161b22;font-family:monospace}
.data-table tr:last-child td{border:none}
.val-hr{color:#58a6ff;font-weight:600}
.val-sp{color:#3fb950;font-weight:600}
.val-bat{color:#d29922;font-weight:600}
.val-null{color:#484f58}
</style>
</head>
<body>

<div class="header">
  <h1>❤️ AIFD Vitals Viewer</h1>
  <select class="user-select" id="userSel" onchange="onUser()"></select>
</div>

<div class="card">
  <!-- Metric tabs -->
  <div class="metric-tabs">
    <button class="mtab hr-on" id="mHR"  onclick="setMetric('hr')">❤ Heart Rate</button>
    <button class="mtab"       id="mSP"  onclick="setMetric('spo2')">💧 SpO₂</button>
    <button class="mtab"       id="mBAT" onclick="setMetric('battery')">🔋 Pin</button>
  </div>

  <!-- Big value -->
  <div class="bigval">
    <div><span class="num hr-color" id="bigNum">–</span><span class="unit" id="bigUnit">bpm</span></div>
    <div class="lbl" id="bigLbl">Heart Rate</div>
  </div>

  <!-- Chart -->
  <div class="chart-wrap"><canvas id="cv"></canvas></div>

  <!-- Range tabs -->
  <div class="rtabs">
    <button class="rtab on" id="r5m"   onclick="setRange('5m')">5m</button>
    <button class="rtab"    id="r1h"   onclick="setRange('1h')">1H</button>
    <button class="rtab"    id="r24h"  onclick="setRange('24h')">24H</button>
    <button class="rtab"    id="r3d"   onclick="setRange('3d')">3D</button>
    <button class="rtab"    id="r7d"   onclick="setRange('7d')">7D</button>
  </div>

  <!-- Stats -->
  <div class="stats" id="statsGrid">
    <div class="scard"><div class="slbl">Current</div><div class="sval" id="sCur"  style="color:#e6edf3">–</div></div>
    <div class="scard" id="cardMin"><div class="slbl">Min</div>    <div class="sval" id="sMin"  style="color:#58a6ff">–</div></div>
    <div class="scard" id="cardMax"><div class="slbl">Max</div>    <div class="sval" id="sMax"  style="color:#f85149">–</div></div>
    <div class="scard" id="cardAvg"><div class="slbl">Avg</div>    <div class="sval" id="sAvg"  style="color:#e6edf3">–</div></div>
  </div>

  <!-- Status bar -->
  <div class="statusbar">
    <span id="status"><span class="dot dot-y"></span>Connecting...</span>
    <button class="rbtn" onclick="load()">↻ Refresh</button>
  </div>
</div>

<!-- Raw data table -->
<div class="data-card">
  <h3 id="tableTitle">Recent records</h3>
  <table class="data-table">
    <thead><tr><th>#</th><th>Timestamp (UTC)</th><th>HR (bpm)</th><th>SpO₂ (%)</th><th>Pin (%)</th></tr></thead>
    <tbody id="tbody"></tbody>
  </table>
</div>

<script>
// ── State ──────────────────────────────────────────────────────────────────
let range  = '5m';
let metric = 'hr';
let user   = '';
let chart  = null;
let timer  = null;
let cache  = null;
const INTERVALS = { '5m': 10_000, '1h': 60_000, '24h': 300_000, '3d': 600_000, '7d': 600_000 };

// ── Init ───────────────────────────────────────────────────────────────────
async function init() {
  const r   = await fetch('/api/users');
  const d   = await r.json();
  const sel = document.getElementById('userSel');
  sel.innerHTML = '';
  (d.users || []).forEach(u => {
    const o = document.createElement('option');
    o.value = o.text = u;
    sel.appendChild(o);
  });
  if (d.users && d.users.length) {
    user = d.users[d.users.length - 1];
    sel.value = user;
  }
  load();
}

function onUser() {
  user = document.getElementById('userSel').value;
  load();
}

// ── Tab switching ──────────────────────────────────────────────────────────
function setRange(r) {
  clearTimeout(timer);
  range = r;
  ['5m','1h','24h','3d','7d'].forEach(x => document.getElementById('r'+x).classList.remove('on'));
  document.getElementById('r' + r).classList.add('on');
  if (chart) { chart.destroy(); chart = null; }
  load();
}

function setMetric(m) {
  metric = m;
  const isHR = m === 'hr';
  const isSP = m === 'spo2';
  const isBAT= m === 'battery';
  document.getElementById('mHR').className = 'mtab' + (isHR  ? ' hr-on' : '');
  document.getElementById('mSP').className = 'mtab' + (isSP  ? ' sp-on' : '');
  document.getElementById('mBAT').className= 'mtab' + (isBAT ? ' bat-on': '');
  document.getElementById('bigUnit').textContent = isHR ? 'bpm' : '%';
  document.getElementById('bigLbl').textContent  = isHR ? 'Heart Rate' : (isSP ? 'SpO₂' : 'Pin');
  document.getElementById('bigNum').className    = 'num ' + (isHR ? 'hr-color' : (isSP ? 'sp-color' : 'bat-color'));
  if (cache) renderUI(cache);
}

// ── Load data ──────────────────────────────────────────────────────────────
async function load() {
  clearTimeout(timer);
  setStatus('loading');
  try {
    const r = await fetch(`/api/vitals?range=${range}&userId=${encodeURIComponent(user)}`);
    cache   = await r.json();
    renderUI(cache);
    setStatus('ok', cache.count);
  } catch(e) {
    setStatus('error', 0, e.message);
  }
  timer = setTimeout(load, INTERVALS[range]);
}

// ── Render ─────────────────────────────────────────────────────────────────
function renderUI(data) {
  if (!data) return;
  const isHR = metric === 'hr';
  const isSP = metric === 'spo2';
  const isBAT= metric === 'battery';
  
  const vals  = isHR ? data.hr : (isSP ? data.spo2 : data.battery);
  const stats = isHR ? data.stats?.hr : (isSP ? data.stats?.spo2 : data.stats?.battery);
  const color = isHR ? '#58a6ff' : (isSP ? '#3fb950' : '#d29922');
  const colorFade = isHR ? 'rgba(88,166,255,.14)' : (isSP ? 'rgba(63,185,80,.14)' : 'rgba(210,153,34,.14)');
  const unit  = isHR ? 'bpm' : '%';
  const isLine = data.chartType === 'line';

  // Big value
  const cur = stats?.current;
  document.getElementById('bigNum').textContent = cur != null ? cur : '–';

  // Stats row
  const fmt = v => v != null ? v + ' ' + unit : '–';
  document.getElementById('sCur').textContent = fmt(stats?.current);
  document.getElementById('sMin').textContent = fmt(stats?.min);
  document.getElementById('sMax').textContent = fmt(stats?.max);
  document.getElementById('sAvg').textContent = stats?.avg != null ? stats.avg + ' ' + unit : '–';

  // Hide Min/Max/Avg for Battery
  const dsp = isBAT ? 'none' : 'block';
  document.getElementById('cardMin').style.display = dsp;
  document.getElementById('cardMax').style.display = dsp;
  document.getElementById('cardAvg').style.display = dsp;
  document.getElementById('statsGrid').style.gridTemplateColumns = isBAT ? '1fr' : '1fr 1fr 1fr 1fr';

  // Chart data — null/0 → NaN (gap in chart)
  const chartData = (vals || []).map(v => (v != null && v > 0) ? v : NaN);
  const labels    = data.labels || [];
  const barColors = chartData.map(v => isNaN(v) ? 'rgba(48,54,61,.4)' : color);

  if (chart && chart.config.type === (isLine ? 'line' : 'bar')) {
    // Same chart type — just update data
    chart.data.labels                        = labels;
    chart.data.datasets[0].data             = chartData;
    chart.data.datasets[0].borderColor      = color;
    chart.data.datasets[0].backgroundColor  = isLine ? colorFade : barColors;
    chart.data.datasets[0].pointBackgroundColor = color;
    chart.options.scales.y.min = isHR ? 40 : (isSP ? 80 : 0);
    chart.options.scales.y.max = isHR ? 140 : (isSP ? 101 : 105);
    chart.update('active');
  } else {
    // Rebuild chart (type changed or first load)
    if (chart) { chart.destroy(); chart = null; }
    const ctx = document.getElementById('cv').getContext('2d');
    chart = new Chart(ctx, {
      type: isLine ? 'line' : 'bar',
      data: {
        labels,
        datasets: [{
          data: chartData,
          borderColor: color,
          backgroundColor: isLine ? colorFade : barColors,
          borderWidth: isLine ? 2 : 0,
          borderRadius: isLine ? 0 : 5,
          fill: isLine,
          tension: 0.35,
          pointRadius: isLine ? 4 : 0,
          pointHoverRadius: 6,
          pointBackgroundColor: color,
          spanGaps: true,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 250 },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#21262d',
            borderColor: '#30363d',
            borderWidth: 1,
            titleColor: '#8b949e',
            bodyColor: '#e6edf3',
            callbacks: {
              label: ctx => isNaN(ctx.raw) ? 'No data' : `${ctx.raw} ${isHR ? 'bpm' : '%'}`
            }
          }
        },
        scales: {
          x: {
            ticks: { color: '#8b949e', font: { size: 10 }, maxTicksLimit: range === '7d' ? 7 : (range === '3d' ? 12 : (range === '24h' ? 8 : 12)), maxRotation: 35 },
            grid:  { color: '#1c2128' }
          },
          y: {
            min: isHR ? 40 : (isSP ? 80 : 0),
            max: isHR ? 140 : (isSP ? 101 : 105),
            ticks: { color: '#8b949e', font: { size: 11 } },
            grid:  { color: '#1c2128' }
          }
        }
      }
    });
  }

  // Raw data table
  renderTable(data, isHR);
}

// ── Raw data table ─────────────────────────────────────────────────────────
function renderTable(data, isHR) {
  const tbody = document.getElementById('tbody');
  const title = document.getElementById('tableTitle');
  const labels = data.labels || [];
  const hr     = data.hr    || [];
  const spo2   = data.spo2  || [];
  const bat    = data.battery || [];

  let rows = '';
  const n = labels.length;

  if (n === 0) {
    title.textContent = 'No data';
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#8b949e;padding:16px">No records found for this user/range</td></tr>';
    return;
  }

  title.textContent = `${range === '5m' ? 'Last readings (5m)' : range === '1h' ? '1H buckets (5-min avg)' : range === '24h' ? '24H buckets (hourly avg)' : range === '3d' ? '3D buckets (hourly avg)' : '7D buckets (hourly avg)'}  ·  ${data.count || n} raw records`;

  // Show all rows (max 30 for live, all for 1h/24h)
  const show = range === '5m' ? Math.min(n, 30) : n;
  for (let i = 0; i < show; i++) {
    const hrVal = hr[i];
    const spVal = spo2[i];
    const batVal= bat[i];
    const hrStr = (hrVal != null && hrVal > 0) ? `<span class="val-hr">${hrVal}</span>` : `<span class="val-null">–</span>`;
    const spStr = (spVal != null && spVal > 0) ? `<span class="val-sp">${spVal}</span>` : `<span class="val-null">–</span>`;
    const batStr= (batVal != null && batVal > 0) ? `<span class="val-bat">${batVal}%</span>` : `<span class="val-null">–</span>`;
    rows += `<tr><td>${i}</td><td>${labels[i]}</td><td>${hrStr}</td><td>${spStr}</td><td>${batStr}</td></tr>`;
  }
  tbody.innerHTML = rows;
}

// ── Status helper ──────────────────────────────────────────────────────────
function setStatus(state, count, msg) {
  const el = document.getElementById('status');
  const refreshInfo = { '5m': '10s', '1h': '1min', '24h': '5min', '3d': '10min', '7d': '10min' }[range];
  if (state === 'loading') {
    el.innerHTML = `<span class="spinner"></span>Loading...`;
  } else if (state === 'ok') {
    const t = new Date().toLocaleTimeString('vi-VN');
    el.innerHTML = `<span class="dot dot-g"></span>${t} · ${count} records · auto-refresh ${refreshInfo}`;
  } else {
    el.innerHTML = `<span class="dot dot-r"></span>Error: ${msg}`;
  }
}

init();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    print("=" * 50)
    print(" AIFD Vitals Viewer")
    print(" http://localhost:3000")
    print(" Ctrl+C để dừng")
    print("=" * 50)
    app.run(host="0.0.0.0", port=3000, debug=False, use_reloader=False)
