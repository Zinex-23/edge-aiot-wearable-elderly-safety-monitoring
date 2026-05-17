# Experiment Report — V62

## Config
- Arch: 4×Conv1D [32, 48, 64, 96], K=[5, 5, 5, 5], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: V54+V59 combo: D32 + batch=32 (best F1 + best FAR combo)

## Results
- Accuracy: 0.9049
- Recall: 0.9701
- F1: 0.9107
- FAR: 0.1604
- Size: 78.52 KB | Threshold: 0.49
