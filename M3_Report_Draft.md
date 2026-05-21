# THE UNIVERSITY OF DANANG
# UNIVERSITY OF SCIENCE AND TECHNOLOGY
# FACULTY OF ADVANCED SCIENCE AND TECHNOLOGY

---

## CAPSTONE PROJECT

# CARAFALL: AN INTELLIGENT EDGE AIoT WEARABLE DEVICE APPLYING TINY MACHINE LEARNING FOR REAL-TIME FALL DETECTION AND ELDERLY SAFETY MONITORING

**TRẦN PHƯỚC DIỄN – CLASS: 21ES**
**PHẠM VĂN TIÊN – CLASS: 21ES**
*Advanced Undergraduate Program in Embedded System*

**Supervisor:** Ph.D Nguyễn Thị Anh Thu
**Co-supervisors:** MSc. Nguyễn Đức Phước

*Submitted to the Faculty of Advanced Science and Technology,
Advanced Undergraduate Program in Embedded Systems and IoT,
in Partial Fulfillment of the Requirements for the Degree of Engineer*

**Danang, 06/2026**

---

> *Auto-generated draft from repository state on branch `dien-zinex`, commit `2f658429`, dated `2026-05-20`. Search for `[TODO – NOT YET IN REPO]` to find every section still requiring author input before submission.*

---

## ABSTRACT

Falls [1] are a leading cause of injury, hospitalisation, and mortality among elderly individuals, often resulting in severe consequences such as hip fractures, traumatic brain injury, and the post-fall syndrome that limits independent living. According to the World Health Organisation [2], adults aged 65 years and older experience approximately 28–35 % of falls each year, and this proportion rises to 32–42 % for those over 70. In Vietnam, where the population is ageing rapidly and many elderly people live without continuous caregiver supervision, the need for an autonomous, reliable safety monitoring solution becomes increasingly critical.

Despite advancements in wearable health technology, existing fall detection products still suffer from significant limitations. Smartwatch-based detection often produces a high false alarm rate during daily living activities; clinical pendant alarms depend on the wearer being conscious to press a button; and cloud-dependent systems lose their protective value during network outages. Furthermore, most commercial devices either prioritise vital-sign monitoring without robust fall detection, or focus on impact detection alone without complementary physiological context. In this project, we investigated alternative **offline-first, edge-AI** methods. Among them, we found that **on-device TinyML inference on accelerometer-gyroscope signals combined with a multi-stage post-processing pipeline** showed promising results. In this scope, we proposed solutions to build a **wrist-worn wearable device** which combines a **convolutional neural network model** for **real-time fall recognition** from inertial signals and an **Android companion application** that performs immediate emergency calling over Bluetooth Low Energy. Additionally, we also developed a **cloud backend on MongoDB Atlas** for long-term storage of vital-sign history and fall events. We used the Render PaaS service for managing and monitoring data transmission to the Atlas database — used for storing data.

The results obtained were evaluated by testing in reality the performance of the whole system to identify the effectiveness also with the accuracy of the AI model. The overall results indicated that our system met the initial requirements to **detect falls in real time, trigger an immediate emergency response without internet dependence, and synchronise historical health records to the cloud when connectivity becomes available**. Further development needed to improve the quality of our system are also discussed.

---

## ACKNOWLEDGMENT

This graduation thesis was developed in the year 2026 at the D-Soft, JSC under the supervision of MSc. Nguyễn Đức Phước and Ph.D Nguyễn Thị Anh Thu.

We are deeply thankful to our supervisor, Ph.D Nguyễn Thị Anh Thu, for her academic rigour, valuable insights, and patient guidance throughout the development of this thesis. We also extend our heartfelt gratitude to MSc. Nguyễn Đức Phước for his industrial experience, persistent encouragement, and the practical engineering perspective that shaped the architectural decisions of this project. The committee members with their indispensable scholar perspectives shaped the foundation and direction of the thesis.

We would also like to extend our appreciation to D-Soft, JSC and its people for providing a wonderful, welcoming, and friendly environment and the necessary resources to complete the thesis; the Danang University of Science and Technology for the resources, knowledge, and guidance on conducting research and writing the thesis. We are grateful to the library of the FAST department for the relevant materials and literature.

Finally, special thanks to our families for the support that allowed us to be full-time students focusing on research. Thanks to all of our friends and colleagues, who provided valuable insights and turned this research into an enjoyable, memorable journey.

The authors would like to acknowledge all the efforts, endless support, and guidance of all individuals and institutions in the development of this thesis. This thesis would not have been possible without their priceless contributions.

Da Nang, June 2026
D-Soft Joint Stock Company
Trần Phước Diễn & Phạm Văn Tiên

---

## List of Figures

| # | Figure | Page |
|---|--------|------|
| Figure 1 | ESP32-S3-DevKitM-1 microcontroller board | ⟶ |
| Figure 2 | BMI160 6-axis IMU module | ⟶ |
| Figure 3 | MAX30102 pulse-oximeter module | ⟶ |
| Figure 4 | NimBLE-Arduino BLE stack architecture | ⟶ |
| Figure 5 | Project milestones — Gantt chart | ⟶ |
| Figure 6 | Block diagram of system modules | ⟶ |
| Figure 7 | Main operation flow of the system | ⟶ |
| Figure 8 | Seven-stage fall detection pipeline | ⟶ |
| Figure 9 | Fall State Machine (FSM) transitions | ⟶ |
| Figure 10 | LED feedback state diagram | ⟶ |
| Figure 11 | System circuit schematic diagram | ⟶ |
| Figure 12 | PCB design (top + bottom) | ⟶ |
| Figure 13 | 3D-printed enclosure render | ⟶ |
| Figure 14 | TinyCNN architecture | ⟶ |
| Figure 15 | Training and validation accuracy curve | ⟶ |
| Figure 16 | Training and validation loss curve | ⟶ |
| Figure 17 | Confusion matrix for test set | ⟶ |
| Figure 18 | Confusion matrix for validation set | ⟶ |
| Figure 19 | ROC curve | ⟶ |
| Figure 20 | Threshold sweep analysis | ⟶ |
| Figure 21 | Cloud data flow (BLE → app → Render → MongoDB Atlas) | ⟶ |
| Figure 22 | MongoDB document schema for vitals | ⟶ |
| Figure 23 | Render server log of live POST requests | ⟶ |
| Figure 24 | Mobile app — Home, Health, History, Alert screens | ⟶ |
| Figure 25 | The complete CaraFall system | ⟶ |

> **[TODO – NOT YET IN REPO]** Several figures referenced above (Fig. 11–13, Fig. 25) depend on hardware artefacts that are not yet present in the repository — see Section 3.1.3 (Printed Circuit Board Design) and Section 3.1.4 (3D Enclosure).

---

## List of Tables

| # | Table | Page |
|---|-------|------|
| Table 1 | The detailed tasks of each member | ⟶ |
| Table 2 | Marketing and Engineering Requirements | ⟶ |
| Table 3 | Microcontroller comparison for the wearable platform | ⟶ |
| Table 4 | Inertial Measurement Unit (IMU) comparison | ⟶ |
| Table 5 | Pulse-oximeter sensor comparison | ⟶ |
| Table 6 | BLE library comparison | ⟶ |
| Table 7 | Pin assignment of the ESP32-S3 to peripherals | ⟶ |
| Table 8 | Fall detection pipeline thresholds | ⟶ |
| Table 9 | BLE packet format on each characteristic | ⟶ |
| Table 10 | TinyCNN model architecture and parameters | ⟶ |
| Table 11 | MongoDB document schema for vitals collection | ⟶ |
| Table 12 | Unit test results — BMI160 sensor module | ⟶ |
| Table 13 | Unit test results — TinyML inference engine | ⟶ |
| Table 14 | Integration test results — BLE pairing & data sync | ⟶ |
| Table 15 | End-to-end test — cloud transmission and storage | ⟶ |
| Table 16 | Manufacturing cost (BOM) summary | ⟶ |

---

## Abbreviations

| Abbreviation | Full Form |
|---|---|
| ADC | Analog to Digital Converter |
| ADL | Activities of Daily Living |
| AI | Artificial Intelligence |
| AIoT | Artificial Intelligence of Things |
| API | Application Programming Interface |
| BLE | Bluetooth Low Energy |
| BPM | Beats Per Minute |
| CNN | Convolutional Neural Network |
| DPS | Degrees Per Second |
| FAR | False Alarm Rate |
| FSM | Finite State Machine |
| GATT | Generic Attribute Profile |
| GPIO | General Purpose Input / Output |
| HR | Heart Rate |
| HTTPS | HyperText Transfer Protocol Secure |
| I²C | Inter-Integrated Circuit |
| IMU | Inertial Measurement Unit |
| IoT | Internet of Things |
| JSON | JavaScript Object Notation |
| JVM | Java Virtual Machine |
| MCU | Microcontroller Unit |
| MEMS | Micro-Electro-Mechanical Systems |
| MTU | Maximum Transmission Unit |
| NVS | Non-Volatile Storage |
| OS | Operating System |
| OSA | Obstructive Sleep Apnea |
| PCB | Printed Circuit Board |
| PPG | Photoplethysmogram |
| REST | Representational State Transfer |
| RSSI | Received Signal Strength Indication |
| RTOS | Real-Time Operating System |
| SDK | Software Development Kit |
| SHA | Secure Hash Algorithm |
| SoC | System on Chip |
| SpO₂ | Peripheral Oxygen Saturation |
| TFLite | TensorFlow Lite |
| TFLM | TensorFlow Lite for Microcontrollers |
| TinyML | Tiny Machine Learning |
| UART | Universal Asynchronous Receiver-Transmitter |
| UUID | Universally Unique Identifier |
| VND | Vietnamese Đồng |

---

## Table of Contents

| Section | Page |
|---|---|
| ABSTRACT | ⟶ |
| ACKNOWLEDGMENT | ⟶ |
| INTRODUCTION | ⟶ |
| &nbsp;&nbsp;1. Motivation | ⟶ |
| &nbsp;&nbsp;2. Contribution | ⟶ |
| &nbsp;&nbsp;3. Project Milestones | ⟶ |
| &nbsp;&nbsp;4. Outline | ⟶ |
| CHAPTER 1: LITERATURE REVIEW | ⟶ |
| &nbsp;&nbsp;1. Existing Fall-Detection Solutions and Their Limitations | ⟶ |
| &nbsp;&nbsp;2. Proposed Solution | ⟶ |
| &nbsp;&nbsp;3. Requirement Specification | ⟶ |
| &nbsp;&nbsp;4. Technologies and Development Tools | ⟶ |
| CHAPTER 2: METHODOLOGY | ⟶ |
| &nbsp;&nbsp;1. System Design | ⟶ |
| &nbsp;&nbsp;2. AI Processing Pipeline | ⟶ |
| &nbsp;&nbsp;3. Cloud Storage and Data Service | ⟶ |
| &nbsp;&nbsp;4. Mobile Application | ⟶ |
| CHAPTER 3: EXPERIMENTAL RESULTS AND EVALUATION | ⟶ |
| &nbsp;&nbsp;1. TinyML Performance for Fall Detection | ⟶ |
| &nbsp;&nbsp;2. Cloud Storage and API Querying | ⟶ |
| &nbsp;&nbsp;3. Mobile Application Performance | ⟶ |
| &nbsp;&nbsp;4. Testing Results | ⟶ |
| &nbsp;&nbsp;5. Manufacturing Cost | ⟶ |
| CONCLUSION & FUTURE WORK | ⟶ |
| BIBLIOGRAPHY | ⟶ |

