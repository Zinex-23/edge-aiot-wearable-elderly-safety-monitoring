# Experiment Report — Model V55

## Config
- Architecture: 4×Conv1D [48, 64, 80, 96], Kernels=[5, 5, 5, 5], Dense=20
- LR: 0.0003 | Dropout: 0.4 | L2: 0.0001 | Batch: 64
- Class weight: {0: 1.0, 1: 1.2}
- Note: Wider filters [48,64,80,96] — more feature capacity

## Results
- Accuracy: 0.9123
- Recall:   0.9664
- F1:       0.9168
- FAR:      0.1418
- Size:     104.00 KB
- Threshold: 0.27
