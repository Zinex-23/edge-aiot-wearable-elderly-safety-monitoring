# Experiment Report — V85

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.4 | L2=0.0003
- EarlyStopping patience=25 | ReduceLR factor=0.2 patience=10
- Augmentation sigma=0.0 | Cosine LR=True
- Note: Cosine decay LR — smooth convergence, no oscillation

## Results
- F1: 0.9050 | Recall: 0.9776 | FAR: 0.1828
- Accuracy: 0.8974 | Size: 62.09 KB | Threshold: 0.42
- Stopped at epoch: 43
- Train/Val loss gap (last epoch): -0.2205 (overfitting)
