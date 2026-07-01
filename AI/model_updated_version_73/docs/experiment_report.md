# Experiment Report — V73

## Config
- Arch: 4×Conv1D [32, 64, 96, 96], K=[3, 3, 3, 3], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2} | Epochs=200
- Note: V23 arch [32,64,96,96]/K3 + D32+batch=32 (V23 had FAR=7.84%)

## Results
- F1: 0.9071 | Recall: 0.9104 | FAR: 0.0970
- Accuracy: 0.9067 | Size: 77.88 KB | Threshold: 0.73
