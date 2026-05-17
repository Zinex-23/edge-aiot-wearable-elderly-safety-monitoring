# Experiment Report — V84

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.4 | L2=0.0003
- EarlyStopping patience=25 | ReduceLR factor=0.2 patience=10
- Augmentation sigma=0.05 | Cosine LR=False
- Note: Gaussian noise aug σ=0.05 — fix overfitting at root

## Results
- F1: 0.9345 | Recall: 0.9851 | FAR: 0.1231
- Accuracy: 0.9310 | Size: 62.09 KB | Threshold: 0.42
- Stopped at epoch: 78
- Train/Val loss gap (last epoch): 0.0194 (ok)
