# Experiment Report — V61

## Config
- Arch: 4×Conv1D [16, 32, 48, 64], K=[5, 5, 5, 5], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: V22 arch [16,32,48,64]/K5 + D32 + batch=32

## Results
- Accuracy: 0.8694
- Recall: 0.9030
- F1: 0.8736
- FAR: 0.1642
- Size: 46.95 KB | Threshold: 0.78