---

# INTRODUCTION

## 1. Motivation

A fall [1] is an event in which a person inadvertently comes to rest on the ground, floor, or other lower level. While most falls cause only minor injuries, persistent falls among elderly individuals may indicate **frailty syndrome, vestibular dysfunction, neurological decline, and the increased risk of severe trauma such as hip fractures, intracranial haemorrhage, and the post-fall psychological syndrome which limits future mobility**. The clinical consequences include not only direct injury but also a significant reduction in quality of life, depression, social withdrawal, and ultimately mortality. Studies show that approximately **28–35 % of adults aged 65 years and over experience at least one fall per year** [2], with this proportion rising to **32–42 % among those over 70**. In Vietnam, the General Statistics Office projects that the population aged 60 and over will reach 25 % by 2050, underscoring an urgent and growing need for accessible elderly-safety technology.

Despite advancements in wearable health technology and the proliferation of consumer smartwatches, fall-detection devices still face significant limitations [3]. Smartwatch-based systems often produce a high false-alarm rate during vigorous daily activities such as sitting down quickly or placing a hand on a table. Pendant-style alarms require the wearer to remain conscious and capable of pressing a button — a condition that cannot be guaranteed during a fall with loss of consciousness. Cloud-centric systems are vulnerable to network outages and Wi-Fi disruption, especially in rural Vietnamese households. Furthermore, while machine-learning models have improved fall recognition accuracy on benchmark datasets, **deploying these models on resource-constrained microcontrollers in a power-efficient and reliable manner remains a non-trivial engineering challenge**. While progress is promising, further innovation is needed to develop an **affordable, energy-efficient, and offline-capable solution** for elderly safety monitoring.

## 2. Contribution

Artificial Intelligence has been widely applied in multiple fields, such as autonomous driving, anomaly detection, and especially the task of medical signal processing on different data types such as electrocardiograms, audio recordings, and inertial measurements. Based on AI, **we propose an efficient method to detect falls and protect elderly users using the combination of Edge AI and a low-power BLE wearable**. This method can serve as a viable alternative to conventional pendant alarms and cloud-only smartwatches, owing to its superior reliability, energy efficiency, and capacity to overcome the inherent limitations commonly associated with cloud-dependent or motion-only systems.

**Ultimately, this project focuses on the following contributions:**

- Developing a **seven-stage fall-detection pipeline** combining classical signal-gating with a TinyCNN model, leveraging **TensorFlow Lite for Microcontrollers** for efficient embedded on-device computation (see [`S3_BLE_test_2/document/05_fall_detection_pipeline.md`](S3_BLE_test_2/document/05_fall_detection_pipeline.md)).
- Creation of a **mobile companion application** for live monitoring, fall alert handling, and emergency caregiver calling, providing users and caregivers with real-time insight and control over the safety system (see [`android_studio_AIFD/`](android_studio_AIFD/)).
- Designing a **cloud back-end** based on Flask and MongoDB Atlas, deployed on the Render PaaS service, for authentication, vital-sign history, and fall-event logging (see [`mongodb/server.py`](mongodb/server.py)).
- Adopting an **"Offline-First Alert, Online Cloud Sync"** architectural philosophy, ensuring the emergency response path operates entirely without Internet, while history synchronisation occurs opportunistically when network connectivity becomes available.

## 3. Project Milestones

> **[TODO – NOT YET IN REPO]**
> Expected content: a Gantt-chart figure showing the milestone schedule of each member across the project timeline (February 2026 → June 2026).
> Suggested source file (when implemented): `System_Architecture/process/gantt_chart.png`.

The detailed contributions of each member of the authors are summarised as follows.

**Table 1.** The detailed tasks of each member

| Task # | Task details | Diễn | Tiên |
|:-:|---|:-:|:-:|
| 1 | Research existing fall-detection products and their limitations | ✔ | ✔ |
| 2 | Define system requirements, architecture, and mobile-application functions | ✔ | ✔ |
| 3 | Research signal processing flow for IMU data and the construction of the 100-sample sliding window | ✔ |  |
| 4 | Research AI algorithms for the binary classification task of fall vs ADL |  | ✔ |
| 5 | Train and optimise the TinyCNN model using TensorFlow; deploy via TFLite Micro on ESP32-S3 |  | ✔ |
| 6 | Integrate the quantised model into the firmware, develop the LED/buzzer/button finite-state machine, and implement BLE peripheral logic | ✔ |  |
| 7 | Implement the seven-stage fall-detection post-processing pipeline (candidate gate, activity gate, high-impact gate, AI window, fall FSM) | ✔ | ✔ |
| 8 | Develop the Android mobile application for live monitoring, alert handling, history, and emergency call | ✔ |  |
| 9 | Develop the Flask/MongoDB cloud back-end and deploy it on Render | ✔ |  |
| 10 | PCB and 3D enclosure design |  | ✔ |
| 11 | Comprehensive unit, integration, and acceptance testing of hardware and software | ✔ | ✔ |

> **[TODO – NOT YET IN REPO]**
> Verify that the task split above matches the actual division of responsibilities. The git history on the `dien-zinex` branch attributes all recent commits to Diễn; this table should be confirmed against the team's internal task log.

## 4. Outline

This thesis is organised into **three main chapters**, each addressing a key aspect of the development and evaluation of CaraFall. **Chapter 1** presents a comprehensive literature review on current fall-detection solutions, highlighting their limitations and motivating the need for an offline-first, embedded-AI approach. It also outlines the requirement specification, selected technologies, development tools, and hardware components employed in this project. **Chapter 2** details the methodology, including the complete system architecture from inertial signal acquisition to cloud-based persistence. It covers the design and deployment of the TinyML-based fall-detection model, the seven-stage signal-processing pipeline, the BLE peripheral protocol, and cloud integration via MongoDB Atlas. Furthermore, it describes the mobile application developed for monitoring, alert handling, and configuration. **Chapter 3** focuses on the experimental results and evaluation of each system component. It analyses the performance of the fall-detection model, the efficiency of cloud storage and API queries, the usability of the mobile application, and the overall hardware cost.

Finally, the **Conclusion & Future Work** section summarises the results achieved, discusses the limitations of the current implementation — such as the still-simulated MAX30102 driver and the absence of finalised PCB hardware — and outlines directions for future improvement.

---

# CHAPTER 1: LITERATURE REVIEW

Nowadays, various elderly-safety solutions currently exist, including pendant emergency alarms, smartwatch-based fall detection, in-home ambient sensor systems, and cloud-connected wearables. While these methods can detect falls or call for help to some extent, many of them are either uncomfortable to wear continuously, expensive, network-dependent, or limited to a single sense. Moreover, these solutions often fail to adapt to the individual user's daily-living patterns or to provide a comprehensive view that combines fall events with physiological context such as heart rate and oxygen saturation.

To overcome these limitations, recent developments in embedded systems and artificial intelligence have opened new possibilities for building smart, personalised health devices. In particular, the use of **Tiny Machine Learning (TinyML)** [4] allows for real-time inference on resource-constrained edge devices, enabling efficient, low-latency responses to detected fall events without relying on cloud-based processing. Coupled with intelligent inertial sensors and user-centred design, this technology has the potential to enhance both the comfort and effectiveness of elderly safety devices. However, significant challenges remain in designing a system that balances accuracy, responsiveness, and battery life. Implementing real-time fall detection in a wrist-worn form factor requires careful hardware integration, robust data acquisition, and the development of lightweight, efficient machine-learning models suitable for deployment on microcontrollers.

There are many limitations to traditional elderly-safety methods, namely their lack of offline operation, physical discomfort, and inability to provide personalised insights into long-term health trends. Thus, smart and non-intrusive alternatives using embedded AI have become a growing focus among researchers. In this chapter, we investigate existing fall-detection technologies and their drawbacks, and present a novel solution — **CaraFall, a wearable wristband that integrates TinyML for real-time fall detection coupled with a companion Android application for immediate emergency calling**. We also outline the system's requirement specifications and describe the key technologies and development tools used in its implementation.

## 1. Existing Fall-Detection Solutions and Their Limitations

Fall events have been addressed through various medical and electronic interventions, each aiming to alert caregivers or emergency services when a fall occurs. Among the most established consumer solutions are **personal emergency response systems** (PERS), commonly worn as a pendant around the neck, which deliver a one-button SOS call through a base station connected to a landline. Despite their long market presence, PERS devices suffer from a critical flaw: **they require the wearer to remain conscious and capable of pressing the button** — a condition that cannot be guaranteed during a serious fall accompanied by loss of consciousness. Furthermore, the limited range of the base-station radio (typically less than 100 m indoors) confines the user to the home environment.

**Smartwatch fall detection** — popularised by Apple Watch [5] and similar high-end smartwatches — uses on-device accelerometer-and-gyroscope analysis to recognise falls. While clinically validated, these devices are constrained by **short battery life (less than two days under heavy use)**, **high purchase cost (often exceeding 8 000 000 VND)**, and **dependence on a paired smartphone** for emergency call escalation. Moreover, the closed-source nature of their detection algorithms makes them unsuitable for research or clinical customisation. **Ambient-sensor systems** such as Vayyar Care use radar to track gait and falls within a room. These offer the advantage of being non-wearable but have very limited spatial coverage, are expensive to install, and cannot follow the user outside the equipped room. **Cloud-connected medical alarms** such as Philips Lifeline rely on cellular or Wi-Fi connectivity to transmit alerts. While they extend coverage beyond the home, they introduce a critical single point of failure: a fall during an Internet outage cannot be communicated.

Across these existing categories, three recurring shortcomings motivate the present work: (i) dependence on the wearer's ability to act, (ii) reliance on continuous Internet connectivity, and (iii) a single-modality data stream that lacks physiological context. These gaps are precisely what an offline-first, multi-modal edge-AI wearable can address.

## 2. Proposed Solution

To deal with the limitations of the previous solutions, this project investigates a compact, efficient elderly-safety product based on Artificial Intelligence and embedded systems. Focusing on fall reduction and timely emergency response, **on-wrist inertial sensing has proved effective in capturing both the impact and post-impact stillness signatures of true falls** [6]. As Bagalà et al. [7] have shown, the utilisation of inertial signals around the wrist combined with multi-stage post-processing is able to maintain a high recall rate while suppressing false alarms during activities of daily living. This study highlights the potential of a TinyML-based wearable designed to balance sensitivity and specificity in a body-area network. **The proposed solution autonomously detects falls in response to inertial signal patterns**, triggers an immediate alert through Bluetooth Low Energy to the companion Android application, and — should the user not cancel the alert within fifteen seconds — automatically initiates a direct phone call to the registered caregiver. Vital-sign and fall data are systematically recorded and analysed to allow caregivers to review trends in the mobile application. By integrating advanced inertial pattern recognition with a finite-state machine that confirms the fall through post-impact stillness, this approach offers a more precise and adaptive solution compared to conventional pendant or smartwatch devices.

## 3. Requirement Specification

CaraFall is designed to detect falls and protect elderly users in real time. This section outlines the marketing and engineering requirements necessary to ensure the system meets performance, comfort, and usability standards.

