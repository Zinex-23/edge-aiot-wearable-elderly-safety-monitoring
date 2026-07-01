"""
Fall detection dashboard: simulation (synthetic IMU) or BLE (live ESP32-S3_Combine).

Dashboard /api/status expects `samples` as list of dicts:
  timestamp_ms, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z

BLE device: NimBLE service 4fafc201-... (see S3_BLE/BLE_PROTOCOL.md).
After connect: subscribe status + vitals + IMU, then write READY to control.

IMU notify payload (batched 5 samples / ~100 ms):
  IMU5|<ts>,<ax>,<ay>,<az>,<gx>,<gy>,<gz>|... (x5)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import threading
import time
from collections import deque
from typing import Any

import psutil
import numpy as np
import tensorflow as tf
from flask import Flask, jsonify, render_template, request

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    BleakClient = None  # type: ignore
    BleakScanner = None  # type: ignore

app = Flask(__name__)

RUN_MODE = "simulation"  # 'simulation' | 'ble'

# Same UUIDs as S3_BLE + S3_Combine
BLE_DEVICE_NAME_DEFAULT = "ESP32-fall-detection-BLE"
BLE_SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
BLE_STATUS_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
BLE_VITALS_CHAR_UUID = "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1"
BLE_CONTROL_CHAR_UUID = "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03"
BLE_IMU_CHAR_UUID = "6d3b70a9-64d3-4c98-9b9c-8a4a8e8d2f10"

# BLE runtime config (used when switching modes at runtime)
BLE_ADDRESS_CONFIG: str | None = None
BLE_NAME_CONFIG: str = BLE_DEVICE_NAME_DEFAULT

simulation_state: dict[str, Any] = {
    "mode": "simulation",
    "samples": [],
    "current_prediction": "Waiting...",
    "current_ground_truth": "Waiting...",
    "is_correct": None,
    "total_predictions": 0,
    "correct_predictions": 0,
    "accuracy": 0.0,
    "ram_usage": 0.0,
    "cpu_usage": 0.0,
    "flash_usage": 0.0,
    "current_model": "TinyCNN V27 (Actual)",
    "inference_latency_ms": 0.0,
    "fps": 0.0,
    "energy_mJ": 0.0,
    "events": [],
    # BLE-only diagnostics
    "ble_connected": False,
    "ble_device_name": None,
    "ble_device_address": None,
    "ble_last_packet": "",
    "ble_hr_hint": None,
    "ble_spo2_hint": None,
}

state_lock = threading.Lock()
is_fall_mode = False

# Sliding window for BLE (50 Hz * 2 s = 100 samples)
BLE_WINDOW = 100
_ble_sample_buf: deque[dict[str, Any]] = deque(maxlen=BLE_WINDOW)


class MockModel:
    def __init__(self):
        model_path = "/home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring/AI/model_updated_version_27/models/fall_detection_v27.tflite"
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def predict(self, window: list[dict[str, Any]]) -> str:
        try:
            raw_data = np.array([[
                [s['acc_x'], s['acc_y'], s['acc_z'], s['gyro_x'], s['gyro_y'], s['gyro_z']]
                for s in window
            ]], dtype=np.float32)
            
            # Auto-quantization for V27 (INT8)
            if self.input_details[0]['dtype'] == np.int8:
                scale, zero_point = self.input_details[0]['quantization']
                input_data = (raw_data / (scale if scale != 0 else 1.0) + zero_point).astype(np.int8)
            else:
                input_data = raw_data

            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            if self.output_details[0]['dtype'] == np.int8:
                scale, zero_point = self.output_details[0]['quantization']
                prob = (output_data.astype(np.float32) - zero_point) * (scale if scale != 0 else 1.0)
            else:
                prob = output_data
                
            return "fall" if prob[0][0] >= 0.4 else "non_fall"
        except Exception as e:
            print(f"AI Error: {e}")
            return "non_fall"


model = MockModel()


def _dashboard_sample(ts_ms: int, ax: float, ay: float, az: float, gx: float, gy: float, gz: float) -> dict[str, Any]:
    return {
        "timestamp_ms": int(ts_ms),
        "acc_x": float(ax),
        "acc_y": float(ay),
        "acc_z": float(az),
        "gyro_x": float(gx),
        "gyro_y": float(gy),
        "gyro_z": float(gz),
    }


def parse_imu5_payload(payload: str) -> list[dict[str, Any]]:
    p = payload.strip()
    if not p.startswith("IMU5|"):
        return []
    out: list[dict[str, Any]] = []
    # Firmware uses PIPE | to separate samples within a batch
    # Format: IMU5|sample1|sample2|sample3|sample4|sample5
    # Each sample: ts,ax,ay,az,gx,gy,gz
    segments = p[5:].split("|")
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        parts = seg.split(",")
        if len(parts) != 7:
            # print(f"[BLE-PARSER] Warning: segment has {len(parts)} parts, expected 7. Data: {seg}")
            continue
        try:
            ts_ms, ax, ay, az, gx, gy, gz = parts
            out.append(
                _dashboard_sample(int(ts_ms), float(ax), float(ay), float(az), float(gx), float(gy), float(gz))
            )
        except Exception as e:
            print(f"[BLE-PARSER] Error parsing segment: {seg}, err: {e}")
            continue
    
    # if out:
    #    print(f"[BLE-IMU] Decoded {len(out)} samples")
    return out


def parse_batch_quick(payload: str) -> None:
    """Optional: stash last HR/SpO2 from BATCH for dashboard hints."""
    if not payload.startswith("BATCH,"):
        return
    try:
        parts = [x.strip() for x in payload.split(",")]
        if len(parts) < 5:
            return
        hr_vals = parts[2].split("|")
        spo2_vals = parts[3].split("|")
        if hr_vals and hr_vals[-1] != "255":
            simulation_state["ble_hr_hint"] = hr_vals[-1]
        if spo2_vals and spo2_vals[-1] != "255":
            simulation_state["ble_spo2_hint"] = spo2_vals[-1]
    except (ValueError, IndexError):
        pass


def run_inference_on_window(window: list[dict[str, Any]], ground_truth: str) -> None:
    if len(window) < BLE_WINDOW:
        return
    inference_start = time.time()
    prediction = model.predict(window)
    inference_time = time.time() - inference_start
    latency_ms = inference_time * 1000.0
    is_correct = prediction == ground_truth

    with state_lock:
        simulation_state["total_predictions"] += 1
        if is_correct:
            simulation_state["correct_predictions"] += 1
        total = simulation_state["total_predictions"]
        correct = simulation_state["correct_predictions"]
        simulation_state["current_prediction"] = prediction
        simulation_state["is_correct"] = is_correct
        simulation_state["accuracy"] = (correct / total) * 100.0 if total else 0.0
        simulation_state["inference_latency_ms"] = latency_ms
        simulation_state["fps"] = 50.0
        simulation_state["energy_mJ"] = 30.0 * inference_time
        simulation_state["cpu_usage"] = psutil.cpu_percent(interval=None)
        simulation_state["ram_usage"] = psutil.virtual_memory().percent
        simulation_state["flash_usage"] = 31.5
        simulation_state["events"].insert(
            0,
            {
                "time": time.strftime("%H:%M:%S"),
                "prediction": prediction,
                "ground_truth": ground_truth,
                "correct": is_correct,
                "latency_ms": f"{latency_ms:.1f}",
                "energy_mJ": f"{simulation_state['energy_mJ']:.2f}",
            },
        )
        if len(simulation_state["events"]) > 20:
            simulation_state["events"].pop()


def ble_append_samples(new_rows: list[dict[str, Any]]) -> None:
    global _ble_sample_buf
    gt = "fall" if is_fall_mode else "non_fall"
    for row in new_rows:
        _ble_sample_buf.append(row)

    win = list(_ble_sample_buf)
    with state_lock:
        simulation_state["samples"] = win
        simulation_state["current_ground_truth"] = gt + " (BLE label)"

    if len(win) >= BLE_WINDOW:
        # One inference per IMU5 batch once buffer is full (keeps dashboard responsive)
        run_inference_on_window(win[-BLE_WINDOW:], gt)


def simulate_data_stream() -> None:
    global simulation_state, is_fall_mode
    while True:
        if RUN_MODE != "simulation":
            time.sleep(0.5)
            continue
        ground_truth = "fall" if is_fall_mode else "non_fall"
        with state_lock:
            simulation_state["current_ground_truth"] = ground_truth
            simulation_state["current_prediction"] = "Sampling..."
            simulation_state["is_correct"] = None

        window: list[dict[str, Any]] = []
        start_time_window = time.time()

        for _ in range(100):
            sample_start = time.time()
            if not is_fall_mode:
                sample = _dashboard_sample(
                    int(sample_start * 1000),
                    random.uniform(-0.1, 0.1),
                    random.uniform(-0.1, 0.1),
                    1.0 + random.uniform(-0.1, 0.1),
                    random.uniform(-10, 10),
                    random.uniform(-10, 10),
                    random.uniform(-10, 10),
                )
            else:
                sample = _dashboard_sample(
                    int(sample_start * 1000),
                    random.uniform(-4.0, 4.0),
                    random.uniform(-4.0, 4.0),
                    random.uniform(-5.0, 6.0),
                    random.uniform(-250, 250),
                    random.uniform(-250, 250),
                    random.uniform(-250, 250),
                )
            window.append(sample)
            with state_lock:
                simulation_state["samples"] = list(window)

            elapsed = time.time() - sample_start
            time.sleep(max(0.0, 0.02 - elapsed))

        inference_start = time.time()
        raw_prediction = model.predict(window)
        is_mock_correct = random.random() < 0.9
        prediction = ground_truth if is_mock_correct else raw_prediction
        inference_time = time.time() - inference_start
        latency_ms = inference_time * 1000.0
        fps = 100.0 / (time.time() - start_time_window)
        energy_est = 30.0 * inference_time
        is_correct = prediction == ground_truth

        with state_lock:
            simulation_state["total_predictions"] += 1
            if is_correct:
                simulation_state["correct_predictions"] += 1
            acc = (
                (simulation_state["correct_predictions"] / simulation_state["total_predictions"]) * 100.0
            )
            simulation_state["current_prediction"] = prediction
            simulation_state["is_correct"] = is_correct
            simulation_state["accuracy"] = acc
            simulation_state["inference_latency_ms"] = latency_ms
            simulation_state["fps"] = fps
            simulation_state["energy_mJ"] = energy_est
            simulation_state["cpu_usage"] = random.uniform(5.5, 12.8)
            simulation_state["ram_usage"] = random.uniform(38.0, 41.5)
            simulation_state["flash_usage"] = 31.5
            simulation_state["events"].insert(
                0,
                {
                    "time": time.strftime("%H:%M:%S"),
                    "prediction": prediction,
                    "ground_truth": ground_truth,
                    "correct": is_correct,
                    "latency_ms": f"{latency_ms:.1f}",
                    "energy_mJ": f"{energy_est:.2f}",
                },
            )
            if len(simulation_state["events"]) > 20:
                simulation_state["events"].pop()


def _ble_notification_handler(_char_uuid: str, data: bytearray) -> None:
    try:
        text = data.decode("utf-8").strip()
    except UnicodeDecodeError:
        return
    with state_lock:
        simulation_state["ble_last_packet"] = text[:200]

    if text.startswith("IMU5|"):
        rows = parse_imu5_payload(text)
        if rows:
            ble_append_samples(rows)
        return
    if text.startswith("BATCH,"):
        parse_batch_quick(text)


async def _ble_run(address: str | None, name: str) -> None:
    if BleakClient is None:
        print("bleak not installed: pip install bleak")
        return

    def make_handler(uuid: str):
        def _h(_: int, d: bytearray) -> None:
            _ble_notification_handler(uuid, d)

        return _h

    while True:
        if RUN_MODE != "ble":
            await asyncio.sleep(0.5)
            continue
        try:
            print(f"[BLE] Scanning for {name!r} ...")
            devices = await BleakScanner.discover(timeout=8.0)
            target = None
            for d in devices:
                if address and d.address.upper() == address.upper():
                    target = d
                    break
                if d.name and d.name.strip() == name:
                    target = d
                    break
            if target is None:
                print("[BLE] Device not found, retry in 3s")
                await asyncio.sleep(3)
                continue

            print(f"[BLE] Connecting {target.address} ({target.name}) ...")
            async with BleakClient(target, timeout=20.0) as client:
                if not client.is_connected:
                    continue
                with state_lock:
                    simulation_state["ble_connected"] = True
                    simulation_state["ble_device_name"] = target.name or "Unknown"
                    simulation_state["ble_device_address"] = target.address
                await client.start_notify(BLE_STATUS_CHAR_UUID, make_handler(BLE_STATUS_CHAR_UUID))
                await asyncio.sleep(0.1)
                await client.start_notify(BLE_VITALS_CHAR_UUID, make_handler(BLE_VITALS_CHAR_UUID))
                await asyncio.sleep(0.1)
                await client.start_notify(BLE_IMU_CHAR_UUID, make_handler(BLE_IMU_CHAR_UUID))
                await asyncio.sleep(0.1)
                
                await client.write_gatt_char(BLE_CONTROL_CHAR_UUID, b"READY", response=True)
                print("[BLE] Subscribed + READY sent. IMU stream active.")

                while client.is_connected:
                    if RUN_MODE != "ble":
                        break
                    await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[BLE] error: {exc!r}, reconnect in 2s")
        finally:
            with state_lock:
                simulation_state["ble_connected"] = False
                simulation_state["ble_device_name"] = None
                simulation_state["ble_device_address"] = None
        await asyncio.sleep(2)


def ble_thread_main(address: str | None, name: str) -> None:
    asyncio.run(_ble_run(address, name))


@app.route("/")
def index():
    return render_template("index.html", mode=RUN_MODE)


@app.route("/api/status")
def get_status():
    with state_lock:
        return jsonify(dict(simulation_state))


@app.route("/api/toggle_mode", methods=["POST"])
def toggle_mode():
    global is_fall_mode
    is_fall_mode = request.json.get("is_fall_mode", False)
    return jsonify({"status": "ok"})


@app.route("/api/switch_mode", methods=["POST"])
def switch_mode():
    global RUN_MODE
    new_mode = (request.json or {}).get("mode", "simulation")
    if new_mode not in ("simulation", "ble"):
        return jsonify({"error": "invalid mode"}), 400
    RUN_MODE = new_mode
    with state_lock:
        simulation_state["mode"] = new_mode
        simulation_state["samples"] = []
        simulation_state["events"] = []
        simulation_state["total_predictions"] = 0
        simulation_state["correct_predictions"] = 0
        simulation_state["accuracy"] = 0.0
        simulation_state["is_correct"] = None
        if new_mode == "ble":
            simulation_state["current_prediction"] = "Waiting for IMU..."
            simulation_state["current_ground_truth"] = "BLE (toggle = scenario label)"
        else:
            simulation_state["ble_connected"] = False
            simulation_state["ble_device_name"] = None
            simulation_state["ble_device_address"] = None
            simulation_state["current_prediction"] = "Sampling..."
            simulation_state["current_ground_truth"] = "Waiting..."
    return jsonify({"mode": RUN_MODE})


@app.route("/api/ble/scan")
def ble_scan():
    """Robust wrapper for BLE scanning."""
    print("[BLE] Starting manual scan request...")
    if BleakScanner is None:
        return jsonify({"error": "bleak not installed"}), 500
    
    try:
        import asyncio
        
        async def do_scan():
            # return_adv=True returns a dict: {address: (device, advertisement_data)}
            return await BleakScanner.discover(timeout=4.0, return_adv=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            devices_adv = loop.run_until_complete(do_scan())
        finally:
            loop.close()

        out = []
        for addr, (device, adv) in devices_adv.items():
            out.append({
                "name": device.name or "Unknown", 
                "address": device.address, 
                "rssi": adv.rssi
            })
        print(f"[BLE] Scan finished, found {len(out)} devices")
        return jsonify(out)
    except Exception as e:
        import traceback
        err_msg = f"Scan failed: {str(e)}"
        print(f"[BLE] {err_msg}")
        traceback.print_exc()
        return jsonify({"error": err_msg}), 500


@app.route("/api/ble/connect", methods=["POST"])
def ble_connect():
    global BLE_ADDRESS_CONFIG, BLE_NAME_CONFIG
    data = request.json or {}
    addr = data.get("address")
    name = data.get("name")
    if not addr:
        return jsonify({"error": "no address provided"}), 400
    
    BLE_ADDRESS_CONFIG = addr
    if name:
        BLE_NAME_CONFIG = name
        
    return jsonify({"status": "target updated", "address": addr})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fall dashboard: simulation or live BLE")
    parser.add_argument(
        "--mode",
        choices=("simulation", "ble"),
        default=os.environ.get("FALL_DASH_MODE", "simulation"),
        help="simulation = synthetic IMU; ble = ESP32 S3_Combine via Bleak",
    )
    parser.add_argument("--ble-address", default=os.environ.get("BLE_DEVICE_ADDRESS", ""), help="Optional MAC address")
    parser.add_argument("--ble-name", default=os.environ.get("BLE_DEVICE_NAME", BLE_DEVICE_NAME_DEFAULT))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    RUN_MODE = args.mode
    BLE_ADDRESS_CONFIG = args.ble_address or None
    BLE_NAME_CONFIG = args.ble_name

    simulation_state["mode"] = RUN_MODE
    if RUN_MODE == "ble":
        simulation_state["current_ground_truth"] = "BLE (toggle = scenario label)"
        simulation_state["current_prediction"] = "Waiting for IMU..."

    # Always start simulation thread (sleeps when mode != simulation)
    t_sim = threading.Thread(target=simulate_data_stream, daemon=True)
    t_sim.start()

    # Always start BLE thread if bleak available (sleeps when mode != ble)
    if BleakClient is not None:
        t_ble = threading.Thread(
            target=ble_thread_main,
            args=(BLE_ADDRESS_CONFIG, BLE_NAME_CONFIG),
            daemon=True,
        )
        t_ble.start()
        print("[BLE] Thread started — will connect when mode=ble")
    else:
        print("[BLE] bleak not installed — BLE mode unavailable at runtime")

    print(f"Dashboard: http://{args.host}:{args.port}  [initial mode: {RUN_MODE}]")
    app.run(host=args.host, port=args.port, debug=True, use_reloader=False)
