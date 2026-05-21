import hashlib
import os
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, Response, stream_with_context
from pymongo import MongoClient, DESCENDING
import json
import time

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