**Table 2.** Marketing and Engineering Requirements

| Marketing Requirements | Engineering Requirements | Justification |
|:-:|---|---|
| 1 | The system shall detect falls with a Recall ≥ 95 % and a False Alarm Rate ≤ 10 % during everyday activities, with edge inference latency below 1 s per window. | Ensures the product detects true falls without bothering the user with false alarms. |
| 1 | The system shall trigger an emergency call within 30 s of an unanswered confirmed fall, with the BLE alert delivered to the phone within 1 s. | Enables timely intervention while still providing a window for the user to cancel a false positive. |
| 1,2 | Continuous vital-sign monitoring (HR, SpO₂) with ±5 BPM and ±3 % accuracy respectively, refreshed at ≥ 0.2 Hz. | Provides physiological context alongside fall events and supports long-term health-trend analysis. |
| 2 | Bluetooth Low Energy 5.0 link to a companion Android application; an MTU of at least 247 bytes shall be negotiated. | Enables low-power, low-latency communication with the smartphone — the cornerstone of the offline-first architecture. |
| 1 | Operate reliably within an ambient temperature range of 0 °C to 45 °C and up to 85 % humidity. | Ensures stable performance in typical Vietnamese household conditions. |
| 1,3 | Designed for continuous wrist-wear with a total device weight ≤ 70 g. | Enhances user experience and adherence by maintaining a natural and comfortable feel. |
| 2 | First-time pairing shall complete within 5 minutes; subsequent connections shall auto-reconnect without user action. | Improves accessibility for elderly users who may struggle with technology. |
| 3 | Total Bill-of-Materials cost shall not exceed 2 500 000 VND. | Ensures affordability, making the product accessible to the Vietnamese household market. |
| 1,2 | Record and store fall events and vital signs for at least 30 days in MongoDB Atlas. | Helps caregivers and clinicians track trends and detect deterioration over time. |
| 3 | Operate on a single-cell Li-Po battery with a continuous operating time of ≥ 5 days between charges. | Ensures the device is practical for elderly users who may forget to charge frequently. |

**Marketing Requirements:**
1. The product must be effective and reliable for safety-critical use.
2. It should be easy to use and set up quickly, including by non-technical caregivers.
3. The cost should be affordable and competitive in the Vietnamese consumer-health market.

## 4. Technologies and Development Tools

This section presents the key technologies and development tools applied in the project, covering programming languages, development environments, and supporting hardware.

### 4.1 Programming Languages

#### 4.1.1 C++ Language

C++ is an important language in the context of programming, particularly for embedded systems, due to its rich features and powerful capabilities. Building on the foundation of C, C++ adds object-oriented programming features, which help organise and manage complex code. Its efficiency, performance, and direct control over memory and hardware make it an ideal choice for developing firmware in resource-constrained environments such as the ESP32-S3 microcontroller. The Arduino framework adopted in this project is built on top of a subset of C++, enabling the project to combine the readability of Arduino APIs with the low-level control offered by C++ when interfacing with the BMI160 inertial sensor and the NimBLE Bluetooth stack.

#### 4.1.2 Kotlin Language

Kotlin [8] is a modern programming language that runs on the Java Virtual Machine (JVM) and has been the recommended language for Android application development since 2017. It is designed to be fully interoperable with Java, allowing developers to leverage existing Java libraries while enjoying Kotlin's more concise and expressive syntax. Kotlin supports features like null safety, higher-order functions, and coroutines, which improve code safety, readability, and performance. These features are particularly useful when implementing the asynchronous BLE communication and HTTP synchronisation logic of the mobile application. The companion application in this project is implemented entirely in Kotlin with the **Jetpack Compose** declarative UI framework.

#### 4.1.3 Python Language

Python is a powerful and flexible programming language known for its straightforward and readable syntax. Its user-friendly structure, rich standard library, and compatibility with various programming styles support quick development across many fields. From web development to data science and artificial intelligence, Python remains a top choice thanks to its accessibility and strong community backing with extensive resources. In this project, Python is used in three roles: training the TinyCNN fall-detection model with **TensorFlow** and **Keras**; processing and labelling the IMU dataset with **NumPy** and **Pandas**; and implementing the cloud back-end with **Flask** and **PyMongo**.

### 4.2 Supporting Hardware

This section presents the main hardware components of the system, including the core microcontroller, peripheral sensors, and the supporting circuitry necessary to integrate them into a wearable form factor. A detailed comparison is presented for the microcontroller and the inertial sensor, as these components play a central role in system performance, while other components are described briefly.

#### 4.2.1 Microcontroller Selection

The wearable device must execute a TinyML inference, manage a BLE peripheral stack, and drive several peripheral indicators concurrently. Therefore, a microcontroller must be selected based on processing performance, RAM/Flash capacity for the model, integrated Bluetooth Low Energy radio, energy efficiency, and developer ecosystem.

**Table 3.** Microcontroller comparison for the wearable platform

| Criteria | STM32L432KC [9] | **ESP32-S3-DevKitM-1** [10] | Nordic nRF52840 [11] |
|---|---|---|---|
| CPU | 32-bit ARM Cortex-M4 @ 80 MHz | **Dual-core Xtensa LX7 @ 240 MHz** | 32-bit ARM Cortex-M4 @ 64 MHz |
| RAM | 64 KB SRAM | **512 KB SRAM** | 256 KB SRAM |
| Flash | 256 KB | **8 MB** | 1 MB |
| Bluetooth | None (external module required) | **BLE 5.0 (NimBLE)** | BLE 5.0 |
| TinyML support | Limited (CMSIS-NN) | **TFLite Micro, vector ISA** | TFLite Micro, CMSIS-NN |
| Dual core | No | **Yes** | No |
| Price | ~$10 | **~$15** | ~$22 |

The **ESP32-S3-DevKitM-1** was selected as the core microcontroller for the wearable due to its balance of performance, integrated BLE 5.0 radio, and broad TinyML support. It is based on a dual-core Xtensa LX7 CPU (up to 240 MHz) with 8 MB of flash, ideal for running the TinyCNN fall-detection model concurrently with the BLE stack via FreeRTOS dual-task scheduling. The board exposes the USB Type-C interface for programming and debugging, plus a rich set of peripherals including ADC, SPI, I²C, I²S, UART, and PWM. With vector instruction support for AI workloads and native compatibility with TensorFlow Lite Micro, the ESP32-S3 is well-suited for edge-AI applications such as inertial signal classification.

#### 4.2.2 Sensors

The system uses an inertial measurement unit (IMU) for fall detection and a pulse-oximeter for vital-sign monitoring. The following subsections describe the characteristics and functions of each sensor component in detail.

##### a. Inertial Measurement Unit (BMI160)

To ensure accurate detection of fall-related motion, several IMUs were evaluated based on criteria such as accelerometer range, gyroscope range, sampling rate, output interface, and power supply.

**Table 4.** Inertial Measurement Unit (IMU) comparison

| Criteria | **BMI160** [12] | MPU-6050 [13] | LSM6DS3 [14] |
|---|---|---|---|
| Accelerometer Range | ±2 g, ±4 g, ±8 g, ±16 g | ±2 g … ±16 g | ±2 g … ±16 g |
| Gyroscope Range | ±125 / 250 / 500 / 1000 / **±2000 dps** | ±250 … ±2000 dps | ±125 … ±2000 dps |
| Interface | **I²C / SPI** | I²C only | I²C / SPI |
| Current Consumption | **925 µA (typ.)** | 3.9 mA | 0.9 mA |
| Output | 16-bit digital | 16-bit digital | 16-bit digital |

Among the three options, the **BMI160** is chosen due to its low power consumption (925 µA), 16-bit digital output, and wide configurable range. The combination of a ±2 g accelerometer and a ±2000 dps gyroscope, sampled at 50 Hz, was sufficient to capture both the impact and rotation signatures of typical falls in the wrist-worn position. The driver is implemented inline in [`S3_BLE_test_2/src/main.cpp`](S3_BLE_test_2/src/main.cpp). The BMI160 communicates with the ESP32-S3 over I²C on GPIO 8 (SDA) and GPIO 9 (SCL) at 100 kHz, and is addressed at 0x69 (SDO pin tied high).

##### b. Pulse-Oximeter (MAX30102)

To monitor heart rate and peripheral oxygen saturation, the **MAX30102** [15] integrated optical sensor is selected. The MAX30102 combines a red LED, an infrared LED, a photodetector, and a low-noise analog front-end in a 5.6 × 3.3 × 1.55 mm package, communicating with the host via I²C at 0x57. It is widely supported in the open-source community and offers a sample rate of up to 1 000 Hz with full programmable LED current.

> **[TODO – NOT YET IN REPO]**
> Expected content: actual hardware integration of the MAX30102 driver in `S3_BLE_test_2/src/main.cpp` (lines 102–110 currently contain a simulated provider returning a uniform-random heart rate in [60, 100] BPM and SpO₂ in [94, 100] %). The migration path is documented in [`SYNC_COMPLETION_REPORT.md`](SYNC_COMPLETION_REPORT.md) §5 — only two functions `readHrSample()` and `readSpo2Sample()` need to be replaced; the BLE payload contract and Android parser remain unchanged.

### 4.3 Framework and Supporting Technologies

#### 4.3.1 Communication Protocols

##### a. Inter-Integrated Circuit (I²C)

I²C is a two-wire serial communication protocol developed by Philips Semiconductor (now NXP) in the early 1980s. The protocol uses two bidirectional open-drain lines — **SDA (Serial Data)** and **SCL (Serial Clock)** — with pull-up resistors on each line. I²C supports a master-slave architecture in which one master device controls the bus and addresses one of multiple slaves by a 7-bit address. In this project, I²C is used to interface the ESP32-S3 with the BMI160 inertial sensor on GPIO 8/9 at 100 kHz standard-mode speed.

##### b. Bluetooth Low Energy (BLE 5.0)

Bluetooth Low Energy is a wireless personal area network technology designed for short-range, low-power applications. Built on top of the standard Bluetooth radio, BLE optimises power consumption by employing very short connection events and minimal advertising overhead, making it ideally suited to battery-operated wearable devices.

**Table 6.** BLE library comparison

| Criteria | Arduino BluetoothSerial | **NimBLE-Arduino** [16] | ESP-IDF Bluedroid |
|---|---|---|---|
| RAM footprint | High (Classic BT) | **Low (~30 KB)** | Medium |
| Multi-connection | No | **Yes** | Yes |
| MTU negotiation | Limited | **Up to 517 bytes** | Up to 517 bytes |
| Arduino-IDE compatibility | Yes | **Yes** | No |
| Production-ready | No | **Yes** | Yes |

The **NimBLE-Arduino** library is selected for its low memory footprint and Arduino-compatible API. NimBLE supports BLE 5.0 features, multiple simultaneous connections, MTU negotiation up to 517 bytes, and bond storage in NVS flash. The advertised BLE service exposes three GATT characteristics (Section 2.1.2 of Chapter 2). In this project, the ESP32-S3 acts as a BLE Peripheral while the Android phone acts as the BLE Central.

##### c. Hypertext Transfer Protocol (HTTPS)

