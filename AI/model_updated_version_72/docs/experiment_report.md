# Experiment Report — V72

## Config
- Arch: 4×Conv1D [32, 64, 64, 96], K=[3, 3, 3, 3], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=16
- Class weight: {0: 1.0, 1: 1.2} | Epochs=200
- Note: V64 + batch=16 (smaller batch → better generalization)

## Results
- F1: 0.8997 | Recall: 0.9701 | FAR: 0.1866
- Accuracy: 0.8918 | Size: 61.93 KB | Threshold: 0.46
