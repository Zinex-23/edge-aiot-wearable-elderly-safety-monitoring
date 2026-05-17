# Experiment Report — Model V57

## Config
- Architecture: 4×Conv1D [32, 48, 64, 96], Kernels=[5, 5, 5, 5], Dense=20
- LR: 0.0003 | Dropout: 0.4 | L2: 0.0005 | Batch: 64
- Class weight: {0: 1.0, 1: 1.2}
- Note: V50 base + L2=5e-4 (stronger weight decay)

## Results
- Accuracy: 0.9104
- Recall:   0.9701
- F1:       0.9155
- FAR:      0.1493
- Size:     77.23 KB
- Threshold: 0.53
