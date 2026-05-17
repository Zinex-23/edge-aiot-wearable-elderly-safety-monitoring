# Experiment Report — V65

## Config
- Arch: 4×Conv1D [24, 48, 64, 96], K=[5, 5, 5, 5], Dense=24
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: V37 arch [24,48,64,96]/K5 + D24 + batch=32

## Results
- Accuracy: 0.8918
- Recall: 0.9627
- F1: 0.8990
- FAR: 0.1791
- Size: 75.38 KB | Threshold: 0.60
