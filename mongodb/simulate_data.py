import random
import time
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

# =========================
# KẾT NỐI VỚI MONGODB
# =========================
MONGO_URI = "mongodb+srv://dien572:dien562003@cluster0.smq9ywt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DEVICE_ID = "wristband_001"
USER_ID = "elder_001"
INTERVAL_SECONDS = 10

client = MongoClient(MONGO_URI)
db = client["elderly_aiot"]
sensor_col = db["sensor_readings_new"]


# =========================
# TẠO DỮ LIỆU VÀ GỬI VÀO MONGODB
# =========================
def generate_data():
    sample_time = datetime.now(timezone.utc).replace(microsecond=0)
    document = build_sensor_document(sample_time)
    sensor_col.insert_one(document)
    print("Data inserted:", format_log_payload(document))


def build_sensor_document(sample_time):
    heart_rate_value = random.randint(60, 120)
    spo2_value = random.randint(92, 100)

    return {
        "device_id": DEVICE_ID,
        "user_id": USER_ID,
        "timestamp": sample_time,
        "heart_rate": [{"timestamp": sample_time, "value": heart_rate_value}],
        "spo2": [{"timestamp": sample_time, "value": spo2_value}],
        "battery": random.randint(20, 100),
    }


def format_log_payload(document):
    return {
        "timestamp": document["timestamp"].isoformat(),
        "heart_rate": document["heart_rate"][0]["value"],
        "spo2": document["spo2"][0]["value"],
    }


def seed_initial_history():
    if sensor_col.count_documents({}) > 0:
        return

    now = datetime.now(timezone.utc).replace(microsecond=0)
    initial_docs = []
    for offset in range(60, 0, -1):
        sample_time = now - timedelta(seconds=offset * INTERVAL_SECONDS)
        initial_docs.append(build_sensor_document(sample_time))

    sensor_col.insert_many(initial_docs)
    print(f"Seeded {len(initial_docs)} historical samples.")


def main():
    try:
        seed_initial_history()
        while True:
            generate_data()
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("Stopped data simulation.")


if __name__ == "__main__":
    main()
