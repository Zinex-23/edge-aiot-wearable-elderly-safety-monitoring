# Experiment Report - Model V27

## Dataset
This experiment used the rebuilt balanced dataset with 6-channel IMU data.

Before balancing:
- Fall windows: 1628
- Non-fall windows: 5468

After balancing:
- Fall windows: 1628
- Non-fall windows: 1628
- Ratio: 1:1

## Training Configuration
- Architecture: 4x Conv1D [32, 64, 64, 96]
- Epochs: 200 (Early Stopping at ~60-80)
- Batch Size: 64
- Learning Rate: 5e-4
- Optimizer: Adam
- Loss: Binary Crossentropy
- Class Weight: {Non-fall: 1.0, Fall: 1.2}

## Final Metrics (Test Set)
- Accuracy: 0.9067
- Precision: 0.9098
- Recall: 0.9030
- F1-score: 0.9064
- False Alarm Rate: 0.0896
- Miss Rate: 0.0970
