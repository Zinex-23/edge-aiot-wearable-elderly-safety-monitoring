#!/usr/bin/env bash
set -euo pipefail

RULE_FILE="/etc/udev/rules.d/60-esp32-s3-usb-jtag.rules"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo:"
  echo "  sudo bash $0"
  exit 1
fi

cat > "${RULE_FILE}" <<'EOF'
# ESP32-S3 built-in USB JTAG/serial debug unit
SUBSYSTEM=="usb", ATTR{idVendor}=="303a", ATTR{idProduct}=="1001", MODE="0666", TAG+="uaccess"
EOF

udevadm control --reload-rules
udevadm trigger

current_device="$(lsusb -d 303a:1001 | awk '{gsub(":", "", $4); print "/dev/bus/usb/" $2 "/" $4}' | head -n 1)"
if [[ -n "${current_device}" && -e "${current_device}" ]]; then
  chmod 666 "${current_device}"
  echo "Updated current device permissions: ${current_device}"
else
  echo "ESP32-S3 USB JTAG device not found right now. Replug the board after this script."
fi

echo "Installed ${RULE_FILE}"
echo "Unplug/replug the ESP32-S3, then run: pio run -t upload && pio device monitor"
