# Experiment Report — Model V56

## Config
- Architecture: 4×Conv1D [32, 48, 64, 96], Kernels=[5, 5, 5, 5], Dense=20
- LR: 0.0003 | Dropout: 0.5 | L2: 0.0001 | Batch: 64
- Class weight: {0: 1.0, 1: 1.2}
- Note: V50 base + Dropout=0.5 (more regularization)

## Results
- Accuracy: 0.9086
- Recall:   0.8955
- F1:       0.9074
- FAR:      0.0784
- Size:     77.23 KB
- Threshold: 0.77
