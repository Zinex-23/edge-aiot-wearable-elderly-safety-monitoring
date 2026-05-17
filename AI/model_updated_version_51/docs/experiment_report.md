# Experiment Report — Model V51

## Config
- Architecture: 4×Conv1D [32, 48, 64, 96], Kernels=[5, 5, 5, 5], Dense=20
- LR: 0.0003 | Dropout: 0.4 | L2: 0.0001 | Batch: 64
- Class weight: {0: 1.0, 1: 1.0}
- Note: V50 base, cw=1:1, FAR-penalized scoring

## Results
- Accuracy: 0.8321
- Recall:   0.7276
- F1:       0.8125
- FAR:      0.0634
- Size:     76.64 KB
- Threshold: 0.85
