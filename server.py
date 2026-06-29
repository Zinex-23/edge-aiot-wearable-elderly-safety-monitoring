import hashlib
import os
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, Response, stream_with_context
from pymongo import MongoClient, DESCENDING
import json
import time
import random
import requests

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:
    firebase_admin = None

# =========================
# CONFIG
# =========================
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://dien572:dien562003@cluster0.smq9ywt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME = "elderly_aiot"

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

sensor_col     = db["sensor_readings_new"]
users_col      = db["users"]
vitals_col     = db["vitals"]
fall_events_col = db["fall_events"]

app = Flask(__name__)

# =========================
# FIREBASE INIT
# =========================
try:
    if firebase_admin and not firebase_admin._apps:
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("Firebase Admin initialized successfully.")
        else:
            print("WARNING: serviceAccountKey.json not found. FCM Push Notifications will not work.")
except Exception as e:
    print(f"Failed to initialize Firebase Admin: {e}")


# =========================
# HELPERS
# =========================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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


def serialize_vital(doc):
    if not doc:
        return None
    return {
        "id": str(doc.get("_id", "")),
        "deviceId": doc.get("deviceId", ""),
        "userId": doc.get("userId", ""),
        "timestamp": dt_to_iso(doc.get("timestamp")),
        "heartRate": doc.get("heartRate"),
        "spo2": doc.get("spo2"),
        "temperature": doc.get("temperature"),
        "bloodPressure": doc.get("bloodPressure", {"systolic": None, "diastolic": None}),
        "source": doc.get("source", "ble_edge"),
    }


def serialize_fall_event(doc):
    if not doc:
        return None
    return {
        "id": str(doc.get("_id", "")),
        "deviceId": doc.get("deviceId", ""),
        "userId": doc.get("userId", ""),
        "timestamp": dt_to_iso(doc.get("timestamp")),
        "type": doc.get("type", "fall_auto"),
        "fallProb": doc.get("fallProb"),
        "resolved": doc.get("resolved", False),
    }


def get_latest_doc():
    doc = sensor_col.find_one(sort=[("timestamp", DESCENDING), ("_id", DESCENDING)])
    return serialize_doc(doc)


def get_history(limit=100):
    docs = list(
        sensor_col.find(
            {},
            {"_id": 1, "device_id": 1, "user_id": 1, "timestamp": 1,
             "heart_rate": 1, "spo2": 1, "battery": 1,
             "accel": 1, "gyro": 1, "raw_ppg": 1, "created_at": 1},
        ).sort("timestamp", DESCENDING).limit(limit)
    )
    docs.reverse()
    return [serialize_doc(doc) for doc in docs]


# =========================
# UI (legacy dashboard)
# =========================
@app.route("/", methods=["GET"])
def dashboard():
    return jsonify({"ok": True, "service": "AIFD Cloud API", "version": "2.0"}), 200


