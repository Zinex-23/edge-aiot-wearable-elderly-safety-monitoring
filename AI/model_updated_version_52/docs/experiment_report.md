# Experiment Report — Model V52

## Config
- Architecture: 4×Conv1D [32, 48, 64, 96], Kernels=[5, 5, 5, 5], Dense=20
- LR: 0.0003 | Dropout: 0.4 | L2: 0.0001 | Batch: 64
- Class weight: {0: 1.0, 1: 1.5}
- Note: V50 base, cw=1:1.5, Recall-maximizing scoring

## Results
- Accuracy: 0.9216
- Recall:   0.9739
- F1:       0.9255
- FAR:      0.1306
- Size:     77.06 KB
- Threshold: 0.29
