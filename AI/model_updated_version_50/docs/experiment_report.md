# Experiment Report - Model V50

## Dataset
- Type: Rebuilt Balanced HR_IMU
- Ratio: 1:1 (1628 samples each)
- Splitting: 70/15/15

## Training Configuration
- Architecture: 4x Conv1D [32, 48, 64, 96]
- **Kernel Size**: 5 (Major upgrade from K3)
- Epochs: 200
- Batch Size: 64
- Learning Rate: 3e-4 (Optimized for K5 stability)
- Optimizer: Adam
- Loss: Binary Crossentropy

## Final Metrics (Experimental Peak)
- Accuracy: 0.9123
- Precision: 0.8741
- Recall: 0.9664
- F1-score: 0.9168
- False Alarm Rate: 0.1418
- Miss Rate: 0.0336
- ROC AUC: 0.9782

## Technical Conclusion
Model V50 is chosen as the **Best Overall** because it successfully achieves high F1-score and Sensitivity while remaining 20% smaller than the V27/V30 baselines. The K5 architecture proves to be superior for capturing the rapid signal transitions characteristic of fall events.
