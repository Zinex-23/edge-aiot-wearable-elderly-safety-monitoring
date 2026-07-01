# Experiment Report — V68

## Config
- Arch: 4×Conv1D [32, 48, 64, 96], K=[5, 5, 5, 5], Dense=20
- LR=0.0001 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: V58+V59 combo: LR=1e-4 + batch=32

## Results
- Accuracy: 0.8974
- Recall: 0.9590
- F1: 0.9033
- FAR: 0.1642
- Size: 77.23 KB | Threshold: 0.62
