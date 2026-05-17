# Experiment Report — Model V58

## Config
- Architecture: 4×Conv1D [32, 48, 64, 96], Kernels=[5, 5, 5, 5], Dense=20
- LR: 0.0001 | Dropout: 0.4 | L2: 0.0001 | Batch: 64
- Class weight: {0: 1.0, 1: 1.2}
- Note: V50 base + LR=1e-4 (finer convergence)

## Results
- Accuracy: 0.9123
- Recall:   0.9366
- F1:       0.9144
- FAR:      0.1119
- Size:     77.23 KB
- Threshold: 0.70
