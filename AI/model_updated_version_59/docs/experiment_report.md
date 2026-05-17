# Experiment Report — Model V59

## Config
- Architecture: 4×Conv1D [32, 48, 64, 96], Kernels=[5, 5, 5, 5], Dense=20
- LR: 0.0003 | Dropout: 0.4 | L2: 0.0001 | Batch: 32
- Class weight: {0: 1.0, 1: 1.2}
- Note: V50 base + BatchSize=32 (better generalization)

## Results
- Accuracy: 0.9216
- Recall:   0.9254
- F1:       0.9219
- FAR:      0.0821
- Size:     77.23 KB
- Threshold: 0.73
