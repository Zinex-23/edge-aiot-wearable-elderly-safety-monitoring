# Result Balanced V2

This run uses only HR_IMU data and balances the dataset after windowing by undersampling the larger class.

Key counts:
- fall windows before balancing: 1628
- non-fall windows before balancing: 5468
- fall windows after balancing: 1628
- non-fall windows after balancing: 1628
- total balanced windows: 3256

Training used 60 epochs with early stopping enabled and a lightweight TinyCNN for ESP32-S3.
