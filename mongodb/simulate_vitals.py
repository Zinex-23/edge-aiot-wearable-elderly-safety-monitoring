"""
simulate_vitals.py — Bắn dữ liệu vitals giả định lên MongoDB để test chart.
Tự động XÓA TOÀN BỘ data cũ của userId trước khi insert (tránh chồng/thừa data).

Cách dùng:
    python simulate_vitals.py                        # fill 24h, mỗi 1 phút (1440 records)
    python simulate_vitals.py --mode quick           # fill 24h, mỗi 5 phút (288 records)
    python simulate_vitals.py --mode normal          # fill 24h, mỗi 1 phút (1440 records)
    python simulate_vitals.py --mode dense           # fill 24h, mỗi 25 giây (3456 records, giống thiết bị thật)
    python simulate_vitals.py --hours 1              # chỉ fill 1h gần nhất
    python simulate_vitals.py --live                 # chỉ fill 10 phút gần nhất (cho live chart)
    python simulate_vitals.py --userId dien572 --mode dense
"""

import argparse
import math
import random
from datetime import datetime, timedelta

from pymongo import MongoClient

MONGO_URI  = (
    "mongodb+srv://dien572:dien562003@cluster0.smq9ywt.mongodb.net/"
    "?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME    = "elderly_aiot"
COLLECTION = "vitals"

# Interval presets (giây)
INTERVALS = {
    "quick":  5 * 60,   # 1 record / 5 phút  → 288 records / 24h
    "normal": 60,        # 1 record / 1 phút  → 1440 records / 24h
    "dense":  25,        # 1 record / 25 giây → 3456 records / 24h  (giống thiết bị thật)
}

# ─── Realistic vitals generator ───────────────────────────────────────────────

def circadian_hr(dt: datetime) -> float:
    """
    Nhịp tim theo chu kỳ ngày-đêm (circadian rhythm).
    Ban đêm (02:00) thấp nhất ~58 bpm, ban ngày (14:00) cao nhất ~82 bpm.
    """
    hour = dt.hour + dt.minute / 60.0
    # Sóng sin: min lúc 02:00, max lúc 14:00
    phase = (hour - 2) / 24.0 * 2 * math.pi
    base  = 70 + 12 * math.sin(phase)
    return base


def gen_vitals(dt: datetime, prev_hr: float | None = None) -> tuple[int, int]:
    """
    Sinh HR và SpO2 tại thời điểm dt.
    - HR: circadian rhythm + random walk ± nhỏ
    - SpO2: ổn định 96-99%, thỉnh thoảng dip nhẹ
    """
    # ── Heart Rate ────────────────────────────────────────────────────────
    target = circadian_hr(dt)
    if prev_hr is None:
        hr_float = target + random.gauss(0, 4)
    else:
        # Random walk: kéo dần về target, bước ±1.5 bpm
        hr_float = prev_hr + (target - prev_hr) * 0.05 + random.gauss(0, 1.5)

    # Kẹp trong khoảng sinh lý bình thường
    hr = int(round(max(52, min(105, hr_float))))

    # ── SpO2 ──────────────────────────────────────────────────────────────
    # 97% base, dao động ±1.5%, dip ngẫu nhiên (5% khả năng xuống 94-96%)
    if random.random() < 0.05:
        spo2 = random.randint(94, 96)
    else:
        spo2 = int(round(max(95, min(99, random.gauss(97.2, 0.8)))))

    return hr, spo2


# ─── Progress bar đơn giản ────────────────────────────────────────────────────

def progress(done: int, total: int, prefix: str = ""):
    pct  = done / total
    bars = int(pct * 30)
    bar  = "█" * bars + "░" * (30 - bars)
    print(f"\r{prefix} [{bar}] {done}/{total} ({pct*100:.0f}%)", end="", flush=True)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Simulate vitals data → MongoDB")
    parser.add_argument("--userId",   default="dien572",           help="User ID")
    parser.add_argument("--deviceId", default="A0:F2:62:F1:09:E5", help="Device MAC")
    parser.add_argument("--mode",     default="normal", choices=["quick", "normal", "dense"])
    parser.add_argument("--hours",    type=float, default=24.0,    help="Số giờ cần fill (default: 24)")
    parser.add_argument("--live",     action="store_true",         help="Chỉ fill 10 phút gần nhất (live chart)")
    args = parser.parse_args()

    interval_s = INTERVALS[args.mode]
    hours      = 10 / 60.0 if args.live else args.hours  # live = 10 phút
    total_secs = hours * 3600
    total_recs = int(total_secs / interval_s)

    # Thông tin
    print("=" * 55)
    print(" Vitals Simulator → MongoDB")
    print("=" * 55)
    print(f"  userId    : {args.userId}")
    print(f"  deviceId  : {args.deviceId}")
    print(f"  mode      : {args.mode}  ({interval_s}s interval)")
    print(f"  fill      : last {'10 min' if args.live else f'{hours:.0f}h'}")
    print(f"  records   : ~{total_recs:,}")
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
    # Naive UTC (giống schema hiện tại trong DB)
    now     = datetime.utcnow()
    start   = now - timedelta(seconds=total_secs)

    # Sinh tất cả timestamps
    timestamps = []
    t = start
    while t <= now:
        timestamps.append(t)
        t += timedelta(seconds=interval_s)

    total = len(timestamps)
    print(f"\nGenerating {total:,} records from {start.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%Y-%m-%d %H:%M')} UTC")
    print()

    # ── Insert theo batch ──────────────────────────────────────────────────
    BATCH_SIZE = 200
    docs       = []
    prev_hr    = None
    inserted   = 0

    for i, ts in enumerate(timestamps):
        hr, spo2 = gen_vitals(ts, prev_hr)
        prev_hr  = hr

        docs.append({
            "userId":    args.userId,
            "deviceId":  args.deviceId,
            "timestamp": ts,
            "heartRate": hr,
            "spo2":      spo2,
            "temperature":     None,
            "bloodPressure":   {"systolic": None, "diastolic": None},
            "source":          "simulated",   # flag để dễ xóa sau
            "createdAt":       ts,
        })

        if len(docs) >= BATCH_SIZE:
            col.insert_many(docs)
            inserted += len(docs)
            docs = []
            progress(inserted, total, "  Inserting")

    # Flush phần còn lại
    if docs:
        col.insert_many(docs)
        inserted += len(docs)
        progress(inserted, total, "  Inserting")

    print()  # newline sau progress bar

    # ── Summary ────────────────────────────────────────────────────────────
    total_in_db = col.count_documents({"userId": args.userId})

    print()
    print("=" * 55)
    print(" Done!")
    print("=" * 55)
    print(f"  Inserted      : {inserted:,} records")
    print(f"  Total in DB   : {total_in_db:,} records (userId={args.userId})")
    print()
    print("  Bây giờ mở http://localhost:3000 → 24H để xem chart đầy")
    print("=" * 55)

    client.close()


if __name__ == "__main__":
    main()