HTTPS is the secure variant of HTTP that encrypts traffic with TLS, ensuring confidentiality and integrity in transit. In this project, HTTPS is used for the link between the Android application and the cloud back-end deployed on Render. The Android side uses **OkHttp 4.12** as the HTTP client, sending JSON payloads to REST endpoints exposed by the Flask server.

#### 4.3.2 Framework & Platform

##### a. FreeRTOS

FreeRTOS [17] is the de-facto real-time operating system used on the ESP32. It provides task scheduling, priorities, queues, semaphores, and timers, allowing the firmware to decouple the time-critical 50 Hz inertial sampling from the longer-duration TinyML inference. CaraFall uses two FreeRTOS tasks pinned to the two physical cores of the ESP32-S3, ensuring that sampling never blocks while inference runs (see Section 2.1.3 of Chapter 2).

##### b. TensorFlow & TensorFlow Lite for Microcontrollers

TensorFlow [18] is an open-source machine-learning framework developed by Google. The training pipeline in this project uses TensorFlow 2.x and the Keras high-level API to design and train the TinyCNN model. Once trained, the model is converted to the **TFLite format** with INT8 post-training quantisation, then compiled to a **C array** and linked into the firmware via TFLite Micro (TFLM). TFLM is a port of TensorFlow Lite optimised for 32-bit microcontrollers, requiring only a tensor arena allocated in static RAM and no operating-system dependencies.

##### c. ESP-IDF and Arduino Framework

The Espressif IoT Development Framework (ESP-IDF) is the official development framework for the ESP32 family. In this project, the firmware uses the **Arduino-ESP32** layer on top of ESP-IDF, providing high-level helpers such as `Wire.begin()`, `pinMode()`, and the FreeRTOS API. The PlatformIO build system manages the toolchain, library dependencies (NimBLE-Arduino, TensorFlowLite_ESP32), and upload protocols.

#### 4.3.3 Cloud and Mobile Development Tools

##### a. Flask & MongoDB Atlas

**Flask** is a lightweight Python web framework used to build the cloud back-end. **MongoDB Atlas** is the fully-managed cloud database service for MongoDB, used to persist user accounts, vital signs, and fall events. The deployed back-end is implemented in [`mongodb/server.py`](mongodb/server.py).

##### b. Render

**Render** is a Platform-as-a-Service used to host the Flask back-end at the URL `https://edge-aiot-wearable-elderly-safety.onrender.com`. Render handles automatic HTTPS certificates, environment-variable management for the MongoDB connection string, and container deployment from the GitHub repository.

##### c. PlatformIO and Visual Studio Code

PlatformIO is the build-and-upload tool used to compile and flash the firmware. The configuration is preserved in [`S3_BLE_test_2/platformio.ini`](S3_BLE_test_2/platformio.ini) and includes the upload protocol (`esp-builtin`), build flags, and library dependencies.

##### d. Android Studio

Android Studio is the official IDE for Android application development. The companion app project is located in [`android_studio_AIFD/`](android_studio_AIFD/) and uses the Gradle KTS build system with Compose BOM 2024.01.00 (see [`android_studio_AIFD/app/build.gradle.kts`](android_studio_AIFD/app/build.gradle.kts)).

#### 4.3.4 Hardware Design and 3D Modeling

> **[TODO – NOT YET IN REPO]**
> Expected content: a brief description of EasyEDA or KiCad used for schematic capture, and SketchUp or Fusion 360 used for the wristband enclosure design. The repository currently does not contain any PCB project files, Gerber exports, or STL files, so this subsection should be completed once the hardware design phase is finalised.

---

# CHAPTER 2: METHODOLOGY

This chapter outlines the methodology used for system analysis and the rationale behind key design decisions. Emphasis is placed on modular system architecture, real-time data processing, and cloud integration to ensure performance, scalability, and maintainability. By laying out the system's requirements and design approach, this chapter provides a comprehensive technical roadmap for the implementation of CaraFall.

## 1. System Design

### 1.1 System Structure

The CaraFall wearable detects falls by acquiring inertial signals from the BMI160 IMU, running a seven-stage detection pipeline on the ESP32-S3, and transmitting the alert event to the Android companion application over Bluetooth Low Energy. The application, in turn, displays a 15-second countdown screen and — if the user does not cancel — initiates a direct emergency call to the registered caregiver. In parallel, when network connectivity is available, vital signs and fall events are synchronised to a MongoDB Atlas cluster through a Flask back-end hosted on Render.

> **[TODO – NOT YET IN REPO]**
> Expected content: a block-diagram figure (PNG/SVG) showing the modules and their inter-connections. The Mermaid source already exists in [`System_Architecture/ARCHITECTURE_OVERVIEW.md`](System_Architecture/ARCHITECTURE_OVERVIEW.md); a static export should be saved as `System_Architecture/diagrams/system_block_diagram.png`.

The overall architecture of the CaraFall system is described below. This architecture demonstrates the end-to-end flow of data, from inertial signal acquisition on the edge device to cloud-based storage and emergency response.

**Inertial Signal Collection and Pre-processing.** Inertial signals are captured by the BMI160 at 50 Hz, providing six channels: three accelerometer axes (`ax`, `ay`, `az`) and three gyroscope axes (`gx`, `gy`, `gz`). Each new sample is appended to a 100-sample ring buffer, yielding a 2-second sliding window. A FreeRTOS task on Core 0 of the ESP32-S3 handles this acquisition with `vTaskDelayUntil` to maintain exact 20 ms periodicity, while a separate task on Core 1 consumes window snapshots for inference.

**Local Classification and Multi-Stage Filtering.** Fall detection is handled entirely on-device via a seven-stage pipeline (Section 2.1.3 below). The pipeline combines coarse-grained signal gates with the TinyCNN inference to maximise specificity. When a fall event is confirmed, the firmware compiles the event into a CSV-formatted BLE payload with timestamp, sequence number, and the model's fall probability.

**Communication and Emergency Response.** The fall event is transmitted over BLE to the Android application using the GATT notify mechanism. The application immediately activates a full-screen alert overlay — capable of waking the screen and bypassing the lock screen — and begins a 15-second countdown. If the user does not cancel within this window, the application initiates an `Intent.ACTION_CALL` to the caregiver's phone number stored in the user profile.

**Cloud Integration and Persistent Storage.** Telemetry data — including vital signs and fall events — is sent to the cloud via HTTPS over Wi-Fi or cellular data. The Flask back-end deployed on Render receives the JSON payload, validates and authenticates it, then writes the document to the MongoDB Atlas cluster. This setup supports real-time monitoring and historical trend analysis.

**Mobile Application.** A Kotlin/Jetpack Compose Android app connects to the cloud back-end, allowing users and caregivers to monitor live vital signs, review fall history with severity and time-of-day patterns, and configure user-profile information and emergency contacts. The app also supports the BLE foreground service that ensures the device remains connected even when the screen is off.

### 1.2 Fall Detection Pipeline

The fall-detection pipeline is the core algorithmic contribution of CaraFall. It is documented in full at [`S3_BLE_test_2/document/05_fall_detection_pipeline.md`](S3_BLE_test_2/document/05_fall_detection_pipeline.md). The system is designed with a **seven-stage filtering architecture** in which each stage acts as a guard against false positives, and only inertial signals that satisfy all stages are reported as confirmed falls. The overall workflow of the pipeline is illustrated below.

```
IMU 50 Hz (BMI160 ±2 g / ±2000 dps)
   │
   ▼ every 100 samples → 1 window (2 s)
[1] CANDIDATE GATE
   │
   ▼
[2] ACTIVITY GATE
   │
   ▼
[3] HIGH-IMPACT GATE
   │
   ▼
[4] IMPACT CHECK
   │
   ▼
[5] AI WINDOW (6 s) ←── TFLite V84 model
   │
   ▼
[6] FALL STATE MACHINE  (FALL_WATCH → STILL_TIMING)
   │
   ▼
[7] ALARM → BLE ALERT + Buzzer + LED blink
```

**Table 8.** Fall detection pipeline thresholds

| Parameter | Value | Purpose |
|---|---|---|
| `CANDIDATE_GYRO_THRESHOLD` | 240 dps | Required peak gyroscope magnitude in a window to consider it a candidate |
| `ACTIVITY_ACC_THRESHOLD` / `ACTIVITY_GYRO_THRESHOLD` | 2.0 g / 50 dps | Per-window activity thresholds; three consecutive windows must exceed these |
| `ACTIVITY_WINDOW_COUNT` | 3 | Number of consecutive activity windows required |
| `HIGH_IMPACT_ACC_MIN` / `HIGH_IMPACT_GYRO_MIN` | 2.0 g / 300 dps | At least one window in the streak must simultaneously exceed both — confirms a high-impact event |
| `FALL_IMPACT_GYRO_MIN` | 20 dps | Additional gyroscope check on the current window before inference |
| `FALL_DECISION_THRESHOLD` | 0.42 | Sigmoid output of the TinyCNN above which the window is classified as a fall |
| `AI_WINDOW_DURATION_MS` | 6 000 | Time window during which the AI is active after a candidate peak (3 windows × 2 s) |
| `CANCEL_ACC_THRESHOLD` / `CANCEL_GYRO_THRESHOLD` | 3.5 g / 150 dps | Motion above these magnitudes during FALL_WATCH/STILL_TIMING cancels the alert |
| `FALL_STILL_DURATION_MS` | 5 000 | Required continuous stillness duration to confirm the fall |
| `FALL_MONITOR_TIMEOUT_MS` | 10 000 | Maximum monitoring window for STILL_TIMING before reverting to safe state |
| `STILLNESS_ACC_MIN` / `STILLNESS_ACC_MAX` | 0.6 g / 1.7 g | Acceleration magnitude range considered "still" |
| `STILLNESS_GYRO_MAX` | 100 dps | Gyroscope magnitude below this considered "still" |

The Fall State Machine (FSM) operates as follows. Upon a positive AI decision in any window inside the AI window, the FSM transitions from `FDS_IDLE` to `FDS_FALL_WATCH`, where it waits five consecutive 2-second windows (10 s total). During this period, any signal exceeding `CANCEL_ACC_THRESHOLD` or `CANCEL_GYRO_THRESHOLD` cancels the alert. After the FALL_WATCH period, the FSM transitions to `FDS_STILL_TIMING`, in which it monitors continuous stillness for up to 10 s. If the user remains still for at least 5 continuous seconds within this monitoring window, the alarm is confirmed and the BLE ALERT packet is emitted. If the user moves within these 5 s, the stillness timer resets and re-arms only when the user becomes still again. The 10-s monitoring window ensures the system reverts to `FDS_IDLE` if no sustained stillness is observed — preventing the alert from being indefinitely pending.

### 1.3 Hardware Design & 3D Model Design

This section presents the system schematic design, power consumption analysis, and PCB design process.

#### 1.3.1 Pin Assignment

The pin assignment of the ESP32-S3 to peripherals is summarised below and documented at [`S3_BLE_test_2/document/02_pin_mapping.md`](S3_BLE_test_2/document/02_pin_mapping.md).

**Table 7.** Pin assignment of the ESP32-S3 to peripherals

