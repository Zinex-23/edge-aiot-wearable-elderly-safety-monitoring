# ESP32 Deployment Notes

Files:
- `models/fall_detection_model.tflite`
- `models/fall_detection_model.h`

Input:
- shape: 100 x 6
- channels: ax, ay, az, gx, gy, gz
- sample rate: 50 Hz

Inference threshold:
- selected probability threshold: 0.40
