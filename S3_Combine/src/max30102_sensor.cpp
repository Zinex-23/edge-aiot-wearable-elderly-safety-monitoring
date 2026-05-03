// =====================================================
// MAX30102 SENSOR MODULE - Implementation
// =====================================================
// Non-blocking driver based on the working Test_MAX30102.ino code,
// adapted for concurrent operation with BMI160 + BLE + TFLite.
//
// Changes from original:
//   - Use I2C_SPEED_STANDARD (100kHz) to match BMI160 bus config
//   - Removed setPulseAmplitudeRed override (setup() handles it)
//   - Added volatile for thread-safety on shared state
//   - Replaced linear shift with circular buffer for O(1) updates
// =====================================================

#include "max30102_sensor.h"
#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"

// =====================================================
// INTERNAL STATE
// =====================================================
static MAX30105 particleSensor;
static volatile bool sensorReady = false;

// Circular buffer for sliding window
static uint32_t irBuffer[MAX30102_BUFFER_SIZE];
static uint32_t redBuffer[MAX30102_BUFFER_SIZE];
static volatile uint16_t bufferHead = 0;  // Next write position

// Algorithm output
static int32_t algoSpo2 = 0;
static int8_t  algoValidSpo2 = 0;
static int32_t algoHeartRate = 0;
static int8_t  algoValidHeartRate = 0;

// Filtered stable values (noise-rejected) — volatile for cross-task access
static volatile int lastStableHR = 0;
static volatile int lastStableSpO2 = 0;
static volatile bool currentFingerDetected = false;

// Timing
static unsigned long lastUpdateMs = 0;
static bool bufferInitialized = false;

// =====================================================
// HELPER: Linearize circular buffer for algorithm
// =====================================================
static void linearizeBuffer(const uint32_t *circBuf, uint32_t *linearBuf) {
  // Copy from head to end, then from 0 to head
  uint16_t head = bufferHead;
  uint16_t count = MAX30102_BUFFER_SIZE - head;
  memcpy(linearBuf, &circBuf[head], count * sizeof(uint32_t));
  if (head > 0) {
    memcpy(&linearBuf[count], circBuf, head * sizeof(uint32_t));
  }
}

// =====================================================
// INITIALIZATION
// =====================================================
bool max30102_init() {
  // Attempt to initialize the MAX30102 on the shared I2C bus
  // Wire.begin() must have been called already by the main firmware
  // Use STANDARD speed (100kHz) to match BMI160 bus configuration
  if (!particleSensor.begin(Wire, I2C_SPEED_STANDARD)) {
    Serial.println("[MAX30102] Sensor NOT FOUND on I2C bus");
    sensorReady = false;
    return false;
  }

  Serial.println("[MAX30102] Sensor FOUND, configuring...");

  // Configuration matching Test_MAX30102.ino for optimal HR/SpO2
  // Parameters: ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange
  //   ledBrightness = 60 (0x3C) - moderate LED power for SpO2 measurement
  //   sampleAverage = 4  - average 4 samples internally
  //   ledMode = 2        - Red + IR (SpO2 mode)
  //   sampleRate = 200   - 200 samples/sec
  //   pulseWidth = 411   - 411us pulse (18-bit resolution)
  //   adcRange = 16384   - full ADC range
  particleSensor.setup(60, 4, 2, 200, 411, 16384);

  // NOTE: Do NOT override LED amplitudes here.
  // The setup() call above already configures ledBrightness=60 for both
  // Red and IR LEDs, which is appropriate for SpO2 measurement.
  // Setting setPulseAmplitudeRed(0x0A) would reduce Red LED to a very
  // low level only suitable for proximity detection, NOT SpO2.
  particleSensor.setPulseAmplitudeGreen(0);   // Green LED off (not used)

  Serial.println("[MAX30102] Configuration complete");
  Serial.println("[MAX30102] Filling initial buffer (this may take a moment)...");

  // Fill the initial buffer (blocking, ~2 seconds)
  // This is necessary for the SparkFun algorithm to work correctly
  bufferHead = 0;
  for (int i = 0; i < MAX30102_BUFFER_SIZE; i++) {
    unsigned long sampleWaitStart = millis();
    while (!particleSensor.available()) {
      particleSensor.check();  // Check for new data
      if ((millis() - sampleWaitStart) > 1000) {
        Serial.println("[MAX30102] Initial buffer timeout");
        sensorReady = false;
        bufferInitialized = false;
        return false;
      }
      delay(1);
    }
    redBuffer[i] = particleSensor.getRed();
    irBuffer[i] = particleSensor.getIR();
    particleSensor.nextSample();
  }
  // After filling, head wraps to 0 (buffer is fully initialized in order)

  bufferInitialized = true;
  lastUpdateMs = millis();
  sensorReady = true;

  Serial.println("[MAX30102] Ready - initial buffer filled");
  return true;
}