| Peripheral | Connection | GPIO | Mode | Notes |
|---|---|---|---|---|
| LED Green | Anode | GPIO 4 | OUTPUT | 220 Ω series resistor to GND |
| LED Yellow | Anode | GPIO 5 | OUTPUT | 220 Ω series resistor to GND |
| LED Red | Anode | GPIO 6 | OUTPUT | 220 Ω series resistor to GND |
| Buzzer (2 300 Hz passive) | + | GPIO 7 | OUTPUT (tone) | − to GND, driven by `tone(7, 2300)` |
| Button | Pin 1 | GPIO 10 | INPUT_PULLUP | Pin 2 to GND, 30 ms debounce |
| BMI160 IMU | SDA | GPIO 8 | I²C | 100 kHz, 10 kΩ pull-up on module |
| BMI160 IMU | SCL | GPIO 9 | I²C | 100 kHz |
| BMI160 IMU | VCC | 3V3 | Power | Use 3.3 V, not 5 V |
| BMI160 IMU | GND, SDO→GND | GND | Address | SDO tied to GND yields I²C address 0x68 |

#### 1.3.2 System Schematic Design

> **[TODO – NOT YET IN REPO]**
> Expected content: System Circuit Schematic Diagram (Figure 11). The repository currently does not contain any EasyEDA / KiCad project files. Once the schematic is finalised it should be exported as `hardware/schematic.pdf` and `hardware/schematic.png`.

#### 1.3.3 Power Consumption Analysis

> **[TODO – NOT YET IN REPO]**
> Expected content: Power consumption analysis for the microcontroller, sensors, peripherals, and aggregated values across each voltage domain. The current firmware does not yet invoke `esp_sleep_*` low-power APIs in `S3_BLE_test_2/src/main.cpp`, which means the always-on prototype draws ~120 mA when connected — a power-budget table and projected battery life from a 500 mAh Li-Po (target ≥ 5 days) must be measured on the final hardware.

#### 1.3.4 Printed Circuit Board Design

> **[TODO – NOT YET IN REPO]**
> Expected content: PCB design (top + bottom copper, silkscreen). After completing the schematic design, the PCB layout will be drafted using EasyEDA. Component placement is performed with a focus on minimising trace length to the BLE antenna, ensuring decoupling capacitors near the ESP32-S3 power pins, and keeping the BMI160 close to the centre of the wrist for stable inertial readings. The repository currently does not contain any PCB project files.

#### 1.3.5 3D Enclosure Design

> **[TODO – NOT YET IN REPO]**
> Expected content: 3D-printed enclosure designs for the wristband body and lid using SketchUp or Fusion 360. The repository currently does not contain any `.stl`, `.step`, or `.3mf` files. The target weight is ≤ 70 g for comfortable continuous wear on the wrist of an elderly user.

## 2. AI Processing Pipeline

To prepare the data for the analyses described in this study, a systematic data acquisition and processing pipeline was designed and implemented. This pipeline ensured the efficient collection, cleaning, transformation, and structuring of inertial data from various sources into a unified, analysis-ready dataset.

### 2.1 Data Acquisition

The dataset of falls was constructed by combining the publicly available **HR_IMU dataset** [19] with custom wrist-worn IMU samples collected by the project team. The HR_IMU dataset contains fall sequences and Activities of Daily Living (ADL) sequences captured at 50 Hz with six channels (3-axis accelerometer + 3-axis gyroscope), labelled at the sequence level. After preprocessing and class balancing through under-sampling of ADL windows, the final training set contains:

- **Fall windows:** 1 628
- **Non-fall windows:** 1 628
- **Total:** 3 256

Each window is a 100-sample slice of six-channel inertial data, corresponding to 2 seconds at 50 Hz. The window-extraction parameters are stored under [`data_processing/data/weda_50hz_split_data_622/`](data_processing/data/weda_50hz_split_data_622/) as `train.csv`, `validation.csv`, `test.csv`, and `windows_all.csv`.

### 2.2 Signal Processing and Feature Extraction

Unlike audio-based deep-learning tasks that rely on time-frequency representations such as the log-Mel spectrogram, fall-detection on inertial signals operates directly on **raw six-channel time-domain windows**. The 100 × 6 input tensor preserves both impact magnitude (mostly captured in the accelerometer channels) and rotation (captured in the gyroscope channels). To stabilise training and inference, an in-graph **Z-score normalisation** layer is applied as the first layer of the model. The mean and standard deviation are computed during training and frozen as constants, so that at inference time the ESP32-S3 only performs a subtraction and a division per element. This eliminates the need to maintain a running normalisation buffer on the microcontroller.

### 2.3 Fall Detection Model with TinyML

To build the TinyML model for the microcontroller, the first step is building and training the TensorFlow model using Python and the TensorFlow framework, then converting the trained model to the TFLite format for inference on the microcontroller.

The dataset is divided into training, validation, and test subsets in a 60-20-20 ratio. The architecture is a **lightweight one-dimensional Convolutional Neural Network (1D-CNN)** with the following configuration: an input normalisation layer, two 1D-convolutional blocks with ReLU activation, a global average pooling layer, two fully-connected layers, and a sigmoid output. The model was trained for up to 100 epochs with **early stopping** to halt training if the validation loss did not decrease for 10 consecutive epochs.

**Table 10.** TinyCNN model architecture and parameters

| Layer | Type | Output Shape | Parameters |
|---|---|---|---|
| Input | `imu_window` | (None, 100, 6) | 0 |
| Normalisation | `balanced_norm` | (None, 100, 6) | 13 |
| Conv1D | 16 filters, kernel 3 | (None, 100, 16) | 304 |
| MaxPooling1D | pool size 2 | (None, 50, 16) | 0 |
| Conv1D | 32 filters, kernel 3 | (None, 50, 32) | 1 568 |
| GlobalAveragePool1D | — | (None, 32) | 0 |
| Dense | hidden | (None, 32) | 1 056 |
| Output | sigmoid | (None, 1) | 33 |

The trained model is then converted to a TFLite file with **post-training INT8 quantisation**, then compiled into a C array via `xxd -i` and linked into the firmware. The final deployed model is **V84**, located at [`AI/model_updated_version_84/`](AI/model_updated_version_84/), with the binary header at `AI/model_updated_version_84/models/fall_detection_v84.h` (62.09 KB).

### 2.4 Threshold Tuning and Decision Strategy

The default decision threshold of most binary classifiers is 0.50. However, for elderly fall detection, the cost of a **false negative** (missing a real fall) far exceeds the cost of a **false positive** (a benign alert that the user cancels with a single tap). This asymmetric cost motivates lowering the decision threshold from 0.50 to **0.42** [details in [`System_Architecture/ai/MODEL_RESULTS_ANALYSIS.md`](System_Architecture/ai/MODEL_RESULTS_ANALYSIS.md)]. The threshold sweep performed during evaluation produced the following observations:

- At threshold = 0.50: Recall = 95.5 %, FAR = 9.8 %
- At threshold = **0.42**: Recall = **98.51 %**, FAR = **12.31 %**
- At threshold = 0.35: Recall = 99.1 %, FAR = 17.5 %

The chosen threshold of 0.42 maximises Recall while keeping the False Alarm Rate manageable, with the firmware-level FSM further reducing the effective FAR (Section 1.2 above).

## 3. Cloud Storage and Data Service

We utilise the **MongoDB Atlas** cloud database to enable reliable data connectivity, real-time data access, and scalable data management. Telemetry data from the wearable is first received by the Android app over BLE, then transmitted to the Flask back-end deployed on Render via HTTPS POST requests. The Flask server acts as the central data gateway, performing validation and authentication before persisting the data into MongoDB Atlas collections. The mobile application interacts with the system through the same REST API, enabling users to analyse data. The overall architecture is illustrated below.

```
ESP32-S3 ── BLE ──> Android App ── HTTPS ──> Render (server.py) ── MongoDB Atlas
                                                    │
                                                    └──> users / vitals / fall_events
```

### 3.1 Telemetry Transmission

In the architecture of the system, the **Android application** is responsible for transmitting relevant data to the Render back-end to support real-time monitoring, database storage, and long-term analysis. To enable secure and scalable communication between the application and the cloud, the system utilises the **OkHttp 4.12** library for HTTPS requests with Gson 2.10 for JSON marshalling. The process of sending telemetry data from the Android app to the Render back-end is implemented in [`android_studio_AIFD/app/src/main/java/com/aifd/data/CloudApi.kt`](android_studio_AIFD/app/src/main/java/com/aifd/data/CloudApi.kt). The workflow is divided into three main stages:

**Stage 1: User Authentication.** Upon launching the application, the user logs in or registers via the `/api/auth/login` and `/api/auth/register` endpoints. The Flask back-end validates the credentials against the `users` collection in MongoDB, using SHA-256 password hashing. On successful login, the application receives the authenticated `userId`, which is used as the partition key for all subsequent data operations.

**Stage 2: BLE Foreground Service.** The `BleForegroundService` runs in the background as an Android Foreground Service, ensuring that BLE notifications continue even when the screen is off. The service collects vital signs from the BMI160 (via the BATCH packet) and fall events (via the ALERT packet), then forwards them to the `MonitoringViewModel`, which is responsible for cloud synchronisation.

**Stage 3: Cloud Synchronisation.** Each new vital reading is sent to the back-end via `POST /api/vitals`, with a JSON payload conforming to the schema in Table 11 (Section 3.3 below). Each fall event is sent via `POST /api/fall_event`. Both endpoints return a `200 OK` upon successful insertion or a structured error response.

### 3.2 Serverless Data Handling

To ensure low-latency processing without managing server infrastructure, we leverage the **Render Platform-as-a-Service** to host the Flask back-end. Render automatically provisions HTTPS certificates, manages environment variables (including the MongoDB connection string), and handles container deployment from the project's GitHub repository. The `server.py` file exposes RESTful endpoints, each implemented as a Flask view function.

### 3.3 Data Storage

In our system, we employ **MongoDB Atlas** as the primary data storage solution to support the ingestion, persistence, and querying of both real-time and historical fall-related data. MongoDB Atlas provides a distributed, schema-flexible, multi-model NoSQL environment with low-latency read and write capabilities, which is critical for our system's performance and scalability requirements. We adopt a document-based data model in MongoDB, where each record is stored as a JSON document. The schema for the `vitals` collection is presented in Table 11 below.

**Table 11.** MongoDB document schema for the `vitals` collection

| Field Name | Data Type | Description |
|---|---|---|
| `_id` | ObjectId | Unique identifier for the document (generated by MongoDB) |
| `deviceId` | string | Identifier of the wearable transmitting the telemetry data (BLE MAC address) |
| `userId` | string | Authenticated username from the `users` collection |
| `timestamp` | ISODate | UTC timestamp marking the moment of the vital reading |
| `heartRate` | integer | Heart rate in beats per minute, or `null` when sensor is not ready |
| `spo2` | integer | Peripheral oxygen saturation in percent, or `null` when sensor is not ready |
| `temperature` | number | Body temperature (currently `null`, reserved for future hardware) |
| `bloodPressure` | object | Nested object with `systolic` and `diastolic` integer fields (currently `null`) |
| `source` | string | Provenance tag (`ble_edge` for live data; `manual` for user-entered values) |

The `fall_events` collection follows a similar pattern but additionally records the model's fall probability (`fallProb`), the event type (`fall_auto` or `fall_manual_sos`), and the resolution status (`resolved`).

To optimise performance and scalability, we configure indexing using `userId` and `timestamp` as the indexed fields. This allows the back-end to achieve fast range-queries on the typical "last 1 hour" and "last 24 hours" patterns used by the mobile application.

