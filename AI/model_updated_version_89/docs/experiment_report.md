# Experiment Report — V89

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.4 | L2=0.0003
- EarlyStopping patience=25 | ReduceLR factor=0.2 patience=10
- Augmentation sigma=0.1 | Cosine LR=False
- Note: Gaussian noise aug σ=0.10 — stronger augmentation

## Results
- F1: 0.9088 | Recall: 0.9478 | FAR: 0.1381
- Accuracy: 0.9049 | Size: 62.10 KB | Threshold: 0.75
- Stopped at epoch: 57
- Train/Val loss gap (last epoch): -0.0295 (ok)
