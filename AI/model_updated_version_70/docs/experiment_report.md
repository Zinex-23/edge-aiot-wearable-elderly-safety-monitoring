# Experiment Report — V70

## Config
- Arch: 5×Conv1D [16, 32, 48, 64, 96], K=[5, 5, 5, 5, 5], Dense=24
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: 5 conv layers [16,32,48,64,96]/K5 — novel depth + batch=32

## Results
- Accuracy: 0.9086
- Recall: 0.9403
- F1: 0.9114
- FAR: 0.1231
- Size: 83.25 KB | Threshold: 0.50