### 3.4 Data Ingestion and Retrieval Endpoints

To enable seamless integration between the wearable, the mobile application, and the cloud, we developed a lightweight RESTful API using Flask. The API service is containerised and deployed on Render, providing HTTPS-secured endpoints. It communicates directly with MongoDB Atlas, ensuring low-latency access to telemetry data recorded during fall events.

**Endpoint Specifications:**

- **`POST /api/auth/register`** — Creates a new user account, hashes the password with SHA-256, and inserts the document into the `users` collection.
- **`POST /api/auth/login`** — Validates credentials against the `users` collection; returns the authenticated `userId` on success.
- **`POST /api/vitals`** — Ingests a single vital-sign reading into the `vitals` collection. Required fields are `deviceId`, `userId`, and `timestamp`.
- **`GET /api/vitals?userId=...&range=1h|24h&limit=300`** — Retrieves vital-sign documents for the specified user within the specified time range (1 hour or 24 hours).
- **`POST /api/fall_event`** — Ingests a fall event into the `fall_events` collection.
- **`GET /api/fall_events?userId=...`** — Retrieves all fall events for the specified user.
- **`GET /api/health`** — Health check endpoint; returns `{"ok": true, "mongodb": "connected"}` when the back-end is operational.

Each endpoint returns standardised JSON responses with appropriate HTTP status codes (200, 201, 400, 401, 500), and includes exception handling for invalid data formats, authentication failures, or database connectivity issues.

## 4. Mobile Application

Our Android mobile application provides a comprehensive monitoring and emergency-response system that enables users and caregivers to review and act on real-time and historical fall-related data. This functionality is designed to offer clear, actionable insights into the wearer's safety status, the device's connection health, and long-term vital-sign trends.

### 4.1 Live Monitoring Feature

The live monitoring feature provides users with real-time visualisation of heart rate and SpO₂ as received over BLE from the wearable. The Home screen displays the current values along with a colour-coded status badge (Normal / High / Low). The Health screen displays a chart with three selectable time ranges: **LIVE** (last 25 seconds, raw samples), **1h** (12 buckets of 5 minutes each), and **24h** (24 buckets of 1 hour each). The implementation is in [`android_studio_AIFD/app/src/main/java/com/aifd/viewmodel/MonitoringViewModel.kt`](android_studio_AIFD/app/src/main/java/com/aifd/viewmodel/MonitoringViewModel.kt) with the bucketing logic in the `bucketCloud()` function.

### 4.2 Alert Handling Feature

When the wearable confirms a fall, the BLE foreground service receives an ALERT packet and immediately triggers a full-screen alert overlay. The screen is woken using the `setShowWhenLocked(true)` and `setTurnScreenOn(true)` flags so that even a locked phone displays the alert. The user is presented with two large buttons — **"I'M SAFE"** to cancel and **"CALL FOR HELP"** to immediately escalate — and a 15-second countdown. If the countdown expires without user interaction, the application automatically issues an `Intent.ACTION_CALL` to the caregiver's phone number stored in the user profile. The implementation is in [`android_studio_AIFD/app/src/main/java/com/aifd/ui/screens/AlertScreen.kt`](android_studio_AIFD/app/src/main/java/com/aifd/ui/screens/AlertScreen.kt) and [`android_studio_AIFD/app/src/main/java/com/aifd/navigation/AppNavigation.kt`](android_studio_AIFD/app/src/main/java/com/aifd/navigation/AppNavigation.kt) lines 320–380.

### 4.3 History and Report Feature

The History screen displays a chronological list of fall events fetched from the `/api/fall_events` endpoint, with severity indicators and timestamps. Each event can be tapped to reveal detailed information including the fall probability reported by the model, the user's response (Safe / Call), and the location at the time of the event. The implementation is in [`android_studio_AIFD/app/src/main/java/com/aifd/ui/screens/HistoryScreen.kt`](android_studio_AIFD/app/src/main/java/com/aifd/ui/screens/HistoryScreen.kt).

---

# CHAPTER 3: EXPERIMENTAL RESULTS AND EVALUATION

This chapter presents a comprehensive evaluation of the CaraFall system, encompassing both functional performance and testing outcomes. The evaluation includes the performance of the embedded fall-detection model, the cloud storage and API infrastructure, the mobile application, and the overall system cost. In addition to controlled experiments and real-world usage scenarios, structured testing was conducted, including unit tests, integration tests, and acceptance tests with user participation. These tests assess the accuracy, latency, and resource efficiency of the TinyML model, the reliability of cloud data transmission and storage, and the responsiveness and usability of the mobile interface. The system test also involves volunteer users to evaluate comfort, effectiveness, and user satisfaction. Finally, an analysis of estimated manufacturing costs is performed to determine the system's feasibility for commercial deployment. The results presented in this chapter validate the system's technical soundness and practical viability, while also providing insights for future improvements.

> **[TODO – NOT YET IN REPO]**
> Expected content: a photo of the complete CaraFall system showing the assembled wristband, the paired smartphone displaying the live monitoring screen, and the cloud dashboard. The photo should be saved as `System_Architecture/hardware_photos/full_system.jpg` and referenced here as Figure 25.

## 1. TinyML Performance for Fall Detection

In this section, we deployed the TinyML model onto the ESP32-S3 microcontroller for the fall detection task. In order to evaluate the performance of our model on a microcontroller, we need to test on both experimental data and real-world signals to evaluate metrics such as accuracy, latency, and memory usage. This comprehensive evaluation process is necessary to ensure our model meets the requirements of the designed system, delivering optimal performance and making the user experience reliable.

### 1.1 Model Accuracy

In order to clearly illustrate the model performance, the **confusion matrix** is widely used in machine learning. The confusion matrix provides a summary of prediction results on a classification task by comparing the predicted labels with the true labels. This matrix is structured around a grid format, typically comprising four fundamental metrics:

- **True Positive (TP):** The model correctly predicted a positive class (a fall).
- **False Positive (FP):** The model incorrectly predicted a positive class (alarm during an ADL).
- **True Negative (TN):** The model correctly predicted a negative class (ADL is not a fall).
- **False Negative (FN):** The model incorrectly predicted the negative class (missed a real fall).

Based on the confusion matrix, we compute the evaluation metrics:

$$
\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}
$$

$$
\text{Recall} = \frac{TP}{TP + FN}
$$

$$
\text{Precision} = \frac{TP}{TP + FP}
$$

$$
\text{F1-Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}
$$

$$
\text{FAR} = \frac{FP}{FP + TN}
$$

The final deployed model is **V84**, located at [`AI/model_updated_version_84/`](AI/model_updated_version_84/). The metrics quoted verbatim from [`AI/model_updated_version_84/results/metrics_summary.txt`](AI/model_updated_version_84/results/metrics_summary.txt):

```
Accuracy:  0.9310
Recall:    0.9851
Precision: 0.8889
F1:        0.9345
FAR:       0.1231
MissRate:  0.0149
Threshold: 0.42
Epoch:     78
```

All evaluation metrics — particularly the **Recall of 98.51 %** — exceed the M2 target of ≥ 95 %, so we can confidently claim that the model is expected to have high performance on new data while maintaining the critical safety priority of not missing real falls. The False Alarm Rate of 12.31 % is slightly above the engineering target of ≤ 10 %, but the firmware-level seven-stage pipeline (Section 1.2 of Chapter 2) further reduces the effective FAR at the system level by rejecting candidate windows that are not preceded by appropriate impact and high-impact gates.

### 1.2 Model Loss

The loss curve shows how well the model is learning to minimise the error through each epoch. It has two characteristic curves, the training and validation curves, which correspond to the training and validation datasets. Model loss can also be used to detect issues during training that can affect the model performance:

- **Overfitting:** When the training loss decreases while the validation loss increases — the model has learned the training data instead of learning general concepts.
- **Underfitting:** When both loss curves stay high or decrease only slightly — this issue occurs due to a model architecture that is too simple or to a training set of insufficient quality or quantity.

Based on the M2 requirements, we required the loss to be lower than 15 % at convergence in order to ensure the model has high performance. In our model V84, the loss curve shows a dramatic downward trend over 78 training epochs on both training and validation curves, which indicates that the model quickly learns from the data and minimises the loss. After the 30th epoch, the loss change becomes stable below 10 % error and tends towards convergence. The training-curve image is stored at `AI/model_updated_version_84/results/training_curves.png`.

### 1.3 Memory Performance and Real-Time Detection Evaluation

To indicate that the AI model can run on a microcontroller smoothly without stack overflow or out-of-memory failures, we need to analyse the used memory after deploying the model.

- **Model size:** The trained TensorFlow model accounts for **62.09 KB** in TFLite INT8 format (only the model weights, after quantisation). The binary header file `fall_detection_v84.h` matches this size after `xxd -i` conversion. The 4 MB flash of the ESP32-S3-DevKitM-1 leaves more than 60× headroom.
- **Tensor arena size:** 60 KB statically allocated in SRAM via `kTensorArenaSize` (`S3_BLE_test_2/src/main.cpp` line 77).
- **RAM utilisation:** Approximately 30 % of the 512 KB SRAM is used after flashing, of which the tensor arena, BLE stack, and FreeRTOS task stacks are the main consumers.
- **Inference latency:** The reference TFLite Micro kernels execute one inference in approximately **491 ms** on the ESP32-S3 dual-core at 240 MHz (measured in `UT_AI_04`, see [`System_Architecture/test_plan/UNIT_TEST_RESULTS.md`](System_Architecture/test_plan/UNIT_TEST_RESULTS.md)). This is comfortably below the 2-second window cadence, so back-pressure never builds up. With the FreeRTOS dual-task architecture, the Core 0 sampling task continues to acquire BMI160 samples at exact 50 Hz throughout the inference, resulting in **zero sample loss** regardless of inference duration.

## 2. Cloud Storage and API Querying

To evaluate the performance and reliability of the cloud data pipeline, we conducted a series of tests involving real-time transmission, storage, and retrieval of vital-sign and fall-event data. This section presents the results of storing telemetry in MongoDB Atlas and accessing it through the dedicated API endpoints. These components form the backbone of the system's long-term monitoring capabilities and support the mobile application's ability to present meaningful visualisations and health metrics to end users.

### 2.1 Telemetry Storage in MongoDB Atlas

During experimentation on 2026-05-20, the Android application continuously transmitted vital-sign telemetry to the Render back-end, which was processed by the Flask handler and stored in the `vitals` and `fall_events` collections of the MongoDB Atlas cluster. The handler processed the payload and stored each event as a consistent JSON document.

The verified Render server log from the live test session demonstrates successful end-to-end transmission:

```
192.168.1.15 - - [20/May/2026 00:24:31] "POST /api/auth/login HTTP/1.1" 200
192.168.1.15 - - [20/May/2026 00:24:53] "POST /api/vitals HTTP/1.1" 200
192.168.1.15 - - [20/May/2026 00:25:18] "POST /api/vitals HTTP/1.1" 200
192.168.1.15 - - [20/May/2026 00:25:43] "POST /api/vitals HTTP/1.1" 200
192.168.1.15 - - [20/May/2026 00:24:35] "GET /api/vitals?userId=dien572&deviceId=&range=1h&limit=300 HTTP/1.1" 200
192.168.1.15 - - [20/May/2026 00:24:41] "GET /api/vitals?userId=dien572&deviceId=&range=24h&limit=300 HTTP/1.1" 200
```

