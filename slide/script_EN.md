# Presentation Script — M2 Report (English)
**CaraFall: Intelligent Edge AIoT Wearable System for Elderly Safety Monitoring**

---

## Slide 1 — Title (~20s)

Good morning, everyone. My name is Tran Phuoc Dien, and together with my teammate Pham Van Tien, we are presenting our M2 Capstone Report on the design and implementation of an Intelligent Edge AIoT Wearable System for Real-Time Safety Monitoring of Elderly People. This project is supervised by Ph.D Nguyen Thi Anh Thu and MSc. Nguyen Duc Phuoc.

---

## Slide 2 — Table of Contents (~20s)

Our presentation today is structured into five sections: first, a recap of the project objectives; second, the system architecture and proposed methods; third, individual contributions; fourth, the results we have achieved so far; and finally, our future work and timeline toward the final milestone.

---

## Slide 3 — Problem Statement & Motivation (~45s)

So why does this project matter? Falls are the second leading cause of unintentional injury deaths worldwide, according to the WHO. Elderly people aged 60 and above suffer the greatest number of fatal falls. What makes this particularly critical is the concept of "golden time" — if emergency response happens within the first few minutes after a fall, survival rates improve dramatically. In Vietnam specifically, the population is aging rapidly, with projections showing 20% of the population will be elderly by 2038. This creates an urgent need for affordable, reliable, and autonomous fall detection solutions — which is exactly the gap our system addresses.

---

## Slide 4 — System Architecture Overview (Diagram) (~30s)

Our system follows a layered architecture consisting of five layers: the Perception Layer where sensors collect data, the Edge Processing Layer where AI inference runs locally on the microcontroller, the Communication Layer using BLE 5.0, the Application Layer which is the Android mobile app, and finally the Cloud Layer for long-term data storage.

---

## Slide 5 — System Architecture Overview (Modules) (~45s)

Breaking it down into three functional modules: First, the Data Acquisition Module — this includes the BMI160 IMU sensor for 3-axis accelerometer and 3-axis gyroscope data, and the MAX30102 PPG sensor for Heart Rate and SpO2 measurement. Second, the Edge Processing Module — the ESP32-S3 microcontroller runs our TinyCNN model locally with no cloud dependency whatsoever. Third, the Communication and Alert Module — BLE 5.0 connects the wearable to the Android app, which then triggers automated emergency calls upon fall detection.

---

## Slide 6 — Proposed Methods: Data Flow (~60s)

This diagram illustrates the complete data flow of our system. Starting from the elderly person wearing the device, sensor data — accelerometer, gyroscope, heart rate, and SpO2 — is continuously collected. This data feeds into the ESP32-S3 MCU, which runs our Edge AI fall detection model in real-time with low latency. The key design philosophy here is **Offline-First**: the primary emergency path is Wearable → BLE → Android App → Direct Phone Call. This entire path requires zero internet connectivity. When a fall is detected, the app triggers an immediate call to the caregiver. Simultaneously, when an internet connection is available, health data is synced to our MongoDB cloud database for historical analysis. This architecture ensures that safety-critical alerts are never delayed by network instability.

---

## Slide 7 — Practical Design Model: Comparison with CareFall (~60s)

Our system is built upon the academic foundation of the CareFall paper by Ruiz-Garcia et al. However, we identified key limitations that make it unsuitable for real-world embedded deployment. As shown in this comparison table: CareFall uses a 60-second analysis window — far too slow for emergency response. We reduced this to a **2-second sliding window** for near real-time detection. CareFall extracts 88 hand-crafted statistical features, which adds significant preprocessing overhead. Our TinyCNN instead learns directly from raw 6-axis IMU data — the (100 × 6) tensor — eliminating the need for manual feature engineering. CareFall uses classical ML models like RF and SVM with a model size around 1 MB. Our TinyCNN is approximately 50 KB after INT8 quantization, making it feasible to run directly on the ESP32-S3. In summary, we adapted CareFall's validated direction toward practical, lightweight, offline-capable edge deployment.

---

## Slide 8 — Dataset & Training Pipeline: Class Distribution (~45s)

For training our model, we used the HR-IMU dataset, which contains data from 21 subjects across 19 activity scenarios — 6 fall types and 9 Activities of Daily Living. The raw dataset has a significant class imbalance: 1,628 fall windows versus 5,468 non-fall windows — roughly a 1-to-3.4 ratio. To prevent the model from developing a bias toward non-fall predictions, we applied undersampling to balance the dataset to a 1:1 ratio, resulting in 1,628 windows per class and a total of 3,256 training samples. This balanced distribution is essential for achieving high sensitivity in a safety-critical context.

---

## Slide 9 — Dataset & Training Pipeline: Configuration (~45s)

The model was trained using these carefully selected hyperparameters. We used the Adam optimizer with a learning rate of 1e-3 — chosen after testing 1e-2, which was unstable, and 1e-4, which was too slow. The loss function is Binary Cross-Entropy, the standard choice for binary classification with a Sigmoid output. Batch size of 32 was selected after testing 16 and 64 — 32 provided the most stable gradient updates. We set a maximum of 60 epochs with Early Stopping at patience 10, since our learning curves showed convergence between epochs 35 and 45. Finally, we save the checkpoint with the lowest validation loss, not the final epoch, to avoid overfitting.

---

## Slide 10 — Model Architecture: TinyCNN (~60s)

