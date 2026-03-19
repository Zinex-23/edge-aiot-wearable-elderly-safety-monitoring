from flask import Flask, jsonify, render_template
from pymongo import MongoClient
import pandas as pd

app = Flask(__name__)

# =========================
# KẾT NỐI VỚI MONGODB
# =========================
MONGO_URI = "mongodb+srv://dien572:dien562003@cluster0.smq9ywt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MAX_DOCUMENTS = 720
DISPLAY_POINTS = 360

client = MongoClient(MONGO_URI)
db = client["elderly_aiot"]
sensor_col = db["sensor_readings_new"]


def flatten_sensor_document(doc):
    rows_by_timestamp = {}

    for field_name in ("heart_rate", "spo2"):
        for sample in doc.get(field_name, []):
            sample_timestamp = sample.get("timestamp") or doc.get("timestamp")
            if sample_timestamp is None:
                continue

            row = rows_by_timestamp.setdefault(
                sample_timestamp,
                {
                    "ingested_at": doc.get("timestamp"),
                    "sample_timestamp": sample_timestamp,
                    "heart_rate": None,
                    "spo2": None,
                },
            )
            row[field_name] = sample.get("value")

    if rows_by_timestamp:
        return list(rows_by_timestamp.values())

    fallback_timestamp = doc.get("timestamp")
    if fallback_timestamp is None:
        return []

    return [
        {
            "ingested_at": fallback_timestamp,
            "sample_timestamp": fallback_timestamp,
            "heart_rate": None,
            "spo2": None,
        }
    ]


def build_payload(df, apply_ingest_alignment_filter):
    working_df = df.copy()

    if apply_ingest_alignment_filter:
        # Loại bỏ các document cũ bị sinh sai timestamp, lệch quá xa thời điểm insert.
        min_valid_time = working_df["ingested_at"] - pd.Timedelta(minutes=15)
        max_valid_time = working_df["ingested_at"] + pd.Timedelta(minutes=1)
        working_df = working_df[
            (working_df["sample_timestamp"] >= min_valid_time)
            & (working_df["sample_timestamp"] <= max_valid_time)
        ]

    if working_df.empty:
        return []

    working_df["timestamp"] = working_df["sample_timestamp"].dt.floor("10s")
    working_df = working_df.sort_values(["timestamp", "ingested_at"])
    working_df = working_df.drop_duplicates(subset=["timestamp"], keep="last")
    working_df = working_df.sort_values("timestamp").tail(DISPLAY_POINTS)
    working_df["timestamp"] = working_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    payload_df = working_df[["timestamp", "heart_rate", "spo2"]]
    payload_df = payload_df.where(pd.notnull(payload_df), None)
    return payload_df.to_dict(orient="records")


# =========================
# LẤY DỮ LIỆU TỪ MONGODB
# =========================
@app.route("/data")
def get_data():
    cursor = sensor_col.find(
        {},
        {"_id": 0, "timestamp": 1, "heart_rate": 1, "spo2": 1},
    ).sort("timestamp", -1).limit(MAX_DOCUMENTS)

    rows = []
    for doc in cursor:
        rows.extend(flatten_sensor_document(doc))

    if not rows:
        return jsonify([])

    df = pd.DataFrame(rows)
    df["ingested_at"] = pd.to_datetime(df["ingested_at"], utc=True, errors="coerce")
    df["sample_timestamp"] = pd.to_datetime(
        df["sample_timestamp"], utc=True, errors="coerce"
    )
    df["heart_rate"] = pd.to_numeric(df["heart_rate"], errors="coerce")
    df["spo2"] = pd.to_numeric(df["spo2"], errors="coerce")

    df = df.dropna(subset=["ingested_at", "sample_timestamp"])
    df = df[df["heart_rate"].notna() | df["spo2"].notna()]

    if df.empty:
        return jsonify([])

    payload = build_payload(df, apply_ingest_alignment_filter=True)
    if not payload:
        payload = build_payload(df, apply_ingest_alignment_filter=False)

    return jsonify(payload)


# =========================
# GIAO DIỆN CHẠY ỨNG DỤNG
# =========================
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
