"""
fetch_compare.py — Lấy vitals từ MongoDB, áp dụng đúng logic bucketing của app Android,
xuất file để so sánh với log app.

Cách dùng:
    python fetch_compare.py                          # lấy 24h, user mặc định
    python fetch_compare.py --userId dien562003      # chỉ định user
    python fetch_compare.py --range 1h               # chỉ lấy 1h gần nhất
    python fetch_compare.py --userId dien562003 --range 24h --out result.txt
"""

import argparse
import math
import sys
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING

# ─── Kết nối MongoDB (cùng URI với server.py) ─────────────────────────────────
MONGO_URI = (
    "mongodb+srv://dien572:dien562003@cluster0.smq9ywt.mongodb.net/"
    "?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME    = "elderly_aiot"
COLLECTION = "vitals"

# ─── Hàm tiện ích ─────────────────────────────────────────────────────────────

def iso(dt: datetime) -> str:
    """Datetime → ISO 8601 UTC string (match Android isoFmt)"""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime | None:
    """ISO 8601 UTC string → datetime (returns None nếu lỗi)"""
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def dt_to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


# ─── Bucket logic — GIỐNG HỆT Android MonitoringViewModel.bucketCloud() ──────
# Slot 0 = oldest, slot [slotCount-1] = newest. Empty slots = 0.

def bucket_cloud(items: list[dict], slot_count: int, slot_ms: int) -> tuple[list[int], list[int]]:
    """
    Nhận danh sách raw vitals (dict với keys 'timestamp', 'heartRate', 'spo2').
    Trả về (hr_buckets, spo2_buckets) — mỗi list có slot_count phần tử.
    Phần tử = 0 nghĩa là không có data trong slot đó.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    # Căn theo boundary giống Android: currentSlot = (now / slotMs) * slotMs
    current_slot = (now_ms // slot_ms) * slot_ms
    oldest_slot  = current_slot - (slot_count - 1) * slot_ms

    hr_sum   = [0] * slot_count
    hr_count = [0] * slot_count
    sp_sum   = [0] * slot_count
    sp_count = [0] * slot_count

    skipped = 0
    for item in items:
        ts_str = item.get("timestamp", "")
        dt = parse_iso(ts_str) if isinstance(ts_str, str) else None
        if dt is None:
            skipped += 1
            continue
        ts_ms = dt_to_ms(dt)

        if ts_ms < oldest_slot or ts_ms > current_slot + slot_ms:
            skipped += 1
            continue

        idx = int((ts_ms - oldest_slot) / slot_ms)
        idx = max(0, min(idx, slot_count - 1))

        hr = item.get("heartRate")
        sp = item.get("spo2")

        if hr is not None and hr > 0:
            hr_sum[idx]   += hr
            hr_count[idx] += 1
        if sp is not None and sp > 0:
            sp_sum[idx]   += sp
            sp_count[idx] += 1

    hr_out  = [hr_sum[i]  // hr_count[i]  if hr_count[i]  > 0 else 0 for i in range(slot_count)]
    spo2_out = [sp_sum[i] // sp_count[i]  if sp_count[i]  > 0 else 0 for i in range(slot_count)]

    print(f"  [bucket_cloud] skipped {skipped} item(s) outside window or bad timestamp")
    return hr_out, spo2_out


# ─── Server-side hourly aggregation — GIỐNG server.py mới ────────────────────

def hourly_aggregate(collection, user_id: str, now: datetime) -> list[dict]:
    """
    MongoDB aggregation: group by hour, trả về list dict
    {'timestamp': '2026-05-20T14:00:00Z', 'heartRate': int|None, 'spo2': int|None}
    Đây là path 24h trong server.py mới — kết quả này app sẽ nhận được.
    """
    since = now - timedelta(hours=24)
    pipeline = [
        {"$match": {"userId": user_id, "timestamp": {"$gte": since, "$lte": now}}},
        {"$group": {
            "_id":     {"$dateToString": {"format": "%Y-%m-%dT%H:00:00Z", "date": "$timestamp"}},
            "avgHR":   {"$avg": "$heartRate"},
            "avgSpo2": {"$avg": "$spo2"},
            "count":   {"$sum": 1},
        }},
        {"$sort":  {"_id": 1}},
        {"$limit": 24},
    ]
    results = list(collection.aggregate(pipeline))
    return [
        {
            "timestamp": r["_id"],
            "heartRate": round(r["avgHR"])   if r.get("avgHR")   is not None else None,
            "spo2":      round(r["avgSpo2"]) if r.get("avgSpo2") is not None else None,
            "_raw_count": r["count"],
        }
        for r in results
    ]


# ─── Fetch raw vitals từ MongoDB ──────────────────────────────────────────────

def fetch_raw(collection, user_id: str, hours: int, limit: int = 5000) -> list[dict]:
    """Lấy TẤT CẢ records trong khoảng giờ, không giới hạn 300."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    docs = list(
        collection.find(
            {"userId": user_id, "timestamp": {"$gte": since}},
            {"_id": 0, "userId": 0, "deviceId": 0}
        ).sort("timestamp", ASCENDING).limit(limit)
    )
    items = []
    for d in docs:
        ts = d.get("timestamp")
        items.append({
            "timestamp": iso(ts) if isinstance(ts, datetime) else str(ts),
            "heartRate": d.get("heartRate"),
            "spo2":      d.get("spo2"),
        })
    return items


