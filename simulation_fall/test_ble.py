import asyncio
from bleak import BleakScanner

async def main():
    print("--- BLE Scanner Test ---")
    try:
        # return_adv=True để lấy được RSSI chính xác
        devices_adv = await BleakScanner.discover(timeout=5.0, return_adv=True)
        print(f"Found {len(devices_adv)} devices:")
        for addr, (d, adv) in devices_adv.items():
            print(f"  - {d.name or 'Unknown'}: {d.address} (RSSI: {adv.rssi})")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")
    print("--- Test Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
