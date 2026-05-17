# Experiment Report — Model V54

## Config
- Architecture: 4×Conv1D [32, 48, 64, 96], Kernels=[5, 5, 5, 5], Dense=32
- LR: 0.0003 | Dropout: 0.4 | L2: 0.0001 | Batch: 64
- Class weight: {0: 1.0, 1: 1.2}
- Note: V50 base + Dense=32 (more classification capacity)

## Results
- Accuracy: 0.9272
- Recall:   0.9776
- F1:       0.9307
- FAR:      0.1231
- Size:     78.68 KB
- Threshold: 0.43