# ─── Format slot label ────────────────────────────────────────────────────────

def slot_label(slot_index: int, slot_count: int, slot_ms: int) -> str:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    current_slot = (now_ms // slot_ms) * slot_ms
    oldest_slot  = current_slot - (slot_count - 1) * slot_ms
    slot_start_ms = oldest_slot + slot_index * slot_ms
    dt = ms_to_dt(slot_start_ms)
    if slot_ms == 5 * 60_000:
        return dt.strftime("%H:%M")       # e.g. "14:35"
    else:
        return dt.strftime("%m/%d %H:00") # e.g. "05/20 14:00"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch vitals from MongoDB and compare with app bucketing")
    parser.add_argument("--userId",  default="",     help="User ID (auto-detect nếu bỏ trống)")
    parser.add_argument("--range",   default="24h",  choices=["1h", "24h"], help="Time range (default: 24h)")
    parser.add_argument("--out",     default="",     help="Output file path (default: auto-named)")
    parser.add_argument("--full",    action="store_true", help="In toàn bộ raw records (không ẩn records ở giữa)")
    args = parser.parse_args()

    # Kết nối sớm để auto-detect userId nếu cần
    print(f"Connecting to MongoDB...")
    client_early = MongoClient(MONGO_URI)
    col_early    = client_early[DB_NAME][COLLECTION]
    available_users = col_early.distinct("userId")
    client_early.close()

    if args.userId:
        user_id = args.userId
    elif len(available_users) == 1:
        user_id = available_users[0]
        print(f"  Auto-detected userId: {user_id}")
    elif len(available_users) > 1:
        print(f"  Có nhiều userId trong DB: {available_users}")
        print(f"  Dùng --userId <id> để chỉ định. Tạm dùng: {available_users[-1]}")
        user_id = available_users[-1]
    else:
        print("  ⚠  Không tìm thấy userId nào trong collection vitals!")
        sys.exit(1)
    range_str = args.range
    now_utc   = datetime.now(timezone.utc)

    # Tên file output tự động
    out_file = args.out or f"compare_{user_id}_{range_str}_{now_utc.strftime('%Y%m%d_%H%M%S')}.txt"

    # Kết nối MongoDB
    client = MongoClient(MONGO_URI)
    col    = client[DB_NAME][COLLECTION]
    print(f"  DB={DB_NAME}  collection={COLLECTION}  userId={user_id}  range={range_str}")
    print(f"  All userIds in DB: {available_users}")
    print(f"  Now (UTC): {iso(now_utc)}")
    print()

    lines = []  # Tất cả output ghi vào đây rồi dump ra file

    def w(*args_):
        s = " ".join(str(a) for a in args_)
        print(s)
        lines.append(s)

    w("=" * 70)
    w(f"FETCH & COMPARE REPORT")
    w(f"userId = {user_id}   range = {range_str}   now(UTC) = {iso(now_utc)}")
    w("=" * 70)

    # ── 1. RAW DATA từ MongoDB ─────────────────────────────────────────────
    hours = 24 if range_str == "24h" else 1
    w()
    w(f"[1] RAW DATA — last {hours}h from MongoDB (no limit)")
    w("-" * 70)

    raw_items = fetch_raw(col, user_id, hours)
    w(f"Total records in last {hours}h: {len(raw_items)}")

    if raw_items:
        oldest = raw_items[0]
        newest = raw_items[-1]
        w(f"Oldest record : ts={oldest['timestamp']}  HR={oldest['heartRate']}  SpO2={oldest['spo2']}")
        w(f"Newest record : ts={newest['timestamp']}  HR={newest['heartRate']}  SpO2={newest['spo2']}")

        # Tính range thực tế
        t0 = parse_iso(oldest["timestamp"])
        t1 = parse_iso(newest["timestamp"])
        if t0 and t1:
            span_min = (t1 - t0).total_seconds() / 60
            w(f"Data span     : {span_min:.1f} minutes = {span_min/60:.2f} hours")

        # Đếm valid HR / SpO2
        valid_hr   = sum(1 for x in raw_items if x["heartRate"] and x["heartRate"] > 0)
        valid_spo2 = sum(1 for x in raw_items if x["spo2"] and x["spo2"] > 0)
        w(f"Valid HR      : {valid_hr}/{len(raw_items)}")
        w(f"Valid SpO2    : {valid_spo2}/{len(raw_items)}")

        # HR stats
        hr_vals = [x["heartRate"] for x in raw_items if x["heartRate"] and x["heartRate"] > 0]
        if hr_vals:
            w(f"HR stats      : min={min(hr_vals)}  max={max(hr_vals)}  avg={sum(hr_vals)/len(hr_vals):.1f}")
        sp_vals = [x["spo2"] for x in raw_items if x["spo2"] and x["spo2"] > 0]
        if sp_vals:
            w(f"SpO2 stats    : min={min(sp_vals)}  max={max(sp_vals)}  avg={sum(sp_vals)/len(sp_vals):.1f}")
    else:
        w("  (no records found)")

    # ── 2. SERVER-SIDE AGGREGATION (đây là dữ liệu app nhận) ──────────────
    w()
    w(f"[2] SERVER-SIDE AGGREGATION (cái server.py mới trả về — app sẽ nhận đúng cái này)")
    w("-" * 70)

    if range_str == "24h":
        agg_items = hourly_aggregate(col, user_id, now_utc)
        w(f"Hourly buckets with data: {len(agg_items)} / 24")
        w()
        w(f"{'Giờ UTC':<22} {'HR (avg)':>10} {'SpO2 (avg)':>12} {'n records':>10}")
        w("-" * 60)
        for item in agg_items:
            hr_str   = str(item["heartRate"])   if item["heartRate"]  is not None else "–"
            sp_str   = str(item["spo2"])         if item["spo2"]       is not None else "–"
            w(f"  {item['timestamp']:<20} {hr_str:>10} {sp_str:>12} {item['_raw_count']:>10}")
    else:
        # 1h: server trả về raw 300 records mới nhất, app tự bucket
        since_1h = now_utc - timedelta(hours=1)
        docs_1h  = list(
            col.find(
                {"userId": user_id, "timestamp": {"$gte": since_1h}},
                {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(300)
        )
        docs_1h.reverse()
        agg_items = [
            {
                "timestamp": iso(d["timestamp"]) if isinstance(d["timestamp"], datetime) else str(d["timestamp"]),
                "heartRate": d.get("heartRate"),
                "spo2":      d.get("spo2"),
            }
            for d in docs_1h
        ]
        w(f"Records returned (1h, limit=300): {len(agg_items)}")

    # ── 3. CLIENT-SIDE BUCKETING — GIỐNG HỆT Android bucketCloud() ────────
    w()
    w(f"[3] CLIENT-SIDE BUCKETING — áp dụng đúng logic Android bucketCloud()")
    w("-" * 70)

    if range_str == "24h":
        slot_count = 24
        slot_ms    = 60 * 60_000          # 1 hour
        w(f"Input: {len(agg_items)} aggregated hourly items  →  24 slots × 1h each")
        hr_buckets, spo2_buckets = bucket_cloud(agg_items, slot_count, slot_ms)
    else:
        slot_count = 12
        slot_ms    = 5 * 60_000           # 5 minutes
        w(f"Input: {len(agg_items)} raw items  →  12 slots × 5min each")
        hr_buckets, spo2_buckets = bucket_cloud(agg_items, slot_count, slot_ms)

    filled_hr   = sum(1 for x in hr_buckets   if x > 0)
    filled_spo2 = sum(1 for x in spo2_buckets if x > 0)
    w(f"HR   filled : {filled_hr}/{slot_count}")
    w(f"SpO2 filled : {filled_spo2}/{slot_count}")
    w()

    # Bảng slot-by-slot
    w(f"{'Slot':<6} {'Label':<18} {'HR':>6} {'SpO2':>6}  {'Chart bar'}")
    w("-" * 60)
    for i in range(slot_count):
        label    = slot_label(i, slot_count, slot_ms)
        hr_val   = hr_buckets[i]
        sp_val   = spo2_buckets[i]
        hr_bar   = ("█" * min(20, hr_val // 4)) if hr_val > 0 else "·"
        sp_bar   = ("░" * min(20, sp_val // 5)) if sp_val > 0 else "·"
        hr_str   = str(hr_val)  if hr_val  > 0 else "–"
        sp_str   = str(sp_val)  if sp_val  > 0 else "–"
        w(f"  [{i:02d}] {label:<18} {hr_str:>6} {sp_str:>6}  HR={hr_bar}")

    # ── 4. SUMMARY ────────────────────────────────────────────────────────
    w()
    w("=" * 70)
    w("[4] SUMMARY — đối chiếu Python vs app")
    w("=" * 70)
    w(f"Total raw records (MongoDB, last {hours}h) : {len(raw_items)}")
    if range_str == "24h":
        w(f"Hourly aggregates from server          : {len(agg_items)}")
        w(f"24h chart — HR   buckets filled        : {filled_hr}/24")
        w(f"24h chart — SpO2 buckets filled        : {filled_spo2}/24")
        if filled_hr == 0 and len(raw_items) > 0:
            w("  ⚠  Records exist but no bucket filled — có thể do timezone mismatch hoặc timestamp lỗi")
        elif filled_hr < len(agg_items):
            w("  ⚠  Một số agg items không map được vào bucket — xem slot table ở trên")
        else:
            w("  ✓  Tất cả agg items đã map đúng vào bucket")
    else:
        w(f"1h chart  — HR   buckets filled        : {filled_hr}/12")
        w(f"1h chart  — SpO2 buckets filled        : {filled_spo2}/12")

    w()
    w("Cách so sánh với app log:")
    w("  Tìm trong app logcat: 'fetchCloudVitals[24h]: N raw → 24 buckets (hr filled=X/24'")
    w("  Tìm trong app logcat: 'oldest ts=..., newest ts=...'")
    w("  Số 'hr filled' trong log app phải BẰNG filled_hr của Python script này")
    w("  Nếu khác nhau → gửi log app + file này để debug thêm")
    w()

    # ── 5. RAW TABLE ──────────────────────────────────────────────────────
    if raw_items:
        show_full = args.full
        title = "[5] RAW DATA — TẤT CẢ records" if show_full else "[5] RAW DATA SAMPLE — 10 đầu + 10 cuối  (dùng --full để xem hết)"
        w("=" * 70)
        w(title)
        w("=" * 70)
        w(f"{'#':<6} {'timestamp':<24} {'HR':>6} {'SpO2':>6}")
        w("-" * 50)

        if show_full:
            display = list(enumerate(raw_items))
        else:
            head = list(enumerate(raw_items[:10]))
            tail = list(enumerate(raw_items[-10:], start=len(raw_items) - 10))
            display = head + [(-1, "---")] + tail

        for idx, item in display:
            if item == "---":
                w(f"  ... ({len(raw_items) - 20} records ở giữa — chạy với --full để xem) ...")
                continue
            hr_s = str(item["heartRate"]) if item["heartRate"] is not None else "null"
            sp_s = str(item["spo2"])      if item["spo2"]      is not None else "null"
            w(f"  [{idx:04d}] {item['timestamp']:<24} {hr_s:>6} {sp_s:>6}")

    # Ghi file
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print()
    print(f"✓ Đã ghi kết quả ra: {out_file}")
    client.close()


if __name__ == "__main__":
    main()
