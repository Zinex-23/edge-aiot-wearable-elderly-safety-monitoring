"""
simulate_vitals_continuous.py — Bắn dữ liệu vitals giả định lên MongoDB để test chart 7 ngày và chạy realtime liên tục.
Tự động XÓA TOÀN BỘ data cũ của userId trước khi insert.

Cách dùng:
    python simulate_vitals_continuous.py                        # fill 7 ngày, mỗi 25 giây, sau đó chạy realtime
    python simulate_vitals_continuous.py --days 7 --interval 5  # fill 7 ngày, mỗi 5 giây
"""

import argparse
import math
import random
import time
from datetime import datetime, timedelta

from pymongo import MongoClient

MONGO_URI  = (
    "mongodb+srv://dien572:dien562003@cluster0.smq9ywt.mongodb.net/"
    "?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME    = "elderly_aiot"
COLLECTION = "vitals"

# ─── Realistic vitals generator ───────────────────────────────────────────────

def circadian_hr(dt: datetime) -> float:
    """
    Nhịp tim theo chu kỳ ngày-đêm (circadian rhythm).
    Ban đêm (02:00) thấp nhất ~58 bpm, ban ngày (14:00) cao nhất ~82 bpm.
    """
    hour = dt.hour + dt.minute / 60.0
    phase = (hour - 2) / 24.0 * 2 * math.pi
    base  = 70 + 12 * math.sin(phase)
    return base


def gen_vitals(dt: datetime, prev_hr: float | None = None) -> tuple[int, int, int]:
    """
    Sinh HR, SpO2 và Battery tại thời điểm dt.
    """
    target = circadian_hr(dt)
    if prev_hr is None:
        hr_float = target + random.gauss(0, 4)
    else:
        hr_float = prev_hr + (target - prev_hr) * 0.05 + random.gauss(0, 1.5)

    hr = int(round(max(52, min(105, hr_float))))

    if random.random() < 0.05:
        spo2 = random.randint(94, 96)
    else:
        spo2 = int(round(max(95, min(99, random.gauss(97.2, 0.8)))))

    # Battery generation: 60-hour cycle (2.5 days) dropping from 100% to varying minimums
    cycle_duration = 60 * 3600
    ts = dt.timestamp()
    cycle_index = int(ts // cycle_duration)
    min_levels = [18, 20, 21, 15, 20]
    current_min = min_levels[cycle_index % len(min_levels)]

    cycle_pos = ts % cycle_duration
    drop_amount = 100 - current_min
    battery = 100 - (cycle_pos / cycle_duration) * drop_amount
    battery = int(round(max(0, min(100, battery + random.uniform(-0.5, 0.5)))))

    return hr, spo2, battery


# ─── Progress bar đơn giản ────────────────────────────────────────────────────

def progress(done: int, total: int, prefix: str = ""):
    pct  = done / total if total > 0 else 1
    bars = int(pct * 30)
    bar  = "█" * bars + "░" * (30 - bars)
    print(f"\r{prefix} [{bar}] {done}/{total} ({pct*100:.0f}%)", end="", flush=True)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Continuous Vitals Simulator (7 days history)")
    parser.add_argument("--userId",   default="dien572",           help="User ID")
    parser.add_argument("--deviceId", default="A0:F2:62:F1:09:E5", help="Device MAC")
    parser.add_argument("--days",     type=float, default=7.0,     help="Số ngày lịch sử cần tạo (mặc định 7)")
    parser.add_argument("--interval", type=int,   default=25,      help="Khoảng cách giữa các bản ghi (giây), mặc định 25s")
    args = parser.parse_args()

    interval_s = args.interval
    total_secs = args.days * 24 * 3600
    total_recs = int(total_secs / interval_s)

    # Thông tin
    print("=" * 55)
    print(" Vitals Continuous Simulator → MongoDB")
    print("=" * 55)
    print(f"  userId    : {args.userId}")
    print(f"  deviceId  : {args.deviceId}")
    print(f"  history   : {args.days} days")
    print(f"  interval  : {interval_s} seconds")
    print(f"  records   : ~{total_recs:,} (history)")
    print("=" * 55)

    # Kết nối
    print("\nConnecting to MongoDB...", end="")
    client = MongoClient(MONGO_URI)
    col    = client[DB_NAME][COLLECTION]
    print(" OK")

    # ── Xóa TOÀN BỘ data của userId trước khi insert (tránh đè/thừa) ──────
    print(f"\nClearing ALL existing data for userId={args.userId}...")
    result = col.delete_many({"userId": args.userId})
    print(f"  Deleted {result.deleted_count} records")

    # ── Tạo timestamps ─────────────────────────────────────────────────────
    now     = datetime.utcnow()
    start   = now - timedelta(seconds=total_secs)

    timestamps = []
    t = start
    while t <= now:
        timestamps.append(t)
        t += timedelta(seconds=interval_s)

    total = len(timestamps)
    print(f"\nGenerating {total:,} historical records from {start.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%Y-%m-%d %H:%M')} UTC")
    print()

    # ── Insert theo batch ──────────────────────────────────────────────────
    BATCH_SIZE = 500
    docs       = []
    prev_hr    = None
    inserted   = 0

    for i, ts in enumerate(timestamps):
        hr, spo2, battery = gen_vitals(ts, prev_hr)
        prev_hr  = hr

        docs.append({
            "userId":    args.userId,
            "deviceId":  args.deviceId,
            "timestamp": ts,
            "heartRate": hr,
            "spo2":      spo2,
            "battery":   battery,
            "temperature":     None,
            "bloodPressure":   {"systolic": None, "diastolic": None},
            "source":          "simulated",
            "createdAt":       ts,
        })

        if len(docs) >= BATCH_SIZE:
            col.insert_many(docs)
            inserted += len(docs)
            docs = []
            progress(inserted, total, "  Inserting history")

    # Flush phần còn lại
    if docs:
        col.insert_many(docs)
        inserted += len(docs)
        progress(inserted, total, "  Inserting history")

    print("\n\nHistory generation complete!")
    
    # ── Summary ────────────────────────────────────────────────────────────
    total_in_db = col.count_documents({"userId": args.userId})

    print()
    print("=" * 55)
    print(" Done Initial Data Fill!")
    print("=" * 55)
    print(f"  Inserted      : {inserted:,} records")
    print(f"  Total in DB   : {total_in_db:,} records (userId={args.userId})")
    print("=" * 55)
    
    print(f"\nNow starting CONTINUOUS REAL-TIME stream (1 record / {interval_s}s)...")
    print("Press Ctrl+C to stop.\n")

    # ── Chạy liên tục (Real-time Stream) ───────────────────────────────────
    try:
        while True:
            time.sleep(interval_s)
            ts = datetime.utcnow()
            hr, spo2, battery = gen_vitals(ts, prev_hr)
            prev_hr = hr

            doc = {
                "userId":    args.userId,
                "deviceId":  args.deviceId,
                "timestamp": ts,
                "heartRate": hr,
                "spo2":      spo2,
                "battery":   battery,
                "temperature":     None,
                "bloodPressure":   {"systolic": None, "diastolic": None},
                "source":          "simulated",
                "createdAt":       ts,
            }
            col.insert_one(doc)
            print(f"[{ts.strftime('%H:%M:%S UTC')}] Sent real-time vitals -> HR: {hr} bpm | SpO2: {spo2}% | Pin: {battery}%")

    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