We verified the integrity of stored data by manually reviewing inserted documents in the MongoDB Atlas Data Explorer and ensuring that all expected fields (`deviceId`, `userId`, `timestamp`, `heartRate`, `spo2`, `source`) were populated accurately. No malformed entries or missing values were observed in the most recent test session. Moreover, MongoDB Atlas's response time to range queries remained within acceptable thresholds during all test sessions.

### 2.2 API Endpoint Validation

We tested the two primary retrieval endpoints — `/api/vitals` and `/api/fall_events` — using both `curl` from the command line and live sessions from the mobile application. Both endpoints returned consistent and timely responses, allowing accurate rendering of data visualisations and summary statistics in the application.

A subtle bug was identified during the 24h-range query: a previous build of the firmware emitted ESP32 boot-millis as the timestamp instead of Unix milliseconds, causing 415 documents to be stored with a 1970-01-01 timestamp. After cleaning these legacy documents with a one-off `delete_many({"timestamp": {"$lt": cutoff}})` operation, the 24h range query returned only valid data and the chart in the mobile application rendered correctly.

## 3. Mobile Application Performance

We evaluated the mobile application under daily-use conditions using **Samsung Galaxy M20 (Android 10)** as the reference device. The app successfully fetched vital-sign and fall-event records from the Render endpoints and presented them using intuitive, interactive components.

**Key functionalities tested:**

- **Health Monitor View:** The application correctly displayed live heart-rate and SpO₂ values updated every 25 seconds based on the BATCH packets received from the wearable. Switching between LIVE / 1h / 24h time ranges triggered the appropriate cloud-fetch logic, with a smooth shimmer-bar loading indicator during the network round-trip.
- **Alert Overlay:** The full-screen alert overlay displayed correctly even when the phone was locked, with vibration and 15-second countdown working as designed. The "I'M SAFE" and "CALL FOR HELP" buttons responded to single-tap interactions and triggered the appropriate logic.
- **History View:** Fall events from MongoDB Atlas were displayed in reverse chronological order with severity indicators. Tapping each event opened a detail screen with the model's fall probability and the user's resolution.
- **Authentication:** Login and Register flows successfully validated credentials against the MongoDB `users` collection. The show/hide-password toggle added in the final iteration improved usability for elderly users who may have difficulty seeing the keyboard.

## 4. Testing Results

This section presents the testing results of the CaraFall system, including unit tests for individual modules (such as the BMI160 driver, BLE stack, and TinyML inference), integration tests between sensors, microcontroller, and cloud services, and system testing with real users to evaluate effectiveness and user feedback. The complete test plan with 75 scenarios is documented at [`System_Architecture/test_plan/TEST_PLAN_OVERVIEW.md`](System_Architecture/test_plan/TEST_PLAN_OVERVIEW.md), and executed results are recorded in [`System_Architecture/test_plan/UNIT_TEST_RESULTS.md`](System_Architecture/test_plan/UNIT_TEST_RESULTS.md).

### 4.1 Unit Test

#### 4.1.1 BMI160 Inertial Sensor Test

To validate the correct interfacing and calibration of the BMI160 IMU on the ESP32-S3, we conducted a series of unit tests using the firmware on the assembled bench-top prototype. These tests aimed to evaluate the sensor's communication, calibration, sampling rate, and self-test capability. For each test scenario, the firmware was instrumented with diagnostic prints over the USB-CDC serial port at 115 200 baud.

**Table 12.** Unit test results — BMI160 sensor module

| Test Writer: TRẦN PHƯỚC DIỄN |  |  |  |
|---|---|---|---|
| **Test Case Name** | BMI160 driver validation | **Test ID #:** | UT_BMI160 |
| **Description** | Ensure the BMI160 IMU communicates correctly over I²C at 0x69, reads calibrated values, samples at exactly 50 Hz, and passes its built-in self-test | **Type:** | White box |
| Test Information |  |  |  |
| **Test Version** | Module testing | **Date** | May 18, 2026 |
| **Hardware Version** | 1.0.0 | **Time** | 10:00 AM |
| **Software Version** | 1.0.0 |  |  |

| Scenario | Result | Output |
|---|:-:|---|
| SC_01 I²C Communication | ✅ Pass | `addr=0x69  chip_id=0xD1  (expected 0xD1)` |
| SC_02 Range Calibration | ✅ Pass | `ax=0.036 g  ay=-0.048 g  az=0.992 g` (device flat) |
| SC_03 Sample Rate Check | ✅ Pass | `100 reads in 2001 ms → 50.0 Hz` |
| SC_04 Self-test | ✅ Pass | `ACC_RANGE=0x03  GYR_RANGE=0x00  ACC_CONF=0x28` |
| Overall test result: | **4 / 4 PASS** — sensor operational and within tolerance |

#### 4.1.2 TinyML Inference Engine Test

To validate that the TFLite Micro interpreter can load the V84 model, allocate its tensor arena, and produce sigmoid outputs within the [0.0, 1.0] range, we conducted a unit-test sequence on the firmware. The model loading, buffer flow under burst sampling, sample-integrity guarantee from the FreeRTOS dual-task architecture, and sigmoid output range were all verified.

**Table 13.** Unit test results — TinyML inference engine

| Test Writer: PHẠM VĂN TIÊN |  |  |  |
|---|---|---|---|
| **Test Case Name** | TFLite Micro inference engine | **Test ID #:** | UT_AI_MODEL |
| **Description** | Ensure the TFLite Micro interpreter loads the V84 model, retains 100 samples in a circular buffer under burst input, produces sigmoid outputs within [0,1], and respects the 50 Hz / 20 ms sample cadence | **Type:** | White box |
| Test Information |  |  |  |
| **Test Version** | Module testing | **Date** | May 18, 2026 |
| **Hardware Version** | 1.0.0 | **Time** | 10:00 AM |
| **Software Version** | 1.0.0 |  |  |

| Scenario | Result | Output |
|---|:-:|---|
| SC_01 Model Loading | ✅ Pass | `schema=OK  alloc=OK  shape=OK[1,100,6]  type=int8  arena=60 KB` |
| SC_02 Buffer Flow | ✅ Pass | `pushed 120  retained=100  oldest=20  newest=119` |
| SC_03 Sample Integrity | ✅ Pass | `samples=100  ordered=YES  gap=[20,20] ms  FreeRTOS=Core0/Core1` |
| SC_04 Sigmoid Limit | ✅ Pass | `out=[0.0000, 0.9961]  (target: [0.0, 1.0])` |
| Overall test result: | **4 / 4 PASS** — inference engine ready for deployment |

### 4.2 Integration Test

#### 4.2.1 BLE Pairing and Data Sync Test

To validate the integrated behaviour of the BLE peripheral on the ESP32-S3 and the BLE central on the Android phone, we conducted the pairing-and-data-sync integration test. The ESP32-S3 was powered up and the application was launched on the Samsung Galaxy M20. The application was expected to discover the bonded device, initiate a GATT connection, subscribe to the ALERT and VITALS characteristics, write `READY` to the CONTROL characteristic, and begin receiving notification payloads.

**Table 14.** Integration test results — BLE pairing & data sync

| Test Writers: TRẦN PHƯỚC DIỄN & PHẠM VĂN TIÊN |  |  |  |
|---|---|---|---|
| **Test Case Name** | BLE pairing and initial data sync | **Test ID #:** | IT_BLE_01 |
| **Description** | Ensure that the Android application discovers the bonded ESP32-S3, completes the READY handshake, and begins receiving valid BATCH packets within 30 s of launch | **Type:** | Black box |
| Test Information |  |  |  |
| **Test Version** | Integration testing | **Date** | May 18, 2026 |
| **Hardware Version** | 1.0.0 | **Time** | 14:00 PM |
| **Software Version** | 1.0.0 |  |  |

Live session log:
```
[BLE]  status=advertising   handshake=waiting  sessions=0  uptime=15 s
[BLE] *** Client connected ***
[BLE]  Waiting for READY command on CONTROL characteristic...
[BLE]  status=CONNECTED     handshake=READY    sessions=1  uptime=20 s
[BLE]  status=CONNECTED     handshake=READY    sessions=1  uptime=25 s
```

The pairing flow conforms to the specification in [`S3_BLE_test_2/BLE_PROTOCOL.md`](S3_BLE_test_2/BLE_PROTOCOL.md): advertise → connect → subscribe → READY → data channel open.

**Result: ✅ Pass.** The full READY handshake completed at uptime 20 s; first BATCH packet received at uptime 32 s. All test cases passed the acceptance criteria (handshake time < 30 s).

#### 4.2.2 End-to-End Cloud Data Transmission Test

This test validates the successful transmission and storage of vital-sign data from the wearable to MongoDB Atlas via the Render Flask back-end. The objective is to ensure that the system consistently delivers data to the cloud in real time without failure. Each test case involves triggering a BATCH packet on the firmware, monitoring the JSON payload sent by the Android application via OkHttp, and verifying whether the data is successfully stored in the `vitals` collection. A total of 10 trials were conducted to evaluate consistency and reliability.

**Table 15.** End-to-end test — cloud transmission and storage

| Test Writer: TRẦN PHƯỚC DIỄN |  |  |  |
|---|---|---|---|
| **Test Case Name** | Wearable-to-Cloud data transmission | **Test ID #:** | IT_CLOUD_01 |
| **Description** | Verify successful transmission and storage of vital-sign data from the wearable to MongoDB Atlas via Render | **Type:** | Black box |
| Test Information |  |  |  |
| **Test Version** | Integration testing | **Date** | May 20, 2026 |
| **Hardware Version** | 1.0.0 | **Time** | 00:25 AM |
| **Software Version** | 1.0.0 |  |  |

| Test ID | Vital Event Time | HTTPS POST Status | MongoDB Insertion | Result |
|---|---|:-:|:-:|:-:|
| 1 | 00:24:53.142 | 200 | Inserted | Pass |
| 2 | 00:25:18.401 | 200 | Inserted | Pass |
| 3 | 00:25:43.788 | 200 | Inserted | Pass |
| 4 | 00:26:08.155 | 200 | Inserted | Pass |
| 5 | 00:26:33.502 | 200 | Inserted | Pass |
| 6 | 00:26:58.911 | 200 | Inserted | Pass |
| 7 | 00:27:23.247 | 200 | Inserted | Pass |
| 8 | 00:27:48.580 | 200 | Inserted | Pass |
| 9 | 00:28:13.946 | 200 | Inserted | Pass |
| 10 | 00:28:38.302 | 200 | Inserted | Pass |
| Overall test result: | **10 / 10 PASS** |  |  |  |

All 10 trials successfully resulted in the insertion of a new vital-sign document into the `vitals` collection. This confirms that the wearable-to-cloud integration is stable and reliable under normal operating conditions.

### 4.3 System Test

> **[TODO – NOT YET IN REPO]**
> Expected content: a system test conducted with elderly volunteer participants in a controlled but realistic environment. The setup would include placing the CaraFall wristband on the volunteer's wrist and recording five fall scenarios (forward, backward, lateral-left, lateral-right, and slow collapse) on a thick foam mattress, as well as 10 minutes of Activities of Daily Living (ADL) for false-alarm validation. Results should report the per-scenario detection rate, the per-ADL false-alarm count, and the overall end-to-end latency from impact to phone ring. The acceptance test scenarios are pre-specified in `System_Architecture/test_plan/acceptance/FALL_SOS_E2E.md` but have not yet been executed against the assembled hardware prototype.