# =========================
# CONTROL PANEL & API
# =========================
@app.route("/control", methods=["GET"])
def control_page():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hospicare Device Control</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.5);
            --secondary: #a855f7;
            --success: #10b981;
            --error: #ef4444;
            --bg-dark: #09090b;
            --card-bg: rgba(255, 255, 255, 0.03);
            --card-border: rgba(255, 255, 255, 0.08);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-dark);
            background-image: 
                radial-gradient(circle at 20% 30%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 80% 70%, rgba(168, 85, 247, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 50% 50%, #0f0c1b 0%, #09090b 100%);
            color: #f4f4f5;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }

        /* Decorative Background Elements */
        .glowing-blob {
            position: absolute;
            width: 300px;
            height: 300px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 50%;
            filter: blur(120px);
            opacity: 0.3;
            z-index: 0;
            pointer-events: none;
            animation: float 10s ease-in-out infinite alternate;
        }
        
        .blob-1 { top: 15%; left: 15%; }
        .blob-2 { bottom: 15%; right: 15%; animation-delay: -5s; }

        @keyframes float {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(30px, -20px) scale(1.1); }
        }

        .control-container {
            position: relative;
            z-index: 10;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 40px;
            border-radius: 28px;
            width: 90%;
            max-width: 440px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .header h1 {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #ffffff 0%, #a1a1aa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header p {
            font-size: 14px;
            color: #a1a1aa;
            margin-bottom: 40px;
        }

        /* Pulsing Glow Button */
        .btn-wrapper {
            position: relative;
            display: inline-block;
            margin: 20px auto;
        }

        .control-btn {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            outline: none;
            position: relative;
            z-index: 2;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-shadow: 0 10px 30px var(--primary-glow);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        .control-btn::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            z-index: -1;
            opacity: 0.8;
            transition: all 0.4s ease;
        }

        .control-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 15px 40px rgba(99, 102, 241, 0.7);
        }

        .control-btn:hover::after {
            transform: scale(1.2);
            opacity: 0;
        }

        .control-btn:active {
            transform: scale(0.95);
            box-shadow: 0 5px 15px var(--primary-glow);
        }

        /* Pulse icon */
        .btn-icon {
            font-size: 32px;
            margin-bottom: 8px;
            animation: pulse-icon 2s infinite;
        }

        @keyframes pulse-icon {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }

        /* Pulsing background ripple for active/idle status */
        .ripple {
            position: absolute;
            top: 50%; left: 50%;
            width: 150px; height: 150px;
            margin-left: -75px; margin-top: -75px;
            border-radius: 50%;
            background: var(--primary);
            opacity: 0;
            z-index: 1;
            pointer-events: none;
        }

        .ripple-active {
            animation: ripple-effect 1.5s cubic-bezier(0.1, 0.8, 0.3, 1) infinite;
        }

        @keyframes ripple-effect {
            0% { transform: scale(1); opacity: 0.4; }
            100% { transform: scale(1.6); opacity: 0; }
        }

        /* Status & Feedback Panel */
        .status-panel {
            margin-top: 40px;
            padding: 16px;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
            transition: all 0.3s ease;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 12px;
            background: rgba(99, 102, 241, 0.1);
            color: #818cf8;
            border: 1px solid rgba(99, 102, 241, 0.2);
            transition: all 0.3s ease;
        }

        .status-badge.sending {
            background: rgba(245, 158, 11, 0.1);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.2);
        }

        .status-badge.success {
            background: rgba(16, 185, 129, 0.1);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .status-badge.error {
            background: rgba(239, 68, 68, 0.1);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: currentColor;
            margin-right: 8px;
            display: inline-block;
        }

        .dot-pulse {
            animation: dot-pulse 1.2s infinite ease-in-out;
        }

        @keyframes dot-pulse {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }

        .info-text {
            font-size: 14px;
            color: #a1a1aa;
            line-height: 1.5;
        }

        .highlight-value {
            font-family: monospace;
            font-size: 18px;
            font-weight: 700;
            color: #ffffff;
            margin-top: 4px;
            display: block;
        }

        /* Toast Notification */
        .toast {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: rgba(24, 24, 27, 0.9);
            border: 1px solid var(--card-border);
            padding: 12px 24px;
            border-radius: 12px;
            font-size: 14px;
            z-index: 100;
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            display: flex;
            align-items: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        }

        .toast.show {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }

        .toast-icon {
            margin-right: 8px;
        }
    </style>
</head>
<body>

    <div class="glowing-blob blob-1"></div>
    <div class="glowing-blob blob-2"></div>

    <div class="control-container">
        <div class="header">
            <h1>Hospicare Control</h1>
            <p>Send simulated metrics to Firebase RTDB</p>
        </div>

        <div class="btn-wrapper">
            <div class="ripple ripple-active" id="btn-ripple"></div>
            <button class="control-btn" id="send-btn">
                <span class="btn-icon">⚡</span>
                <span>TRIGGER</span>
            </button>
        </div>

        <div class="status-panel">
            <div class="status-badge" id="status-badge">
                <span class="dot" id="status-dot"></span>
                <span id="status-label">System Ready</span>
            </div>
            <div class="info-text" id="info-text">
                Press the button above to publish a random status value to Firebase.
                <span class="highlight-value" id="value-display">—</span>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">
        <span class="toast-icon"></span>
        <span class="toast-msg"></span>
    </div>

    <script>
        const sendBtn = document.getElementById('send-btn');
        const btnRipple = document.getElementById('btn-ripple');
        const statusBadge = document.getElementById('status-badge');
        const statusDot = document.getElementById('status-dot');
        const statusLabel = document.getElementById('status-label');
        const infoText = document.getElementById('info-text');
        const valueDisplay = document.getElementById('value-display');
        const toast = document.getElementById('toast');
        const toastMsg = toast.querySelector('.toast-msg');
        const toastIcon = toast.querySelector('.toast-icon');

        function showToast(message, isSuccess = true) {
            toastMsg.textContent = message;
            toastIcon.textContent = isSuccess ? '✅' : '❌';
            toast.className = 'toast show';
            setTimeout(() => {
                toast.className = 'toast';
            }, 3000);
        }

        sendBtn.addEventListener('click', async () => {
            sendBtn.disabled = true;
            statusBadge.className = 'status-badge sending';
            statusDot.className = 'dot dot-pulse';
            statusLabel.textContent = 'Sending...';
            btnRipple.classList.remove('ripple-active');
            infoText.innerHTML = 'Updating Firebase Realtime Database...';
            
            try {
                const response = await fetch('/api/control', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                
                if (response.ok && data.ok) {
                    statusBadge.className = 'status-badge success';
                    statusDot.className = 'dot';
                    statusLabel.textContent = 'Success';
                    infoText.innerHTML = `Value successfully pushed to Firebase: <span class="highlight-value">${data.value}</span>`;
                    showToast(`Updated Firebase with status: ${data.value}`, true);
                } else {
                    throw new Error(data.error || 'Server error occurred');
                }
            } catch (error) {
                statusBadge.className = 'status-badge error';
                statusDot.className = 'dot';
                statusLabel.textContent = 'Error';
                infoText.innerHTML = `Failed to send data: <span style="color: var(--error)">${error.message}</span>`;
                showToast(`Error: ${error.message}`, false);
            } finally {
                setTimeout(() => {
                    sendBtn.disabled = false;
                    btnRipple.classList.add('ripple-active');
                }, 1000);
            }
        });
    </script>
</body>
</html>"""
    return Response(html_content, mimetype="text/html"), 200


@app.route("/api/control", methods=["POST"])
def api_control():
    try:
        # Generate a random integer status value
        random_status = random.randint(1, 100)
        
        # Firebase Realtime Database status path REST URL
        firebase_url = "https://hospicare-91930-default-rtdb.asia-southeast1.firebasedatabase.app/status.json"
        
        # Put request to update status node
        response = requests.put(firebase_url, json=random_status, timeout=5)
        
        if response.status_code == 200:
            return jsonify({
                "ok": True,
                "value": random_status
            }), 200
        else:
            return jsonify({
                "ok": False,
                "error": f"Firebase responded with status code {response.status_code}"
            }), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =========================
# HEALTH CHECK
# =========================
@app.route("/api/health", methods=["GET"])
def health():
    try:
        client.admin.command("ping")
        return jsonify({"ok": True, "mongodb": "connected"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =========================
# AUTH
# =========================
@app.route("/api/auth/register", methods=["POST"])
def register():
    try:
        data = request.get_json(force=True)
        username      = (data.get("username") or "").strip()
        password      = data.get("password") or ""
        caregiver_name  = data.get("caregiverName", "")
        wearer_name     = data.get("wearerName", "")
        wearer_age      = data.get("wearerBornYear", data.get("wearerAge", ""))
        wearer_gender   = data.get("wearerGender", "")
        caregiver_phone = data.get("caregiverPhone", "")

        if not username or not password:
            return jsonify({"ok": False, "error": "username and password required"}), 400

        if users_col.find_one({"username": username}):
            return jsonify({"ok": False, "error": "username already exists"}), 409

        doc = {
            "username":       username,
            "passwordHash":   hash_password(password),
            "caregiverName":  caregiver_name,
            "wearerName":     wearer_name,
            "wearerBornYear": wearer_age,
            "wearerGender":   wearer_gender,
            "caregiverPhone": caregiver_phone,
            "createdAt":      datetime.now(timezone.utc).replace(microsecond=0),
        }
        result = users_col.insert_one(doc)

        return jsonify({
            "ok":      True,
            "userId":  username,
            "message": "registered"
        }), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    try:
        data     = request.get_json(force=True)
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""

        if not username or not password:
            return jsonify({"ok": False, "error": "username and password required"}), 400

        user = users_col.find_one({"username": username})
        if not user or user.get("passwordHash") != hash_password(password):
            return jsonify({"ok": False, "error": "invalid credentials"}), 401

        return jsonify({
            "ok":             True,
            "userId":         username,
            "caregiverName":  user.get("caregiverName", ""),
            "wearerName":     user.get("wearerName", ""),
            "wearerBornYear": user.get("wearerBornYear", user.get("wearerAge", "")),
            "wearerGender":   user.get("wearerGender", ""),
            "caregiverPhone": user.get("caregiverPhone", ""),
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/auth/profile", methods=["GET"])
def get_profile():
    try:
        username = request.args.get("username", "").strip()
        if not username:
            return jsonify({"ok": False, "error": "username required"}), 400
        user = users_col.find_one({"username": username})
        if not user:
            return jsonify({"ok": False, "error": "user not found"}), 404
        return jsonify({
            "ok":            True,
            "userId":        username,
            "caregiverName": user.get("caregiverName", ""),
            "wearerName":    user.get("wearerName", ""),
            "wearerBornYear": user.get("wearerBornYear", user.get("wearerAge", "")),
            "wearerGender":  user.get("wearerGender", ""),
            "caregiverPhone": user.get("caregiverPhone", ""),
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/auth/profile", methods=["PUT"])
def update_profile():
    try:
        data     = request.get_json(force=True)
        username = (data.get("username") or "").strip()
        if not username:
            return jsonify({"ok": False, "error": "username required"}), 400
        if not users_col.find_one({"username": username}):
            return jsonify({"ok": False, "error": "user not found"}), 404
        update = {}
        for field in ["caregiverName", "wearerName", "wearerBornYear", "wearerGender", "caregiverPhone"]:
            if field in data:
                update[field] = data[field]
        if update:
            users_col.update_one({"username": username}, {"$set": update})
        return jsonify({"ok": True, "message": "profile updated"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/auth/change-password", methods=["POST"])
def change_password():
    try:
        data         = request.get_json(force=True)
        username     = (data.get("username") or "").strip()
        current_pwd  = data.get("currentPassword") or ""
        new_pwd      = data.get("newPassword") or ""

        if not username or not current_pwd or not new_pwd:
            return jsonify({"ok": False, "error": "username, currentPassword and newPassword required"}), 400

        user = users_col.find_one({"username": username})
        if not user:
            return jsonify({"ok": False, "error": "user not found"}), 404

        if user.get("passwordHash") != hash_password(current_pwd):
            return jsonify({"ok": False, "error": "wrong current password"}), 401

        users_col.update_one(
            {"username": username},
            {"$set": {"passwordHash": hash_password(new_pwd)}}
        )
        return jsonify({"ok": True, "message": "password changed"}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/auth/fcm-token", methods=["POST"])
def update_fcm_token():
    try:
        data      = request.get_json(force=True)
        username  = (data.get("username") or "").strip()
        role      = (data.get("role") or "").strip().upper()
        fcm_token = (data.get("fcmToken") or "").strip()

        if not username or not role or not fcm_token:
            return jsonify({"ok": False, "error": "username, role and fcmToken required"}), 400

        user = users_col.find_one({"username": username})
        if not user:
            return jsonify({"ok": False, "error": "user not found"}), 404

        field_to_update = "wearerFcmToken" if role == "WEARER" else "caregiverFcmToken"
        users_col.update_one({"username": username}, {"$set": {field_to_update: fcm_token}})
        
        return jsonify({"ok": True, "message": f"{role} FCM token updated"}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =========================
# VITALS
# =========================
@app.route("/api/vitals", methods=["POST"])
def post_vitals():
    try:
        data        = request.get_json(force=True)
        device_id   = data.get("deviceId", "unknown")
        user_id     = data.get("userId", "unknown")
        sample_time = parse_timestamp(data.get("timestamp"))

        hr   = data.get("heartRate")
        spo2 = data.get("spo2")

        # Accept None / null for fields the device doesn't measure
        doc = {
            "deviceId":     device_id,
            "userId":       user_id,
            "timestamp":    sample_time,
            "heartRate":    int(hr)   if hr   is not None else None,
            "spo2":         int(spo2) if spo2 is not None else None,
            "temperature":  data.get("temperature"),
            "bloodPressure": {
                "systolic":  data.get("bloodPressure", {}).get("systolic"),
                "diastolic": data.get("bloodPressure", {}).get("diastolic"),
            },
            "source":    data.get("source", "ble_edge"),
            "createdAt": datetime.now(timezone.utc).replace(microsecond=0),
        }
        result = vitals_col.insert_one(doc)

        return jsonify({"ok": True, "insertedId": str(result.inserted_id)}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/vitals", methods=["GET"])
def get_vitals():
    """
    Query parameters:
      userId   — required
      deviceId — optional filter
      range    — "1h" | "24h" (default "1h")
      limit    — max documents for 1h (default 300, max 1000)
    24h range uses hourly aggregation (ignores limit); returns at most 24 hourly buckets.
    """
    try:
        user_id   = request.args.get("userId", "")
        device_id = request.args.get("deviceId", "")
        range_str = request.args.get("range", "1h")
        limit     = int(request.args.get("limit", 300))
        limit     = max(1, min(limit, 1000))

        if not user_id:
            return jsonify({"ok": False, "error": "userId required"}), 400

        now = datetime.now(timezone.utc)

        if range_str == "24h":
            since = now - timedelta(hours=24)
            match_stage = {
                "userId":    user_id,
                "timestamp": {"$gte": since, "$lte": now},
            }
            if device_id:
                match_stage["deviceId"] = device_id

            pipeline = [
                {"$match": match_stage},
                {"$group": {
                    "_id":     {"$dateToString": {"format": "%Y-%m-%dT%H:00:00Z", "date": "$timestamp"}},
                    "avgHR":   {"$avg": "$heartRate"},
                    "avgSpo2": {"$avg": "$spo2"},
                    "count":   {"$sum": 1},
                }},
                {"$sort":  {"_id": 1}},
                {"$limit": 24},
            ]
            buckets = list(vitals_col.aggregate(pipeline))
            items = [
                {
                    "timestamp": b["_id"],
                    "heartRate": round(b["avgHR"])   if b.get("avgHR")   is not None else None,
                    "spo2":      round(b["avgSpo2"]) if b.get("avgSpo2") is not None else None,
                }
                for b in buckets
            ]
            return jsonify({"ok": True, "count": len(items), "items": items}), 200

        else:
            since = now - timedelta(hours=1)
            query = {
                "userId":    user_id,
                "timestamp": {"$gte": since},
            }
            if device_id:
                query["deviceId"] = device_id

            docs = list(
                vitals_col.find(query).sort("timestamp", DESCENDING).limit(limit)
            )
            docs.reverse()

            return jsonify({
                "ok":    True,
                "count": len(docs),
                "items": [serialize_vital(d) for d in docs],
            }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =========================
# FALL EVENTS
# =========================
@app.route("/api/fall_event", methods=["POST"])
def post_fall_event():
    try:
        data        = request.get_json(force=True)
        device_id   = data.get("deviceId", "unknown")
        user_id     = data.get("userId", "unknown")
        sample_time = parse_timestamp(data.get("timestamp"))
        event_type  = data.get("type", "fall_auto")
        fall_prob   = data.get("fallProb")

        doc = {
            "deviceId":  device_id,
            "userId":    user_id,
            "timestamp": sample_time,
            "type":      event_type,
            "fallProb":  float(fall_prob) if fall_prob is not None else None,
            "resolved":  False,
            "createdAt": datetime.now(timezone.utc).replace(microsecond=0),
        }
        result = fall_events_col.insert_one(doc)

        # Trigger FCM Push to Caregiver
        if firebase_admin and firebase_admin._apps:
            user = users_col.find_one({"username": user_id})
            if user and user.get("caregiverFcmToken"):
                try:
                    wearer_name = user.get("wearerName", "Người đeo")
                    title = "CẢNH BÁO TÉ NGÃ!" if event_type == "fall_auto" else "CẢNH BÁO SINH HIỆU!"
                    body = f"{wearer_name} vừa gặp sự cố. Vui lòng kiểm tra ngay!"
                    
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body
                        ),
                        data={
                            "eventId": str(result.inserted_id),
                            "type": event_type,
                            "deviceId": device_id,
                            "timestamp": doc["timestamp"].isoformat()
                        },
                        token=user.get("caregiverFcmToken"),
                    )
                    messaging.send(message)
                except Exception as e:
                    print("FCM Error:", e)

        return jsonify({"ok": True, "insertedId": str(result.inserted_id)}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/fall_events", methods=["GET"])
def get_fall_events():
    try:
        user_id   = request.args.get("userId", "")
        device_id = request.args.get("deviceId", "")
        limit     = int(request.args.get("limit", 50))

        query = {}
        if user_id:
            query["userId"] = user_id
        if device_id:
            query["deviceId"] = device_id

        docs = list(
            fall_events_col.find(query).sort("timestamp", DESCENDING).limit(limit)
        )
        return jsonify({
            "ok":    True,
            "count": len(docs),
            "items": [serialize_fall_event(d) for d in docs],
        }), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/fall_event/acknowledge", methods=["POST"])
def acknowledge_event():
    try:
        data = request.get_json(force=True)
        event_id = data.get("eventId", "")
        user_id = data.get("userId", "")

        from bson.objectid import ObjectId
        if not event_id or not user_id:
            return jsonify({"ok": False, "error": "eventId and userId required"}), 400

        # Update event as resolved
        fall_events_col.update_one({"_id": ObjectId(event_id)}, {"$set": {"resolved": True}})

        # Trigger FCM Push to Wearer
        if firebase_admin and firebase_admin._apps:
            user = users_col.find_one({"username": user_id})
            if user and user.get("wearerFcmToken"):
                try:
                    caregiver_name = user.get("caregiverName", "Người chăm sóc")
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title="Đã nhận được thông báo",
                            body=f"{caregiver_name} đã xác nhận cảnh báo và đang xử lý."
                        ),
                        data={
                            "eventId": event_id,
                            "action": "acknowledged"
                        },
                        token=user.get("wearerFcmToken"),
                    )
                    messaging.send(message)
                except Exception as e:
                    print("FCM Error:", e)

        return jsonify({"ok": True, "message": "Event acknowledged"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =========================
# LEGACY SENSOR API (kept for dashboard compat)
# =========================
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
        data        = request.get_json(force=True)
        sample_time = parse_timestamp(data.get("timestamp"))

        document = {
            "device_id": data.get("device_id", "wristband_001"),
            "user_id":   data.get("user_id", "elder_001"),
            "timestamp": sample_time,
            "heart_rate": [{"timestamp": sample_time, "value": float(data.get("heart_rate_value", 0))}],
            "spo2":       [{"timestamp": sample_time, "value": float(data.get("spo2_value", 0))}],
            "battery":    int(data.get("battery", 0)),
            "accel":  {"x": float(data.get("ax", 0)), "y": float(data.get("ay", 0)), "z": float(data.get("az", 0))},
            "gyro":   {"x": float(data.get("gx", 0)), "y": float(data.get("gy", 0)), "z": float(data.get("gz", 0))},
            "raw_ppg":    {"ir": int(data.get("ir", 0)), "red": int(data.get("red", 0))},
            "created_at": datetime.now(timezone.utc).replace(microsecond=0),
        }
        result = sensor_col.insert_one(document)
        return jsonify({"ok": True, "inserted_id": str(result.inserted_id)}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# =========================
# SSE REALTIME (legacy)
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
                        payload = {"type": "new_data", "item": serialize_doc(latest)}
                        yield f"data: {json.dumps(payload)}\n\n"
                    else:
                        yield ": keep-alive\n\n"
                time.sleep(0.2)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                time.sleep(1)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
