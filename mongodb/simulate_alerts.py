import argparse
import random
from datetime import datetime, timedelta

from pymongo import MongoClient

MONGO_URI  = (
    "mongodb+srv://dien572:dien562003@cluster0.smq9ywt.mongodb.net/"
    "?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME    = "elderly_aiot"
COLLECTION = "fall_events"

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Simulate fall alerts → MongoDB")
    parser.add_argument("--userId",   default="dien572",           help="User ID")
    parser.add_argument("--deviceId", default="A0:F2:62:F1:09:E5", help="Device MAC")
    parser.add_argument("--count",    type=int, default=5,         help="Số lượng alert muốn tạo giả (default: 5)")
    args = parser.parse_args()

    # Kết nối
    print("\nConnecting to MongoDB...", end="")
    client = MongoClient(MONGO_URI)
    col    = client[DB_NAME][COLLECTION]
    print(" OK")

    # ── Xóa TOÀN BỘ data của userId trước khi insert (tránh đè/thừa) ──────
    print(f"\nClearing ALL existing alerts for userId={args.userId}...")
    result = col.delete_many({"userId": args.userId})
    print(f"  Deleted {result.deleted_count} alerts")

    # ── Tạo timestamps ─────────────────────────────────────────────────────
    now = datetime.utcnow()
    
    docs = []
    
    # Các loại cảnh báo có thể có
    event_types = ["FALL", "VITALS", "MANUAL_SOS"]
    
    for i in range(args.count):
        # Đổi logic tạo time: do app Android có filter `lastClearedMs`,
        # nếu tạo time trong quá khứ (trước lúc bấm Xóa) thì app sẽ bỏ qua.
        # Do đó ta tạo timestamp = hiện tại + i giây để đảm bảo luôn là "mới nhất"
        ts = now + timedelta(seconds=i * 10)
        
        event_type = random.choice(event_types)
        
        # Nếu là FALL thì có xác suất, nếu không thì None
        fall_prob = round(random.uniform(0.7, 0.99), 2) if event_type == "FALL" else None
        
        # Tạo ngẫu nhiên một số thông báo đã giải quyết, một số chưa
        resolved = random.choice([True, False])
        
        docs.append({
            "deviceId": args.deviceId,
            "userId": args.userId,
            "timestamp": ts,
            "type": event_type,
            "fallProb": fall_prob,
            "resolved": resolved,
            "source": "simulated",
            "createdAt": ts
        })

    # Sắp xếp lại theo thời gian để insert cho đẹp (cũ đến mới)
    docs.sort(key=lambda x: x["timestamp"])

    if docs:
        col.insert_many(docs)

    # ── Summary ────────────────────────────────────────────────────────────
    total_in_db = col.count_documents({"userId": args.userId})
    unresolved_in_db = col.count_documents({"userId": args.userId, "resolved": False})

    print()
    print("=" * 55)
    print(" Done!")
    print("=" * 55)
    print(f"  Inserted      : {len(docs)} alerts")
    print(f"  Total in DB   : {total_in_db} alerts (userId={args.userId})")
    print(f"  Unresolved    : {unresolved_in_db} alerts (Sẽ hiển thị màu đỏ trên App)")
    print()
    print("  Bây giờ mở điện thoại (Role Caregiver) và xem tab Thông báo nhé!")
    print("=" * 55)

    client.close()


if __name__ == "__main__":
    main()
