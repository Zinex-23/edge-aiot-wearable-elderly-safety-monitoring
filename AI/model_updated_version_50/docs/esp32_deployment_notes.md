# ESP32 Deployment Notes - Version 50 (WINNER)

Files:
- `models/fall_detection_v50.tflite` (Quantized INT8)

Input Configuration:
- Shape: [1, 100, 6]
- Channels: ax, ay, az, gx, gy, gz
- Sample Rate: 50 Hz
- **Architecture Note**: Uses K5 (Kernel Size 5) which requires slightly more computation but provides better temporal resolution.

Hardware Target:
- Platform: ESP32-S3
- Flash Memory: ~42 KB
- RAM: Requires ~60-80 KB for TFLite Arena (due to deeper filters).

Inference Logic:
- Recommended Threshold: 0.45 (Optimal for high sensitivity).
- Sliding Window Stride: 50 samples.
