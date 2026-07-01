import asyncio
import sys
from datetime import datetime

from bleak import BleakClient, BleakScanner


DEVICE_NAME = "ESP32-fall-detection-BLE"
DEVICE_ADDRESS = "A0:F2:62:F1:07:45"
SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
STATUS_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
VITALS_CHAR_UUID = "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1"
CONTROL_CHAR_UUID = "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03"

KNOWN_NOTIFY_CHARS = {
    STATUS_CHAR_UUID: "status",
    VITALS_CHAR_UUID: "vitals",
}

RED = "\033[1;97;41m"
GREEN = "\033[1;97;42m"
BLUE = "\033[1;97;44m"
YELLOW = "\033[1;30;43m"
RESET = "\033[0m"


def now_text() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def decode_payload(data: bytearray) -> str:
    try:
        return bytes(data).decode("utf-8").strip()
    except UnicodeDecodeError:
        return bytes(data).hex()


def split_pipe_values(value: str) -> list[str]:
    return [item.strip() for item in value.split("|")]


def fmt_invalid(value: str) -> str:
    return "NA" if value == "255" else value


def print_banner(title: str, color: str) -> None:
    print(color + f" {title} ".center(88, "=") + RESET)


def print_raw_packet(source: str, payload: str) -> None:
    print(f"[{now_text()}] {BLUE}{source.upper():^8}{RESET} raw={payload}")


def parse_alert_payload(payload: str) -> dict | None:
    parts = [part.strip() for part in payload.split(",")]
    if len(parts) != 7 or parts[0] != "ALERT":
        return None

    return {
        "type": parts[0],
        "sequence": parts[1],
        "timestamp_sec": parts[2],
        "label": parts[3],
        "status_code": parts[4],
        "fall_prob": parts[5],
        "non_fall_prob": parts[6],
    }


def parse_batch_payload(payload: str) -> dict | None:
    parts = [part.strip() for part in payload.split(",")]
    if len(parts) != 5 or parts[0] != "BATCH":
        return None

    hr = split_pipe_values(parts[2])
    spo2 = split_pipe_values(parts[3])
    ts = split_pipe_values(parts[4])
    if len(hr) != 5 or len(spo2) != 5 or len(ts) != 5:
        return None

    samples = []
    for idx in range(5):
        samples.append(
            {
                "index": idx,
                "heart_rate": fmt_invalid(hr[idx]),
                "spo2": fmt_invalid(spo2[idx]),
                "timestamp_sec": ts[idx],
            }
        )

    return {
        "type": parts[0],
        "sequence": parts[1],
        "samples": samples,
    }


def print_alert(parsed: dict) -> None:
    color = RED if parsed["label"].lower() == "fall" else GREEN
    print_banner("ALERT PACKET", color)
    print(
        f"[{now_text()}] seq={parsed['sequence']} uptime_s={parsed['timestamp_sec']} "
        f"label={parsed['label']} status={parsed['status_code']} "
        f"fall_prob={parsed['fall_prob']} non_fall_prob={parsed['non_fall_prob']}"
    )


def print_batch(parsed: dict) -> None:
    print_banner("VITALS BATCH", YELLOW)
    print(f"[{now_text()}] seq={parsed['sequence']} samples={len(parsed['samples'])}")
    for sample in parsed["samples"]:
        print(
            f"  - idx={sample['index']} ts={sample['timestamp_sec']} "
            f"hr={sample['heart_rate']} spo2={sample['spo2']}"
        )


def handle_notification(characteristic_uuid: str, data: bytearray) -> None:
    source = KNOWN_NOTIFY_CHARS.get(characteristic_uuid.lower(), characteristic_uuid)
    payload = decode_payload(data)
    print_raw_packet(source, payload)

    parsed_alert = parse_alert_payload(payload)
    if parsed_alert is not None:
        print_alert(parsed_alert)
        return

    parsed_batch = parse_batch_payload(payload)
    if parsed_batch is not None:
        print_batch(parsed_batch)
        return

    print(f"[{now_text()}] Unparsed payload from {source}: {payload}")


def make_notification_handler(characteristic_uuid: str):
    def _handler(_: int, data: bytearray) -> None:
        try:
            handle_notification(characteristic_uuid, data)
        except Exception as exc:
            print(f"[{now_text()}] Handler error for {characteristic_uuid}: {exc}")

    return _handler


async def find_target_device(target_name: str, target_address: str):
    print("Scanning nearby BLE devices...")
    try:
        devices = await BleakScanner.discover(timeout=10.0)
    except Exception as exc:
        print(f"Discovery error: {exc}")
        return None

    if not devices:
        print("No BLE devices found.")
        return None

    print("\nFound devices:")
    target_device = None
    for device in devices:
        name = device.name or "Unknown"
        print(f"- {name} ({device.address})")

        if device.address.upper() == target_address.upper():
            target_device = device
        elif name.strip() == target_name and target_device is None:
            target_device = device

    if target_device:
        print(f"\nTarget matched: {target_device.name} ({target_device.address})")

    return target_device


async def print_gatt_map(client: BleakClient) -> None:
    print_banner("GATT MAP", BLUE)
    for service in client.services:
        marker = " <target>" if service.uuid.lower() == SERVICE_UUID.lower() else ""
        print(f"Service {service.uuid}{marker}")
        for char in service.characteristics:
            props = ",".join(char.properties)
            name = KNOWN_NOTIFY_CHARS.get(char.uuid.lower(), "")
            suffix = f" [{name}]" if name else ""
            print(f"  - Char {char.uuid}{suffix} props={props}")


async def subscribe_known_characteristics(client: BleakClient) -> None:
    for char_uuid, label in KNOWN_NOTIFY_CHARS.items():
        try:
            await client.start_notify(char_uuid, make_notification_handler(char_uuid))
            print(f"Subscribed to {label}: {char_uuid}")
        except Exception as exc:
            print(f"Failed to subscribe {label} ({char_uuid}): {exc}")


async def send_ready_command(client: BleakClient) -> None:
    payload = b"READY"
    await client.write_gatt_char(CONTROL_CHAR_UUID, payload, response=True)
    print(f"Sent control command: {payload.decode()}")


async def main() -> None:
    device_name = sys.argv[1] if len(sys.argv) > 1 else DEVICE_NAME
    device_address = sys.argv[2] if len(sys.argv) > 2 else DEVICE_ADDRESS

    print(f"Targeting BLE device: {device_name} ({device_address})")

    while True:
        try:
            device = await find_target_device(device_name, device_address)
            if device is None:
                print("Device not found. Retrying in 5s...")
                await asyncio.sleep(5)
                continue

            print(f"Connecting to {device.address}...")
            async with BleakClient(device, timeout=15.0) as client:
                if not client.is_connected:
                    print("Failed to connect.")
                    await asyncio.sleep(1)
                    continue

                print(f"Connected. MTU={client.mtu_size}")
                await print_gatt_map(client)
                await subscribe_known_characteristics(client)
                await send_ready_command(client)
                print("\nNotifications active. Waiting for all ESP32 packets...\n")

                while client.is_connected:
                    await asyncio.sleep(0.5)

                print("Disconnected from device.")

        except Exception as exc:
            print(f"Main loop error: {exc}")
            await asyncio.sleep(2)

        print("Attempting to reconnect...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nUser stopped the client.")
    except Exception as exc:
        print(f"Fatal error: {exc}")
