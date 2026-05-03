// =====================================================
// MAX30102 SENSOR MODULE - Heart Rate & SpO2
// =====================================================
// Non-blocking driver for MAX30102 PPG sensor
// Integrates with the S3_BLE firmware via I2C (shared bus with BMI160)
// 
// Usage:
//   1. Add to platformio.ini: sparkfun/SparkFun MAX3010x Pulse and Proximity Sensor Library
//   2. In main.cpp: #include "max30102_sensor.h"
//   3. Call max30102_init() in setup() AFTER Wire.begin()
//   4. Call max30102_update() periodically (e.g., in sampling task)
//   5. Call max30102_getLatestVitals() to get filtered HR/SpO2
// =====================================================

#ifndef MAX30102_SENSOR_H
#define MAX30102_SENSOR_H

#include <Arduino.h>

// =====================================================
// CONFIGURATION
// =====================================================

// How often to run the SparkFun algorithm (ms)
// The sensor itself runs continuously, we just read periodically
#define MAX30102_UPDATE_INTERVAL_MS    200   // ~5 Hz internal update

// IR threshold to detect finger presence
#define MAX30102_FINGER_THRESHOLD      50000

// Noise filter: reject HR changes > this from last stable reading
#define MAX30102_HR_MAX_JUMP           15

// Noise filter: reject SpO2 changes > this from last stable reading
#define MAX30102_SPO2_MAX_JUMP         3

// Valid physiological ranges
#define MAX30102_HR_MIN                40
#define MAX30102_HR_MAX                180
#define MAX30102_SPO2_MIN              90
#define MAX30102_SPO2_MAX              100

// Algorithm buffer size (SparkFun library uses 100)
#define MAX30102_BUFFER_SIZE           100

// =====================================================
// DATA STRUCTURE
// =====================================================
struct VitalsReading {
  uint8_t heartRate;      // Filtered HR (bpm), 255 = invalid
  uint8_t spo2;           // Filtered SpO2 (%), 255 = invalid
  bool fingerDetected;    // true if finger is on sensor
  bool valid;             // true if both HR and SpO2 are valid
  unsigned long timestamp; // millis() when this reading was taken
};

// =====================================================
// PUBLIC API
// =====================================================

/**
 * Initialize the MAX30102 sensor.
 * Must be called AFTER Wire.begin() has been called.
 * 
 * @return true if sensor was found and initialized successfully
 */
bool max30102_init();

/**
 * Non-blocking update function.
 * Call this frequently (every loop iteration or from a task).
 * Internally manages timing to read sensor at appropriate rate.
 * Updates the sliding window buffer and computes HR/SpO2.
 */
void max30102_update();

/**
 * Get the latest filtered vitals reading.
 * Returns the most recent stable HR and SpO2 values.
 * If no valid reading is available, heartRate and spo2 will be 255.
 * 
 * @return VitalsReading struct with current values
 */
VitalsReading max30102_getLatestVitals();

/**
 * Check if the MAX30102 sensor was initialized successfully.
 * 
 * @return true if sensor is ready
 */
bool max30102_isReady();

/**
 * Check if a finger is currently detected on the sensor.
 * 
 * @return true if finger is present
 */
bool max30102_isFingerDetected();

#endif // MAX30102_SENSOR_H
