# 1.3 AI Fall Detection Methodology and Rationale

The fall detection methodology of this project is developed based on the academic foundation of the **CareFall** study by Ruiz-Garcia et al. CareFall proposes an automatic Fall Detection System using wearable inertial sensors and AI-based classification. In particular, the system uses 3-axis accelerometer and 3-axis gyroscope signals collected from a smartwatch, then evaluates both threshold-based and machine-learning-based approaches for distinguishing falls from Activities of Daily Living. 

Rather than directly reproducing the CareFall pipeline, this project uses it as a scientific baseline to identify which principles are effective and which aspects need to be adapted for a practical edge-AIoT wearable device. The main objective is therefore not only to achieve reliable fall classification, but also to minimize response latency, reduce computational cost, and enable real-time on-device inference on the ESP32-S3.

## 1.3.1 Academic Strengths of the CareFall Baseline

CareFall provides a strong reference framework for wearable fall detection because it demonstrates two important principles.

First, the study confirms the value of **multi-sensor inertial data**. By combining accelerometer and gyroscope information, CareFall achieves better overall performance than using each sensor independently. On the Erciyes University dataset, the machine learning model using both accelerometer and gyroscope features reaches 98.4% accuracy, 98.9% sensitivity, and 96.7% specificity. On the UMAFall dataset, the combined-sensor configuration also achieves the best accuracy, reaching 95.5%. 

Second, CareFall shows that **machine learning is more reliable than simple threshold-based logic**, especially in reducing false alarms. Although threshold-based methods can achieve very high sensitivity, their specificity is significantly lower. For example, on the Erciyes dataset, the threshold-based approach reaches 100% sensitivity but only 68.4% specificity, while the machine-learning-based approach improves specificity to 96.7%. This indicates that threshold methods may detect many falls, but they are more likely to misclassify normal daily activities as falls. 

These findings support the design direction of this project: fall detection should use both accelerometer and gyroscope signals, and the classification logic should rely on AI-based pattern recognition rather than fixed thresholds alone.

## 1.3.2 Real-World Adaptation and Development Factors

Although CareFall provides a robust academic baseline, several adaptations are required before the method can be used effectively in a real-world wearable device.

The first challenge is **response latency**. CareFall uses separate time windows of one minute for analysis, which is suitable for experimental evaluation but may be too slow for emergency fall detection. In a real healthcare scenario, a fall alert should be generated within a few seconds, especially for elderly users who may lose consciousness or be unable to manually request help. Therefore, this project adopts a **2-second sliding window**, allowing the system to make near real-time predictions.

The second challenge is **feature extraction complexity**. CareFall extracts 88 statistical features from accelerometer and gyroscope signals, including mean, variance, median, standard deviation, maximum, minimum, percentiles, Power Spectral Density, and Power Spectral Entropy. While this feature-engineering approach is effective for classical machine learning, it increases preprocessing complexity and is less ideal for microcontroller-level deployment. To address this, our system uses a TinyCNN model that learns temporal motion patterns directly from raw 6-axis IMU signals.

The third challenge is **edge deployment**. The CareFall paper focuses mainly on classification performance across public datasets, while this project further considers embedded constraints such as model size, memory usage, inference time, and independence from cloud connectivity. For this reason, the proposed model is optimized using INT8 quantization and deployed directly on the ESP32-S3.

## 1.3.3 Proposed TinyCNN Architecture and Performance Results

To meet the requirements of real-time wearable fall detection, this project proposes a lightweight **TinyCNN** model optimized for edge-AI inference. The model receives raw 6-axis IMU data as input and automatically learns discriminative motion patterns associated with fall events.

**A. Layer-by-layer architecture**

| Component            | Description                                                                          |
| -------------------- | ------------------------------------------------------------------------------------ |
| Input layer          | `(100, 6)` tensor, representing 2 seconds of 6-axis IMU data sampled at 50 Hz        |
| Convolutional layers | Two 1D convolution layers with 16 and 32 filters to extract temporal motion features |
| Activation           | ReLU activation for nonlinear feature learning                                       |
| Downsampling         | MaxPooling and Global Average Pooling to reduce parameters and computation           |
| Output layer         | One dense unit with sigmoid activation for fall probability prediction               |

Compared with CareFall’s manual feature extraction pipeline, this TinyCNN architecture allows the model to learn fall-related temporal signatures directly from raw sensor signals. This reduces dependence on hand-crafted statistical features and makes the pipeline more suitable for real-time embedded inference.

**B. Performance evaluation results**

| Metric               |        Value | Interpretation                                    |
| -------------------- | -----------: | ------------------------------------------------- |
| Recall / Sensitivity |   **98.36%** | Very strong fall detection capability             |
| Miss Rate            |    **1.64%** | Low probability of missing actual falls           |
| Accuracy             |       90.80% | Good overall classification performance           |
| F1-score             |       91.43% | Balanced performance between precision and recall |
| Model Size           | **10.71 KB** | Suitable for microcontroller deployment           |

For a safety-critical system, recall is the most important metric because missing a real fall can lead to serious consequences. Therefore, the model is tuned to prioritize high sensitivity, even if this may slightly increase the number of false alarms.

## 1.3.4 Comparative Analysis with the CareFall Baseline

The following comparison summarizes how this project adapts the CareFall research direction for real-world edge-AIoT deployment.

| Criteria               | CareFall Baseline                                               | Proposed Edge-AIoT System                   |
| ---------------------- | --------------------------------------------------------------- | ------------------------------------------- |
| Sensor data            | 3-axis accelerometer + 3-axis gyroscope                         | 3-axis accelerometer + 3-axis gyroscope     |
| Sampling rate          | 20–25 Hz                                                        | 50 Hz                                       |
| Decision window        | 1-minute window                                                 | 2-second sliding window                     |
| Feature representation | 88 hand-crafted statistical features                            | Raw `(100, 6)` tensor                       |
| AI approach            | Traditional ML classifiers such as RF, SVM, KNN, GB, ANN        | TinyCNN deep learning model                 |
| Main strength          | High classification accuracy and specificity on public datasets | Real-time inference and embedded deployment |
| Deployment focus       | Academic evaluation on datasets                                 | ESP32-S3 edge-AI wearable implementation    |
| Model size             | Not specified in the paper                                      | 10.71 KB after optimization                 |

This comparison shows that CareFall is a strong academic baseline for validating the importance of sensor fusion and AI-based fall detection. However, the proposed system extends this direction toward a practical wearable device by reducing the decision window from one minute to two seconds, replacing manual feature engineering with automatic CNN-based feature learning, and optimizing the model for on-device inference.

## Conclusion

Overall, CareFall provides the scientific foundation for this project by showing that wearable accelerometer and gyroscope signals can be effectively used for AI-based fall detection. However, practical deployment requires additional optimization beyond classification accuracy alone. The proposed TinyCNN model addresses this gap by prioritizing low latency, compact model size, and autonomous edge inference on the ESP32-S3.

Therefore, the contribution of this project is not to outperform CareFall in every academic metric, but to **translate the CareFall research direction into a real-time, lightweight, and deployable edge-AIoT fall detection system**. This makes the system more suitable for practical elderly safety monitoring, where fast response, portability, and reliability are critical.
