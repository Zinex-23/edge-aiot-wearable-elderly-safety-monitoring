# TinyCNN Fall Detection - Version 27

## 📌 Project Context
Model V27 is a specialized iteration focused on **False Alarm Rate (FAR) suppression** while maintaining a high F1-score. It serves as the baseline for the "Deep TinyCNN" architecture used in versions V27-V50.

## 📁 Directory Structure
- `models/`: Contains the trained TFLite file (`fall_detection_v27.tflite`).
- `results/`: Comprehensive performance reports and visualizations.
  - [Detailed Metrics Summary](results/metrics_summary.txt)
  - [Technical Performance Report](results/metrics_v27.md)
  - [Threshold Optimization Data](results/threshold_metrics.csv)

## 🚀 Key Achievements
- **FAR < 9%**: One of the first models to break the 10% false alarm barrier.
- **Robustness**: High stability across various IMU sensor noise profiles.
- **Architecture**: Proven 4-layer design that became the project standard.

## 📊 Performance at a Glance
- **F1-Score**: 90.64%
- **Recall**: 90.30%
- **Accuracy**: 90.67%
- **Size**: 51.73 KB (INT8 Quantized)

---
*Generated for Edge-AIot Wearable Elderly Safety Monitoring Project*
