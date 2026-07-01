# ESP32-S3 Pin Configuration (S3_AIFD_V1)

This document lists the hardware pin assignments used in the `S3_AIFD_V1` firmware for the elderly safety monitoring wearable device.

## Pin Mapping

| Component / Function | ESP32-S3 GPIO Pin | Description |
| :--- | :--- | :--- |
| **RGB LED Power (VCC)** | `GPIO 4` | Controls power supply to the WS2812 RGB module (Output) |
| **RGB LED Data (DI)** | `GPIO 5` | Data signal for the WS2812 RGB LED (Output) |
| **Buzzer** | `GPIO 7` | Controls the active/passive alarm buzzer (Output) |
| **I2C SDA** | `GPIO 8` | I2C Data line (connected to BMI160 / MAX30102) |
| **I2C SCL** | `GPIO 9` | I2C Clock line (connected to BMI160 / MAX30102) |
| **Button** | `GPIO 10` | Push button for user input / "I'm Safe" / SOS (Input Pullup) |
