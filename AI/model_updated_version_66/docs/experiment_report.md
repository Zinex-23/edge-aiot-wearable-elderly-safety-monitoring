# Experiment Report — V66

## Config
- Arch: 4×Conv1D [16, 32, 48, 64], K=[5, 5, 5, 5], Dense=24
- LR=0.0003 | Dropout=0.45 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: V22 arch tuned: D24 + dropout=0.45 + batch=32

## Results
- Accuracy: 0.9179
- Recall: 0.9552
- F1: 0.9209
- FAR: 0.1194
- Size: 46.81 KB | Threshold: 0.61
