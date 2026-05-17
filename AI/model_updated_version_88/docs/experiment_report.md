# Experiment Report — V88

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.45 | L2=0.0003
- EarlyStopping patience=20 | ReduceLR factor=0.1 patience=5
- Augmentation sigma=0.0 | Cosine LR=False
- Note: Dropout=0.45 + aggressive LR(factor=0.1, p=5) — tuned regularize

## Results
- F1: 0.9184 | Recall: 0.9664 | FAR: 0.1381
- Accuracy: 0.9142 | Size: 62.10 KB | Threshold: 0.65
- Stopped at epoch: 31
- Train/Val loss gap (last epoch): -0.0215 (ok)