This diagram shows the complete layer-by-layer architecture of our TinyCNN model. The input is a (100, 6) tensor — 100 time steps at 50Hz equals 2 seconds of data across 6 IMU axes. A normalization layer with 13 parameters standardizes the input. The first Conv1D layer with 16 filters and kernel size 3 extracts local motion patterns — 304 parameters. MaxPooling1D with pool size 2 reduces the temporal dimension from 100 to 50, removing noise while preserving key features. A second Conv1D with 32 filters — 1,568 parameters — captures higher-level temporal patterns. Global Average Pooling then collapses the entire sequence into a 32-element feature vector, which is the critical step that makes this model edge-deployable. Finally, a Dense layer with 32 units and a Sigmoid output produces the fall probability. Total: approximately 2,974 parameters — extremely lightweight at 10.96 KB after INT8 quantization, well within our 500 KB constraint.

---

## Slide 11 — Model Evaluation: Threshold Optimization (~60s)

This graph shows our decision analysis for threshold selection. The green line is Recall, the blue line is F1-score, and the red line is the False Alarm Rate. We observe that Recall remains consistently high — above 98% — across the threshold range of 0.30 to 0.70. The False Alarm Rate, however, decreases significantly as the threshold increases. We selected a threshold of **0.50** as the optimal balance point. At this value, the model maintains its near-peak Recall of 98.36%, while the False Alarm Rate begins to drop meaningfully. Choosing a lower threshold would not improve Recall but would sharply increase false alarms. Choosing a higher threshold would reduce false alarms but risks missing actual falls — which in a safety-critical application is unacceptable. The cost of a missed fall is significantly higher than the cost of a false alarm.

---

## Slide 12 — Model Evaluation: Confusion Matrix (~45s)

The confusion matrix confirms the model's strong performance on the hold-out test set. Out of 244 actual fall cases, the model correctly identified 240 — and only missed 4. That is a miss rate of just 1.64%, well within our 2% target. The main weakness is on the non-fall side: 41 out of 245 non-fall cases were incorrectly flagged as falls, giving a False Alarm Rate of 16.73% — which currently exceeds our target of 10%. We acknowledge this gap and have planned a "consecutive window validation" mechanism for the final phase, which requires multiple consecutive fall-positive windows before triggering an alert, effectively filtering out sporadic false positives.

---

## Slide 13 — Mobile Application: Core Interfaces (~45s)

The companion Android application serves as the local gateway and user interface. As shown here, the app features a login screen, a role selection screen where the user can choose between Wearer and Caregiver modes, a home dashboard displaying real-time Heart Rate and SpO2 data, and most importantly — the SOS emergency screen. When a fall is detected, this screen appears with a 15-second countdown. The user can either tap "I'm Safe" to cancel, or tap "Call for Help" — or simply do nothing, in which case the app automatically calls the emergency contact after the countdown. This design ensures that conscious users can prevent false alarms, while unconscious users still receive immediate help.

---

## Slide 14 — Mobile Application: Health Monitoring (~30s)

The Health tab provides detailed vital sign monitoring. Users can view Heart Rate and SpO2 trends in three modes: Live, 1-Hour, and 24-Hour history. The app also shows average, minimum, and maximum values, along with contextual health guidance — for example, flagging SpO2 values below 95% as potentially indicating low blood oxygen. The History tab logs all events including fall detections, device disconnections, and low battery alerts with their resolution status.

---

## Slide 15 — Individual Contributions (~30s)

Here is our task breakdown. Tasks 1 through 8 have been completed on schedule. Dien led the AI pipeline — dataset acquisition, model design, training, and edge optimization. Tien led mobile app development and PCB design. Task 9, PCB assembly, is currently in progress. The remaining tasks — firmware integration, system testing, and the 3D-printed enclosure — are planned for the upcoming phases, which I will cover in the Future Work slide.

---

## Slide 16 — PCB & Hardware Design: Schematic (~30s)

The custom PCB integrates all system components on a single board. The schematic includes the ESP32-S3 microcontroller, the BMI160 accelerometer and gyroscope, the MAX30102 physiological sensor, battery management and charging circuit, a 3.3V LDO voltage regulator, USB-C for charging and programming, RGB LED for status indication, and an external antenna connector for optimized BLE range.

---

## Slide 17 — PCB Layout (~30s)

The PCB was designed to fit within 32 × 40 mm — compact enough for a wristband form factor. The 3D render confirms there are no component collisions. Key design principles include: placing the BMI160 and MAX30102 in close proximity to the ESP32-S3 to minimize I2C trace length and EMI susceptibility, and implementing ground planes on both layers for signal integrity and thermal management during AI inference.

---

## Slide 18–19 — (Skipped / Results Summary)

*(If applicable — summarize results briefly before moving to Future Work)*

---

## Slide 20 — App Demo (~20s)

At this point, we would like to do a live demonstration of the Android application, showing the real-time BLE connection to the wearable, live Heart Rate and SpO2 monitoring, and the fall detection alert flow.

---

## Slide 21 — Future Work (~30s)

Looking ahead to the final milestone, our remaining tasks are: completing firmware integration with sensor drivers and TFLite model deployment by May 25th; full system integration of firmware, hardware, BLE, and mobile app by May 31st; designing the 3D-printed wristband enclosure by June 10th; and system-level testing and benchmarking by June 20th. Our primary technical goal is to reduce the False Alarm Rate from 16.73% to below 10% through the consecutive window validation mechanism, while maintaining our Recall above 95%.

---

## Slide 22 — Thank You (~10s)

That concludes our M2 presentation. Thank you for your attention. We are happy to answer any questions.

---

*Total estimated time: ~12–15 minutes*
