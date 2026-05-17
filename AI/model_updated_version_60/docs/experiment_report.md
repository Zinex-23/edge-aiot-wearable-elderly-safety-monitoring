# Experiment Report — Model V60

## Config
- Architecture: 4×Conv1D [32, 48, 64, 96], Kernels=[3, 5, 5, 3], Dense=20
- LR: 0.0003 | Dropout: 0.4 | L2: 0.0001 | Batch: 64
- Class weight: {0: 1.0, 1: 1.2}
- Note: Mixed kernels K3/K5/K5/K3 — multi-scale temporal context

## Results
- Accuracy: 0.8899
- Recall:   0.8993
- F1:       0.8909
- FAR:      0.1194
- Size:     64.85 KB
- Threshold: 0.77
