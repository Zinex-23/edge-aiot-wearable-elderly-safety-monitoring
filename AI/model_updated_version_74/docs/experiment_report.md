# Experiment Report — V74

## Config
- Arch: 4×Conv1D [32, 64, 64, 96], K=[5, 5, 5, 5], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2} | Epochs=200
- Note: V64 arch switched to K5 + D32 + batch=32

## Results
- F1: 0.9136 | Recall: 0.9664 | FAR: 0.1493
- Accuracy: 0.9086 | Size: 86.46 KB | Threshold: 0.67
