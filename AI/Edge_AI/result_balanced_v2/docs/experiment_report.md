# Experiment Report

## Dataset

Only HR_IMU data was used.

Before balancing:
- fall windows: 1628
- non-fall windows: 5468

After balancing:
- fall windows: 1628
- non-fall windows: 1628
- ratio: 1:1

## Training

- epochs: 60
- batch size: 32
- optimizer: Adam
- loss: binary_crossentropy

## Final Metrics

- accuracy: 0.9080
- precision: 0.8541
- recall: 0.9836
- F1-score: 0.9143
- false alarm rate: 0.1673
- miss rate: 0.0164
