# ESP32 Deployment Notes - Version 27

Files:
- `models/fall_detection_v27.tflite` (Quantized INT8)

Input Configuration:
- Shape: [1, 100, 6] (Window size 100, 6 IMU channels)
- Order: ax, ay, az, gx, gy, gz
- Sample Rate: 50 Hz (20ms between samples)

Hardware Target:
- Platform: ESP32-S3
- Memory: Requires ~52 KB Flash for model storage.

Inference Logic:
- Sliding Window Stride: 50 samples (Recommended for 50% overlap).
- Detection Threshold: 0.40 (Adjustable via `threshold_metrics.csv` for specific environments).