// =====================================================
// NON-BLOCKING UPDATE
// =====================================================
void max30102_update() {
  if (!sensorReady || !bufferInitialized) return;

  unsigned long now = millis();
  if ((now - lastUpdateMs) < MAX30102_UPDATE_INTERVAL_MS) return;
  lastUpdateMs = now;

  // Check if new data is available from the sensor
  if (!particleSensor.available()) {
    particleSensor.check();
    if (!particleSensor.available()) return;  // No new data yet
  }

  // Circular buffer: overwrite at head position (O(1) instead of O(n))
  redBuffer[bufferHead] = particleSensor.getRed();
  irBuffer[bufferHead] = particleSensor.getIR();
  particleSensor.nextSample();

  // Check finger presence using the newest IR value
  long irValue = (long)irBuffer[bufferHead];

  // Advance head (wraps around)
  bufferHead = (bufferHead + 1) % MAX30102_BUFFER_SIZE;

  currentFingerDetected = (irValue >= MAX30102_FINGER_THRESHOLD);

  if (!currentFingerDetected) {
    // No finger -> reset stable values
    lastStableHR = 0;
    lastStableSpO2 = 0;
    return;
  }

  // Linearize circular buffers for the SparkFun algorithm
  // (algorithm expects contiguous arrays in chronological order)
  uint32_t linearIR[MAX30102_BUFFER_SIZE];
  uint32_t linearRed[MAX30102_BUFFER_SIZE];
  linearizeBuffer(irBuffer, linearIR);
  linearizeBuffer(redBuffer, linearRed);

  // Run the SparkFun HR/SpO2 algorithm
  maxim_heart_rate_and_oxygen_saturation(
    linearIR,
    MAX30102_BUFFER_SIZE,
    linearRed,
    &algoSpo2,
    &algoValidSpo2,
    &algoHeartRate,
    &algoValidHeartRate
  );

  // Apply noise filtering (same logic as Test_MAX30102.ino)
  
  // Filter Heart Rate
  bool hrValid = algoValidHeartRate &&
                 algoHeartRate > MAX30102_HR_MIN &&
                 algoHeartRate < MAX30102_HR_MAX;
  if (hrValid) {
    if (lastStableHR == 0 || abs(algoHeartRate - lastStableHR) < MAX30102_HR_MAX_JUMP) {
      lastStableHR = algoHeartRate;
    }
    // else: reject this reading as noise (too big a jump)
  }

  // Filter SpO2
  bool spo2Valid = algoValidSpo2 &&
                   algoSpo2 > MAX30102_SPO2_MIN &&
                   algoSpo2 <= MAX30102_SPO2_MAX;
  if (spo2Valid) {
    if (lastStableSpO2 == 0 || abs(algoSpo2 - lastStableSpO2) < MAX30102_SPO2_MAX_JUMP) {
      lastStableSpO2 = algoSpo2;
    }
    // else: reject this reading as noise
  }
}

// =====================================================
// PUBLIC GETTERS
// =====================================================
VitalsReading max30102_getLatestVitals() {
  VitalsReading reading;
  reading.timestamp = millis();
  reading.fingerDetected = currentFingerDetected;

  if (!sensorReady || !currentFingerDetected) {
    reading.heartRate = 255;  // INVALID_VITAL_VALUE
    reading.spo2 = 255;
    reading.valid = false;
    return reading;
  }

  // Use stable filtered values (read volatile atomically on 32-bit MCU)
  int hr = lastStableHR;
  int sp = lastStableSpO2;

  if (hr > 0 && hr <= 255) {
    reading.heartRate = (uint8_t)hr;
  } else {
    reading.heartRate = 255;
  }

  if (sp > 0 && sp <= 100) {
    reading.spo2 = (uint8_t)sp;
  } else {
    reading.spo2 = 255;
  }

  reading.valid = (reading.heartRate != 255 && reading.spo2 != 255);
  return reading;
}

bool max30102_isReady() {
  return sensorReady;
}

bool max30102_isFingerDetected() {
  return currentFingerDetected;
}
