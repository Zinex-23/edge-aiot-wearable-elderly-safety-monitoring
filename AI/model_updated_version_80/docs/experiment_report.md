# Experiment Report — V80

## Config
- Arch: 4×Conv1D [32, 64, 64, 96], K=[3, 3, 3, 3], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0003 | Batch=32
- Class weight: {0: 1.0, 1: 1.2} | Epochs=200
- Note: V64 + L2=3e-4 (tuned regularization between 1e-4 and 5e-4)

## Results
- F1: 0.9338 | Recall: 0.9739 | FAR: 0.1119
- Accuracy: 0.9310 | Size: 62.10 KB | Threshold: 0.66
