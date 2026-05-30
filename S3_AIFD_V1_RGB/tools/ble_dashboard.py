from pathlib import Path

from flask import Flask, render_template


DEVICE_NAME = "ESP32-fall-detection-BLE"
SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
STATUS_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
ACCEL_CHAR_UUID = "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1"
GYRO_CHAR_UUID = "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03"

app = Flask(__name__, template_folder=str(Path(__file__).with_name("templates")))


@app.route("/")
def index():
    return render_template(
        "dashboard.html",
        device_name=DEVICE_NAME,
        service_uuid=SERVICE_UUID,
        status_char_uuid=STATUS_CHAR_UUID,
        accel_char_uuid=ACCEL_CHAR_UUID,
        gyro_char_uuid=GYRO_CHAR_UUID,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