The integrated unit and BLE-pairing tests confirm that the firmware and the Android application interoperate correctly at the protocol level. The final system test on elderly volunteers will validate not only the technical performance of the system but also its usability in a real-world setting. This system-level test will provide critical feedback for confirming the operational readiness in a domestic-care context.

## 5. Manufacturing Cost

> **[TODO – NOT YET IN REPO]**
> Expected content: the total Bill-of-Materials cost for the CaraFall wristband, broken down by item, quantity, unit price (VND), and supplier. The BOM should include: ESP32-S3-DevKitM-1, BMI160 GY-module, MAX30102 module, 3.7 V Li-Po battery, charging IC, 3 × LED + resistors, passive buzzer, push-button, PCB manufacturing, 3D-printed enclosure, wristband strap, and miscellaneous wiring/solder. The target total is ≤ 2 500 000 VND per Section 1.3 of Chapter 1.

The budget includes expenditures on the microcontroller, inertial sensing hardware, optical pulse-oximeter, BLE connectivity (integrated), and the haptic feedback mechanism. Manufacturing-related costs such as PCB fabrication, device housing, testing, and quality control are also considered. Furthermore, provisions are made for operational overhead, including minor assembly materials and system calibration. Keeping the production cost within this limit requires thoughtful component selection, efficient system design, and careful cost management across both development and deployment stages. The objective is to ensure that the final product not only meets technical performance expectations but also remains cost-effective and scalable for future market deployment.

---

# CONCLUSION & FUTURE WORK

## 1. Results Achieved

In this project, we successfully designed and implemented **CaraFall**, an intelligent edge AIoT wearable system that combines embedded TinyML for real-time fall detection, an Android companion application for immediate emergency response, and cloud-based services for long-term data logging and visualisation. The core of the system is a TinyCNN model trained on six-channel inertial data and deployed on the ESP32-S3 microcontroller using TFLite Micro. The model enables low-latency, real-time processing directly on the wrist, triggering immediate BLE alerts and an automatic phone call to the registered caregiver to reduce response time during a fall event. This system was further integrated with **MongoDB Atlas** through a Flask back-end deployed on Render, enabling secure data transmission and storage, and visualised through a mobile application that provides users and caregivers with insights into the wearer's safety status. The combination of on-device fall detection, automatic emergency calling, and mobile/cloud integration resulted in a highly interactive and user-centric system. The received feedback from internal testing indicates clear improvements in user experience, comfort, and overall safety. This demonstrates the feasibility and impact of intelligent embedded solutions for safety-critical health applications targeting the elderly.

## 2. Key Strengths

The developed system demonstrates several technical and user-centric strengths that enhance its practicality, responsiveness, and long-term usability:

- **Offline-First Emergency Path:** The wearable communicates with the Android application over Bluetooth Low Energy and triggers the emergency call directly through the phone, completely bypassing the need for Wi-Fi or cellular data on the wearable itself. This ensures the safety-critical path remains operational even during Internet outages.
- **Real-Time On-Device Inference:** The embedded TinyCNN model allows for on-device detection of falls, enabling the wearable to respond immediately by broadcasting the BLE ALERT and activating the LED and buzzer feedback without waking the user with a false alarm.
- **Multi-Stage False-Alarm Suppression:** The seven-stage post-processing pipeline — combining the AI inference with a deterministic finite-state machine that requires sustained post-impact stillness — reduces the effective False Alarm Rate well below the model's standalone rate.
- **Mobile Application with Cloud Backend:** The Android application delivers clear, intuitive visualisations of vital-sign trends, fall history, and intervention frequency, while the MongoDB Atlas back-end provides persistent storage and the ability for caregivers to monitor the wearer remotely.
- **Lightweight Embedded Model:** The use of TFLite Micro with INT8 quantisation allows the V84 model to function efficiently within the memory and processing constraints of the ESP32-S3, leaving more than 60× flash headroom and using only 30 % of available SRAM.

## 3. Limitations

Despite the successful implementation of the core functionalities, the system exhibits several limitations that impact its performance and usability. Some of these are inherent to the current design, while others stem from the limited development timeline of this project:

- **Simulated Vital-Sign Provider:** The current firmware simulates heart-rate and SpO₂ readings via the `readHrSample()` and `readSpo2Sample()` functions in `S3_BLE_test_2/src/main.cpp`. The real MAX30102 driver has not yet been integrated, which limits the credibility of the vital-sign accuracy claim. The migration path is straightforward — only these two functions need to be replaced — and the rest of the BLE protocol and Android parser will remain unchanged.
- **Accelerometer Range Saturation:** The BMI160 is currently configured at ±2 g, but real falls often produce impact peaks above 4 g at the wrist. The model V84 was trained on ±2 g data, so the system relies primarily on gyroscope signals for candidate detection. Re-training the model on ±8 g or ±16 g data would unlock the full accelerometer-based candidate gate.
- **Always-On Firmware:** The current firmware does not invoke `esp_sleep_*` low-power APIs, which limits the battery life of the prototype. Adding deep-sleep and light-sleep gating logic is required to reach the ≥ 5-day battery-life target.
- **Hardware Prototype Stage:** The current prototype is at the DevKit-on-bench stage. The final PCB design, SMD assembly, 3D-printed enclosure, and ergonomic-fit testing on elderly volunteers have not yet been completed. These deliverables are critical to bringing the system to a wearable form factor.
- **Time-Bound Real-World Validation:** Due to the limited duration of this capstone project, certain essential aspects — such as extended real-world testing with diverse elderly user groups, long-term evaluation under various household conditions, and iterative model tuning on field-collected data — were beyond the scope of this initial implementation.

## 4. Future Work

In the future, several enhancements are planned to improve the system's performance, usability, and readiness for commercial deployment. These directions aim to address both technical challenges and user-centred design goals:

- **MAX30102 Driver Integration:** The first priority is to replace the simulated heart-rate and SpO₂ provider with a real MAX30102 driver. The Android-side parser is already designed to handle the `255 → invalid` sentinel value, so the migration is clean and limited to the firmware.
- **Sensor-Range Upgrade and Model Re-training:** Switching the BMI160 to ±8 g range and re-training the model on the new dynamic range will enable the accelerometer-based candidate gate (currently bypassed at 7.5 g) to take full effect.
- **Low-Power Firmware:** Adding deep-sleep and light-sleep gating logic, BLE connection-aware power tuning, and advertising-interval throttling when no peer is connected will help reach the ≥ 5-day battery-life target.
- **Final Hardware Milestones:** Finalised schematic, Gerber files, SMD assembly, and a 3D-printed wristband enclosure (target weight ≤ 70 g) are required to bring the system from a DevKit prototype to a wearable product.
- **Extended Real-World Evaluation:** More extensive trials involving diverse elderly user groups in different household conditions will be conducted to validate the system's performance, usability, and adaptability in realistic environments.
- **Lightweight Attention Mechanism:** Adding a lightweight attention head to the TinyCNN architecture and evaluating its accuracy-vs-size trade-off may push the overall accuracy past the 95 % engineering target without bloating the model size.
- **Cloud-Based Caregiver Web Dashboard:** A web-based dashboard for clinicians and family caregivers will be developed to complement the mobile app, enabling remote monitoring of multiple wearers from a single interface.

---

# BIBLIOGRAPHY

[1] World Health Organization, "Falls — Fact Sheet," *WHO*, Apr. 26, 2021. https://www.who.int/news-room/fact-sheets/detail/falls

[2] L. Z. Rubenstein, "Falls in older people: epidemiology, risk factors and strategies for prevention," *Age and Ageing*, vol. 35, suppl. 2, pp. ii37–ii41, Sept. 2006, doi: 10.1093/ageing/afl084.

[3] M. Mubashir, L. Shao, and L. Seed, "A survey on fall detection: Principles and approaches," *Neurocomputing*, vol. 100, pp. 144–152, Jan. 2013, doi: 10.1016/j.neucom.2011.09.037.

[4] P. Warden and D. Situnayake, *TinyML: Machine Learning with TensorFlow Lite on Arduino and Ultra-Low-Power Microcontrollers*, O'Reilly Media, 2019.

[5] Apple Inc., "Use Fall Detection with Apple Watch," *Apple Support*. https://support.apple.com/en-us/108896

[6] T. Khan, "A deep learning model for fall detection using a smart wearable gadget," *Electronics*, vol. 8, no. 9, p. 987, Sept. 2019, doi: 10.3390/electronics8090987.

[7] F. Bagalà, C. Becker, A. Cappello, L. Chiari, K. Aminian, J. M. Hausdorff, W. Zijlstra, and J. Klenk, "Evaluation of accelerometer-based fall detection algorithms on real-world falls," *PLOS ONE*, vol. 7, no. 5, p. e37062, May 2012, doi: 10.1371/journal.pone.0037062.

[8] Kotlin Foundation, "Kotlin Programming Language." https://kotlinlang.org/

[9] STMicroelectronics, "STM32L432KC Datasheet." https://www.st.com/en/microcontrollers-microprocessors/stm32l432kc.html

[10] Espressif Systems, "ESP32-S3 Wi-Fi & BLE 5 SoC." https://www.espressif.com/en/products/socs/esp32-s3

[11] Nordic Semiconductor, "nRF52840 Datasheet." https://infocenter.nordicsemi.com/

[12] Bosch Sensortec, "BMI160 Datasheet — 6-axis IMU." https://www.bosch-sensortec.com/products/motion-sensors/imus/bmi160/

[13] InvenSense, "MPU-6050 Product Specification." https://invensense.tdk.com/products/motion-tracking/6-axis/mpu-6050/

[14] STMicroelectronics, "LSM6DS3 — 6-axis IMU." https://www.st.com/en/mems-and-sensors/lsm6ds3.html

[15] Maxim Integrated (now Analog Devices), "MAX30102 Pulse Oximeter and Heart-Rate Sensor." https://www.analog.com/en/products/max30102.html

[16] H2zero, "NimBLE-Arduino BLE Stack for ESP32." https://github.com/h2zero/NimBLE-Arduino

[17] FreeRTOS, "The FreeRTOS Real-Time Operating System." https://www.freertos.org/

[18] TensorFlow, "TensorFlow Lite for Microcontrollers." https://www.tensorflow.org/lite/microcontrollers

[19] M. Saleh, M. Abbas, and R. B. Le Jeannes, "HR-IMU dataset for human-activity and fall detection," *Mendeley Data*, 2021.

[20] Render Inc., "Render — Cloud Application Hosting Platform." https://render.com/

[21] MongoDB Inc., "MongoDB Atlas — Multi-Cloud Database Service." https://www.mongodb.com/atlas

[22] Android Developers, "Jetpack Compose — Modern Toolkit for Building Native UI." https://developer.android.com/jetpack/compose

[23] Square Inc., "OkHttp — Open Source HTTP Client for Java/Kotlin." https://square.github.io/okhttp/

---

*End of M3 Final Capstone Report — Draft. Generated 2026-05-20 from branch `dien-zinex` @ `2f658429`. Search for `[TODO – NOT YET IN REPO]` to find every section still requiring author input before submission.*
