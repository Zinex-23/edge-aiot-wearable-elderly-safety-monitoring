# Experiment Report — V63

## Config
- Arch: 4×Conv1D [32, 48, 64, 96], K=[5, 5, 5, 5], Dense=20
- LR=0.0003 | Dropout=0.5 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: V56+V59 combo: dropout=0.5 + batch=32 (FAR reduction focus)

## Results
- Accuracy: 0.8955
- Recall: 0.9216
- F1: 0.8982
- FAR: 0.1306
- Size: 77.14 KB | Threshold: 0.70
