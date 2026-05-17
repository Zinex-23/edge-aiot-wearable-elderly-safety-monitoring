# Experiment Report — V86

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.4 | L2=0.0005
- EarlyStopping patience=25 | ReduceLR factor=0.1 patience=5
- Augmentation sigma=0.05 | Cosine LR=False
- Note: aug σ=0.05 + L2=5e-4 + LR aggressive — two strongest fixes

## Results
- F1: 0.9228 | Recall: 0.9813 | FAR: 0.1455
- Accuracy: 0.9179 | Size: 62.10 KB | Threshold: 0.81
- Stopped at epoch: 65
- Train/Val loss gap (last epoch): -0.0253 (ok)
