# Experiment Report — V69

## Config
- Arch: 4×Conv1D [32, 48, 64, 96], K=[5, 5, 5, 5], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0005 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: V54+V59+V57 combo: D32 + batch=32 + L2=5e-4

## Results
- Accuracy: 0.9067
- Recall: 0.9739
- F1: 0.9126
- FAR: 0.1604
- Size: 78.70 KB | Threshold: 0.43
