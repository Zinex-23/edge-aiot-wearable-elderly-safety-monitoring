/**
 * S3_BLE_test_2 — src/main.cpp
 *
 * Integration test firmware for AIFD ESP32-S3.
 *
 * Features:
 *   - Real BMI160 fall detection pipeline (same as S3_BLE production):
 *       candidate gate → activity gate (3 windows) → TFLite V84 → impact check → FALL_WATCH → STILL_TIMING
 *   - Confirmed fall → ALERT packet via BLE
 *   - Button press during fall alert → SAFE packet via BLE (replaces app countdown dismiss)
 *   - Simulated HR (60–100 bpm) and SpO2 (94–100%) — BATCH packet every 25 s
 *   - BLE: same UUIDs and READY handshake as production protocol
 *
 * BLE Packet formats (ref: BLE_PROTOCOL.md):
 *   ALERT,<seq>,<ts_sec>,fall,1,<fall_prob>,<non_fall_prob>
 *   SAFE,<seq>,<ts_sec>
 *   BATCH,<seq>,<hr0|hr1|hr2|hr3|hr4>,<spo2_0|...|spo2_4>,<ts0|...|ts4>
 */

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include "fall_detection_v84.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include <NimBLEDevice.h>
#include <string>

// =====================================================================
// PIN CONFIG
// =====================================================================
static const int PIN_LED_GREEN  = 4;
static const int PIN_LED_YELLOW = 5;
static const int PIN_LED_RED    = 6;
static const int PIN_BUZZER     = 7;
static const int PIN_BUTTON     = 10;
static const int PIN_I2C_SDA   = 8;
static const int PIN_I2C_SCL   = 9;

static const unsigned int  BUZZER_FREQ_HZ    = 2300;
static const unsigned long DEBOUNCE_MS       = 30;
static const unsigned long BLINK_INTERVAL_MS = 300;

// =====================================================================
// BMI160 REGISTERS
// =====================================================================
static const uint8_t BMI160_ADDR_LOW  = 0x68;
static const uint8_t BMI160_ADDR_HIGH = 0x69;
static const uint8_t BMI160_CHIP_ID   = 0xD1;

static const uint8_t REG_CHIP_ID   = 0x00;
static const uint8_t REG_GYR_DATA  = 0x0C;
static const uint8_t REG_ACC_DATA  = 0x12;
static const uint8_t REG_ACC_CONF  = 0x40;
static const uint8_t REG_ACC_RANGE = 0x41;
static const uint8_t REG_GYR_CONF  = 0x42;
static const uint8_t REG_GYR_RANGE = 0x43;
static const uint8_t REG_CMD       = 0x7E;

static const float ACC_LSB_PER_G   = 16384.0f;
static const float GYR_LSB_PER_DPS = 16.4f;

// =====================================================================
// SAMPLING + MODEL CONFIG
// =====================================================================
static const uint32_t SAMPLE_PERIOD_MS  = 20;
static const int      kWindowSize       = 100;
static const int      kFeatureCount     = 6;
static const int      kInferenceStride  = 100;
static const int      kTensorArenaSize  = 60 * 1024;

// V84 optimal threshold
static const float FALL_DECISION_THRESHOLD  = 0.42f;
static const float CANDIDATE_ACC_THRESHOLD  = 7.5f;
static const float CANDIDATE_GYRO_THRESHOLD = 240.0f;
static const float ACTIVITY_ACC_THRESHOLD   = 2.0f;   // gate bình thường (3 windows tích lũy)
static const float ACTIVITY_GYRO_THRESHOLD  = 50.0f;  // gate bình thường
static const float CANCEL_ACC_THRESHOLD     = 3.5f;   // ngưỡng huỷ FALL_WATCH/STILL_TIMING
static const float CANCEL_GYRO_THRESHOLD    = 150.0f; // cao hơn để tránh huỷ do phản xạ ngã
static const int   ACTIVITY_WINDOW_COUNT    = 3;
static const float FALL_IMPACT_GYRO_MIN     = 20.0f;
static const float HIGH_IMPACT_ACC_MIN      = 2.0f;   // at least 1 window must have peak > this
static const float HIGH_IMPACT_GYRO_MIN     = 300.0f; // AND peak > this (confirms violent fall event)
static const int   STILLNESS_SAMPLES        = 25;
static const float STILLNESS_ACC_MIN        = 0.6f;
static const float STILLNESS_ACC_MAX        = 1.7f;
static const float STILLNESS_GYRO_MAX       = 100.0f;
static const int      FALL_WATCH_WINDOWS       = 5;
static const uint32_t FALL_STILL_DURATION_MS   = 5000;  // cần nằm im liên tục bao lâu
static const uint32_t FALL_MONITOR_TIMEOUT_MS  = 10000; // tối đa bao lâu để theo dõi sau fall

// =====================================================================
// BLE UUIDs
// =====================================================================
#define AIFD_SVC_UUID      "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHAR_ALERT_UUID    "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define CHAR_VITALS_UUID   "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1"
#define CHAR_CONTROL_UUID  "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03"

// =====================================================================
// BLE GLOBAL STATE
// =====================================================================
static NimBLEServer*         gBleServer    = nullptr;
static NimBLEService*        gBleService   = nullptr;
static NimBLECharacteristic* gCharAlert    = nullptr;
static NimBLECharacteristic* gCharVitals   = nullptr;
static bool                  gBleConnected = false;
static bool                  gBleReady     = false;
static uint32_t              gConnectCount = 0;

class BleServerCb : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer *s) override {
        (void)s;
        gBleConnected = true;
        gBleReady     = false;
        gConnectCount++;
        Serial.println("[BLE] *** Client connected — waiting for READY ***");
    }
    void onDisconnect(NimBLEServer *s) override {
        gBleConnected = false;
        gBleReady     = false;
        s->startAdvertising();
        Serial.println("[BLE] Client disconnected — re-advertising");
    }
};

// Helper — bypass the buggy `setValue<T>` template; always send the string body.
static inline void setStr(NimBLECharacteristic *c, const char *s) {
    c->setValue((uint8_t*)s, strlen(s));
}

class ControlCb : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic *c) override {
        std::string raw = c->getValue();
        String cmd = String(raw.c_str());
        cmd.trim();
        cmd.toUpperCase();
        if (cmd == "READY") {
            gBleReady = true;
            setStr(c, "ACK:READY");
            Serial.println("[BLE] READY received — handshake complete");
        } else if (cmd == "PING") {
            setStr(c, "ACK:PING");
            Serial.println("[BLE] PING -> ACK:PING");
        } else {
            setStr(c, "ERR:UNKNOWN_COMMAND");
            Serial.printf("[BLE] Unknown command: \"%s\"\n", cmd.c_str());
        }
    }
};

// =====================================================================
// LED STATE MACHINE — pipeline-reactive, no manual cycling
// =====================================================================
enum LedState : uint8_t {
    LED_IDLE = 0,      // all OFF  — no movement
    LED_MOVING,        // all ON   — activity detected (1–2 consecutive windows)
    LED_ACTIVE,        // GREEN    — activity gate met (3 windows), ready to analyse
    LED_CANDIDATE,     // G+Y      — candidate peak detected, AI can run
    LED_AI_FALL,       // G+Y+R    — AI says fall this window
    LED_BLINK_WATCH,   // 3 BLINK  — FALL_WATCH / STILL_TIMING (checking stillness)
    LED_ALARM          // 3 BLINK + BUZZER — confirmed fall
};
static const char *LED_STATE_NAMES[] = {
    "IDLE","MOVING","ACTIVE","CANDIDATE","AI_FALL","BLINK_WATCH","ALARM"
};

static volatile LedState gLedState   = LED_IDLE;
static bool              blinkLevel  = true;
static unsigned long     blinkLastMs = 0;

// Button debounce
static int           btnLastReading = HIGH;
static int           btnStable      = HIGH;
static unsigned long btnLastChange  = 0;

// =====================================================================
// FALL ALERT STATE — guards button SAFE logic
// =====================================================================
static volatile bool gFallAlertActive = false;

// Forward declaration so updateLedFromPipeline (defined in LED section) can
// read fallDetectState (defined in fall-detect section below).
enum FallDetectState : uint8_t { FDS_IDLE, FDS_FALL_WATCH, FDS_STILL_TIMING };
static FallDetectState fallDetectState = FDS_IDLE;

// =====================================================================
// IMU RING BUFFER
// =====================================================================
struct ImuSample {
    float ax = 0, ay = 0, az = 0;
    float gx = 0, gy = 0, gz = 0;
    uint32_t tsMs = 0;
};
static ImuSample gImuWindow[kWindowSize];
static int       gWindowHead            = 0;
static int       gWindowCount           = 0;
static int       gSamplesSinceInference = 0;

static SemaphoreHandle_t gImuMutex      = nullptr;
static TaskHandle_t      gInferenceTask = nullptr;
static ImuSample         gSnapshot[kWindowSize];

// =====================================================================
// TFLITE MICRO STATE
// =====================================================================
static uint8_t bmi160Addr = BMI160_ADDR_LOW;
static bool    bmiOk      = false;

namespace {
const tflite::Model*      model            = nullptr;
tflite::ErrorReporter*    errorReporter    = nullptr;
tflite::MicroInterpreter* interpreter      = nullptr;
TfLiteTensor*             inputTensor      = nullptr;
TfLiteTensor*             outputTensor     = nullptr;
uint8_t                   tensorArena[kTensorArenaSize];
int                       outputElementCount = 0;
bool                      modelOk          = false;
}

// =====================================================================
// SEQUENCE COUNTERS
// =====================================================================
static uint32_t gAlertSeq  = 0;
static uint32_t gVitalsSeq = 0;
static uint32_t gBmiSeq    = 0;

// =====================================================================
// LIVE BMI PEAK SNAPSHOT — written by inference task, read by loop()
// (single producer / single consumer, atomic on ESP32)
// =====================================================================
static volatile float    gLastPeakAcc  = 0.0f;   // g
static volatile float    gLastPeakGyro = 0.0f;   // dps
static volatile bool     gLastActive   = false;  // true if peak crossed activity threshold

// =====================================================================
// LED / BUZZER HELPERS
// =====================================================================
static void setLeds(bool g, bool y, bool r) {
    digitalWrite(PIN_LED_GREEN,  g ? HIGH : LOW);
    digitalWrite(PIN_LED_YELLOW, y ? HIGH : LOW);
    digitalWrite(PIN_LED_RED,    r ? HIGH : LOW);
}
static void buzzerOn()  { tone(PIN_BUZZER, BUZZER_FREQ_HZ); }
static void buzzerOff() { noTone(PIN_BUZZER); digitalWrite(PIN_BUZZER, LOW); }

static void applyLedState(LedState st) {
    switch (st) {
        case LED_IDLE:        setLeds(false, false, false); buzzerOff(); break;
        case LED_MOVING:      setLeds(true,  true,  true);  buzzerOff(); break;
        case LED_ACTIVE:      setLeds(true,  false, false); buzzerOff(); break;
        case LED_CANDIDATE:   setLeds(true,  true,  false); buzzerOff(); break;
        case LED_AI_FALL:     setLeds(true,  true,  true);  buzzerOff(); break;
        case LED_BLINK_WATCH:
            blinkLevel = true; blinkLastMs = millis();
            setLeds(true, true, true); buzzerOff(); break;
        case LED_ALARM:
            blinkLevel = true; blinkLastMs = millis();
            setLeds(true, true, true); buzzerOn();  break;
    }
}

static void setLedState(LedState next) {
    if (next == gLedState) return;
    LedState prev = gLedState;
    gLedState = next;
    if (prev == LED_ALARM && next != LED_ALARM) buzzerOff();
    Serial.printf("[LED] %s -> %s\n", LED_STATE_NAMES[prev], LED_STATE_NAMES[next]);
    applyLedState(next);
}

// Called from loop() — drives blink for both BLINK_WATCH (no buzzer) and ALARM
static void handleBlink() {
    LedState st = gLedState;
    if (st != LED_BLINK_WATCH && st != LED_ALARM) return;
    unsigned long now = millis();
    if ((unsigned long)(now - blinkLastMs) >= BLINK_INTERVAL_MS) {
        blinkLastMs = now;
        blinkLevel  = !blinkLevel;
        setLeds(blinkLevel, blinkLevel, blinkLevel);
    }
}

// Called at end of each inference window — sets LED to match current pipeline stage.
// gFallAlertActive=true keeps LED_ALARM locked; button press resets it.
static void updateLedFromPipeline(bool activityActive, int activityCount,
                                  bool candidateActive, bool isFall) {
    if (gFallAlertActive) return; // LED_ALARM already set by onFallConfirmed

    LedState next;
    if (fallDetectState != FDS_IDLE) {         // forward-declared below
        next = LED_BLINK_WATCH;
    } else if (isFall) {
        next = LED_AI_FALL;
    } else if (candidateActive && activityCount >= ACTIVITY_WINDOW_COUNT) {
        next = LED_CANDIDATE;
    } else if (activityCount >= ACTIVITY_WINDOW_COUNT) {
        next = LED_ACTIVE;
    } else if (activityActive) {
        next = LED_MOVING;
    } else {
        next = LED_IDLE;
    }
    setLedState(next);
}

// =====================================================================
// BLE NOTIFY HELPERS
// NOTE: NimBLE-Arduino 1.4.x exposes a buggy template overload
//       `setValue<T>(const T&)` that wins resolution against `const char *`
//       and sends sizeof(pointer)=4 garbage bytes instead of the string.
//       We bypass it with the explicit `(uint8_t*, size_t)` overload.
// =====================================================================
static void notifyAlert(const char *payload) {
    if (!gBleReady || !gCharAlert) return;
    gCharAlert->setValue((uint8_t*)payload, strlen(payload));
    gCharAlert->notify();
    Serial.printf("[BLE] ALERT notify: %s\n", payload);
}

static void notifyVitals(const char *payload) {
    if (!gBleReady || !gCharVitals) return;
    gCharVitals->setValue((uint8_t*)payload, strlen(payload));
    gCharVitals->notify();
    Serial.printf("[BLE] VITALS notify: %s\n", payload);
}

// =====================================================================
// VITALS SOURCE — HR / SpO2
// ---------------------------------------------------------------------
// HR & SpO2 are currently SIMULATED because no MAX30102 / PPG sensor is
// wired up yet. The simulator is isolated behind the two functions below
// so the rest of the firmware (BLE encoder, packet timing, sequence
// counters) never has to change when a real driver lands.
//
// To replace with a real sensor later:
//   1. Implement `readHrSample()` / `readSpo2Sample()` to return the
//      latest reading from the sensor driver (return 255 if not ready).
//   2. Keep the public contract identical: 8-bit values, 255 = invalid.
//   3. Remove the `esp_random()` calls and delete the SIMULATED tag.
// No BLE / parser changes are needed on either side.
// =====================================================================
static uint8_t readHrSample() {
    // TODO(real-sensor): replace with MAX30102/PPG driver read
    // Returns 60-100 bpm in normal operation, 255 if sensor not ready
    return (uint8_t)(60 + (esp_random() % 41));
}
static uint8_t readSpo2Sample() {
    // TODO(real-sensor): replace with MAX30102/PPG driver read
    // Returns 94-100% in normal operation, 255 if sensor not ready
    return (uint8_t)(94 + (esp_random() % 7));
}

// Emit BATCH packet — 5 HR/SpO2 samples spaced 5s, every 25s
static void sendVitalsBatch() {
    uint32_t nowSec = millis() / 1000;
    uint8_t hrs[5], spo2s[5];
    uint32_t tss[5];
    for (int i = 0; i < 5; i++) {
        hrs[i]   = readHrSample();
        spo2s[i] = readSpo2Sample();
        tss[i]   = nowSec - (uint32_t)(4 - i) * 5;
    }
    char buf[140];
    snprintf(buf, sizeof(buf),
             "BATCH,%lu,%u|%u|%u|%u|%u,%u|%u|%u|%u|%u,%lu|%lu|%lu|%lu|%lu",
             (unsigned long)++gVitalsSeq,
             hrs[0], hrs[1], hrs[2], hrs[3], hrs[4],
             spo2s[0], spo2s[1], spo2s[2], spo2s[3], spo2s[4],
             (unsigned long)tss[0], (unsigned long)tss[1],
             (unsigned long)tss[2], (unsigned long)tss[3],
             (unsigned long)tss[4]);
    notifyVitals(buf);
}

// =====================================================================
// BMI PEAK EMITTER — REAL data from BMI160, sent every 5s
// Format: BMI,<seq>,<ts_sec>,<peak_acc_g>,<peak_gyro_dps>,<active>
// Updated by inference task each window; loop() picks up and emits.
// =====================================================================
static void sendBmiSnapshot() {
    uint32_t nowSec = millis() / 1000;
    float    acc    = gLastPeakAcc;
    float    gyr    = gLastPeakGyro;
    int      active = gLastActive ? 1 : 0;
    char buf[80];
    snprintf(buf, sizeof(buf),
             "BMI,%lu,%lu,%.3f,%.1f,%d",
             (unsigned long)++gBmiSeq,
             (unsigned long)nowSec, acc, gyr, active);
    notifyVitals(buf);
}

// =====================================================================
// BMI160 I2C
// =====================================================================
static int16_t toInt16(uint8_t lsb, uint8_t msb) {
    return (int16_t)((msb << 8) | lsb);
}
static bool writeReg(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(bmi160Addr);
    Wire.write(reg); Wire.write(value);
    return Wire.endTransmission() == 0;
}
static bool readRegs(uint8_t reg, uint8_t *buf, size_t len) {
    Wire.beginTransmission(bmi160Addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    size_t got = Wire.requestFrom((int)bmi160Addr, (int)len, (int)true);
    if (got != len) return false;
    for (size_t i = 0; i < len; i++) buf[i] = Wire.read();
    return true;
}
static bool readReg(uint8_t reg, uint8_t &value) { return readRegs(reg, &value, 1); }

static bool detectBMI160() {
    uint8_t id = 0;
    bmi160Addr = BMI160_ADDR_LOW;
    if (readReg(REG_CHIP_ID, id) && id == BMI160_CHIP_ID) return true;
    bmi160Addr = BMI160_ADDR_HIGH;
    if (readReg(REG_CHIP_ID, id) && id == BMI160_CHIP_ID) return true;
    return false;
}
static bool initBMI160() {
    if (!detectBMI160()) return false;
    if (!writeReg(REG_CMD, 0x11)) return false; delay(10);
    if (!writeReg(REG_CMD, 0x15)) return false; delay(80);
    if (!writeReg(REG_ACC_CONF,  0x28)) return false;
    if (!writeReg(REG_ACC_RANGE, 0x03)) return false;
    if (!writeReg(REG_GYR_CONF,  0x28)) return false;
    if (!writeReg(REG_GYR_RANGE, 0x00)) return false;
    delay(10);
    return true;
}
static bool readImuSample(ImuSample &s) {
    uint8_t d[6];
    if (!readRegs(REG_ACC_DATA, d, 6)) return false;
    s.ax = toInt16(d[0], d[1]) / ACC_LSB_PER_G;
    s.ay = toInt16(d[2], d[3]) / ACC_LSB_PER_G;
    s.az = toInt16(d[4], d[5]) / ACC_LSB_PER_G;
    if (!readRegs(REG_GYR_DATA, d, 6)) return false;
    s.gx = toInt16(d[0], d[1]) / GYR_LSB_PER_DPS;
    s.gy = toInt16(d[2], d[3]) / GYR_LSB_PER_DPS;
    s.gz = toInt16(d[4], d[5]) / GYR_LSB_PER_DPS;
    s.tsMs = millis();
    return true;
}

// =====================================================================
// RING BUFFER HELPERS  (call only while holding gImuMutex)
// =====================================================================
static void pushSample(const ImuSample &s) {
    gImuWindow[gWindowHead] = s;
    gWindowHead = (gWindowHead + 1) % kWindowSize;
    if (gWindowCount < kWindowSize) gWindowCount++;
    gSamplesSinceInference++;
}
static void snapshotWindow(ImuSample *dst) {
    int start = (gWindowCount < kWindowSize) ? 0 : gWindowHead;
    for (int i = 0; i < kWindowSize; i++)
        dst[i] = gImuWindow[(start + i) % kWindowSize];
}

// =====================================================================
// TFLITE MICRO
// =====================================================================
static int8_t quantizeInput(float v) {
    float scale = inputTensor->params.scale;
    int   zp    = inputTensor->params.zero_point;
    int   q     = (int)lroundf(v / scale) + zp;
    if (q >  127) q =  127;
    if (q < -128) q = -128;
    return (int8_t)q;
}
static float dequantizeOutput(int8_t v) {
    return (v - outputTensor->params.zero_point) * outputTensor->params.scale;
}

static bool initModel() {
    model = tflite::GetModel(fall_detection_model_tflite);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.println("[MODEL] schema mismatch"); return false;
    }
    static tflite::MicroErrorReporter microErr;
    errorReporter = &microErr;
    static tflite::AllOpsResolver resolver;
    static tflite::MicroInterpreter si(model, resolver, tensorArena, kTensorArenaSize, errorReporter);
    interpreter = &si;
    if (interpreter->AllocateTensors() != kTfLiteOk) {
        Serial.println("[MODEL] AllocateTensors failed"); return false;
    }
    inputTensor  = interpreter->input(0);
    outputTensor = interpreter->output(0);
    outputElementCount = 1;
    for (int i = 0; i < outputTensor->dims->size; i++)
        outputElementCount *= outputTensor->dims->data[i];
    Serial.printf("[MODEL] ready (arena=%dKB out=%d)\n", kTensorArenaSize/1024, outputElementCount);
    return true;
}

// Returns true on success; fallProb=0 when any gate rejects.
// activityCount:    consecutive active windows (reset on idle).
// highImpactSeen:   true if any window in current streak had peak > HIGH_IMPACT thresholds.
// activityActiveOut: true if THIS window crossed the activity threshold.
// candidateActiveOut: true if THIS window crossed the candidate threshold.
static bool runInferenceOnSnapshot(const ImuSample *snap,
                                   float &fallProb,
                                   int   &activityCount,
                                   bool  &highImpactSeen,
                                   bool  &activityActiveOut,
                                   bool  &candidateActiveOut)
{
    fallProb = 0.0f;
    if (!modelOk) return false;

    float maxAcc = 0, maxGyr = 0;
    for (int i = 0; i < kWindowSize; i++) {
        float a = sqrtf(snap[i].ax*snap[i].ax + snap[i].ay*snap[i].ay + snap[i].az*snap[i].az);
        float g = sqrtf(snap[i].gx*snap[i].gx + snap[i].gy*snap[i].gy + snap[i].gz*snap[i].gz);
        if (a > maxAcc) maxAcc = a;
        if (g > maxGyr) maxGyr = g;
    }

    bool candidateActive = (maxAcc > CANDIDATE_ACC_THRESHOLD || maxGyr > CANDIDATE_GYRO_THRESHOLD);
    bool activityActive  = (maxAcc > ACTIVITY_ACC_THRESHOLD  || maxGyr > ACTIVITY_GYRO_THRESHOLD);

    activityActiveOut  = activityActive;
    candidateActiveOut = candidateActive;

    // Publish live BMI peak snapshot — picked up by BMI emitter for BLE notify
    gLastPeakAcc  = maxAcc;
    gLastPeakGyro = maxGyr;
    gLastActive   = activityActive;

    // Activity gate: 3 consecutive active windows; any idle window resets everything
    if (activityActive) {
        if (activityCount < ACTIVITY_WINDOW_COUNT) activityCount++;
        // Track if any window in this streak had a violent high-impact peak
        if (maxAcc > HIGH_IMPACT_ACC_MIN && maxGyr > HIGH_IMPACT_GYRO_MIN)
            highImpactSeen = true;
    } else {
        activityCount   = 0;
        highImpactSeen  = false;
    }

    Serial.printf("[GATE] acc=%.2fg gyro=%.1fdps  cand=%s  activity=%d/%d  highImpact=%s\n",
                  maxAcc, maxGyr,
                  candidateActive ? "yes" : "no",
                  activityCount, ACTIVITY_WINDOW_COUNT,
                  highImpactSeen ? "YES" : "no");

    if (!candidateActive || activityCount < ACTIVITY_WINDOW_COUNT) {
        return true;
    }

    // High-impact gate: among the 3 active windows, at least 1 must have had
    // peak_acc > 10g AND peak_gyro > 500 dps
    if (!highImpactSeen) {
        Serial.printf("[GATE] highImpact=no — need 1 window with acc>%.0fg AND gyro>%.0fdps\n",
                      HIGH_IMPACT_ACC_MIN, HIGH_IMPACT_GYRO_MIN);
        return true;
    }

    // Impact: require significant gyro rotation in window
    if (maxGyr < FALL_IMPACT_GYRO_MIN) {
        Serial.printf("[IMPACT] peak_gyro=%.1fdps < %.1fdps — reject\n", maxGyr, FALL_IMPACT_GYRO_MIN);
        return true;
    }

    for (int t = 0; t < kWindowSize; t++) {
        inputTensor->data.int8[t * kFeatureCount + 0] = quantizeInput(snap[t].ax);
        inputTensor->data.int8[t * kFeatureCount + 1] = quantizeInput(snap[t].ay);
        inputTensor->data.int8[t * kFeatureCount + 2] = quantizeInput(snap[t].az);
        inputTensor->data.int8[t * kFeatureCount + 3] = quantizeInput(snap[t].gx);
        inputTensor->data.int8[t * kFeatureCount + 4] = quantizeInput(snap[t].gy);
        inputTensor->data.int8[t * kFeatureCount + 5] = quantizeInput(snap[t].gz);
    }
    if (interpreter->Invoke() != kTfLiteOk) {
        Serial.println("[MODEL] invoke failed"); return false;
    }
    fallProb = (outputElementCount == 1)
        ? constrain(dequantizeOutput(outputTensor->data.int8[0]), 0.0f, 1.0f)
        : dequantizeOutput(outputTensor->data.int8[1]);
    return true;
}

static bool checkStillness(const ImuSample *snap) {
    float accSum = 0, gyrSum = 0;
    int   start  = kWindowSize - STILLNESS_SAMPLES;
    for (int i = start; i < kWindowSize; i++) {
        accSum += sqrtf(snap[i].ax*snap[i].ax + snap[i].ay*snap[i].ay + snap[i].az*snap[i].az);
        gyrSum += sqrtf(snap[i].gx*snap[i].gx + snap[i].gy*snap[i].gy + snap[i].gz*snap[i].gz);
    }
    float mA = accSum / STILLNESS_SAMPLES;
    float mG = gyrSum / STILLNESS_SAMPLES;
    Serial.printf("[STILL] mean_acc=%.2fg mean_gyro=%.1fdps -> %s\n", mA, mG,
                  (mA >= STILLNESS_ACC_MIN && mA <= STILLNESS_ACC_MAX && mG <= STILLNESS_GYRO_MAX)
                  ? "STILL" : "moving");
    return (mA >= STILLNESS_ACC_MIN && mA <= STILLNESS_ACC_MAX && mG <= STILLNESS_GYRO_MAX);
}

// =====================================================================
// FALL DETECT STATE MACHINE
// (FallDetectState enum + fallDetectState already declared above for LED)
// =====================================================================
static int             fallWatchLeft       = 0;
static uint32_t        monitorStartMs      = 0;    // khi nào bắt đầu vào STILL_TIMING
static uint32_t        stillnessStartMs    = 0;
static bool            stillnessTimerArmed = false;
static float           gLastFallProb       = 0.0f;

static void onFallConfirmed(float fallProb) {
    gFallAlertActive = true;
    setLedState(LED_ALARM);

    char buf[80];
    uint32_t tsSec = millis() / 1000;
    snprintf(buf, sizeof(buf),
             "ALERT,%lu,%lu,fall,1,%.3f,%.3f",
             (unsigned long)++gAlertSeq,
             (unsigned long)tsSec,
             fallProb,
             1.0f - fallProb);
    notifyAlert(buf);
}

// cancelActive: true nếu peak window vượt ngưỡng HUỶ (cao hơn ngưỡng activity thông thường).
// Dùng ngưỡng riêng để tránh huỷ nhầm do phản xạ ngã (lăn người, giơ tay) — chỉ huỷ
// khi chuyển động đủ mạnh để khẳng định người vẫn hoàn toàn bình thường.
static void updateFallStateMachine(float fallProb, bool stillnessNow, bool activityActive,
                                   float peakAcc, float peakGyr) {
    bool isFall      = (fallProb >= FALL_DECISION_THRESHOLD);
    bool cancelActive = (peakAcc > CANCEL_ACC_THRESHOLD || peakGyr > CANCEL_GYRO_THRESHOLD);

    switch (fallDetectState) {
        case FDS_IDLE:
            if (isFall && stillnessNow) {
                gLastFallProb   = fallProb;
                fallDetectState = FDS_FALL_WATCH;
                fallWatchLeft   = FALL_WATCH_WINDOWS - 1;
                Serial.printf("[FSM] IDLE -> FALL_WATCH (left=%d)\n", fallWatchLeft);
            }
            break;

        case FDS_FALL_WATCH:
            // Chỉ huỷ khi chuyển động vượt ngưỡng cancel (3.5g/150dps) —
            // phản xạ nhỏ sau ngã không đủ để huỷ
            if (cancelActive) {
                fallDetectState = FDS_IDLE;
                Serial.printf("[FSM] FALL_WATCH: strong activity (%.2fg/%.1fdps) -> IDLE\n",
                              peakAcc, peakGyr);
                break;
            }
            if (fallWatchLeft > 0) {
                fallWatchLeft--;
                Serial.printf("[FSM] FALL_WATCH left=%d\n", fallWatchLeft);
            } else {
                fallDetectState     = FDS_STILL_TIMING;
                monitorStartMs      = millis();
                stillnessTimerArmed = false;
                Serial.println("[FSM] FALL_WATCH -> STILL_TIMING (monitor timeout=10s)");
            }
            break;

        case FDS_STILL_TIMING: {
            uint32_t monitorElapsed = millis() - monitorStartMs;
            bool isMoving = (cancelActive || !stillnessNow);

            // Monitoring timeout — hết cửa sổ theo dõi
            if (monitorElapsed >= FALL_MONITOR_TIMEOUT_MS) {
                fallDetectState     = FDS_IDLE;
                stillnessTimerArmed = false;
                // Dù đang nằm im hay cử động lúc timeout → đều an toàn
                // (substance chưa hoàn thành thì cũng không báo)
                Serial.printf("[FSM] STILL_TIMING: timeout %lums -> IDLE (safe)\n",
                              (unsigned long)monitorElapsed);
                break;
            }

            if (isMoving) {
                // Cử động → reset substance, VẪN trong STILL_TIMING
                if (stillnessTimerArmed) {
                    stillnessTimerArmed = false;
                    Serial.printf("[FSM] STILL_TIMING: %s -> substance reset (monitor=%lums/%lums)\n",
                                  activityActive ? "activity" : "motion",
                                  (unsigned long)monitorElapsed,
                                  (unsigned long)FALL_MONITOR_TIMEOUT_MS);
                }
            } else {
                // Nằm im → arm substance nếu chưa có
                if (!stillnessTimerArmed) {
                    stillnessTimerArmed = true;
                    stillnessStartMs    = millis();
                    Serial.printf("[FSM] STILL_TIMING: nằm im -> arm substance (monitor=%lums left)\n",
                                  (unsigned long)(FALL_MONITOR_TIMEOUT_MS - monitorElapsed));
                }
                uint32_t stillElapsed = millis() - stillnessStartMs;
                Serial.printf("[FSM] STILL_TIMING: still=%lums/%lums  monitor=%lums/%lums\n",
                              (unsigned long)stillElapsed, (unsigned long)FALL_STILL_DURATION_MS,
                              (unsigned long)monitorElapsed, (unsigned long)FALL_MONITOR_TIMEOUT_MS);
                if (stillElapsed >= FALL_STILL_DURATION_MS) {
                    fallDetectState     = FDS_IDLE;
                    stillnessTimerArmed = false;
                    onFallConfirmed(gLastFallProb);
                }
            }
            break;
        }
    }
}

// =====================================================================
// TASK 1: IMU SAMPLING — Core 0, priority MAX-1
// =====================================================================
static void taskSampling(void *pvParams) {
    TickType_t xLastWake = xTaskGetTickCount();
    while (true) {
        vTaskDelayUntil(&xLastWake, pdMS_TO_TICKS(SAMPLE_PERIOD_MS));
        if (!bmiOk) continue;
        ImuSample s;
        if (!readImuSample(s)) { Serial.println("[IMU] read failed"); continue; }

        xSemaphoreTake(gImuMutex, portMAX_DELAY);
        pushSample(s);
        bool windowReady = (gWindowCount >= kWindowSize) && (gSamplesSinceInference >= kInferenceStride);
        if (windowReady) gSamplesSinceInference = 0;
        xSemaphoreGive(gImuMutex);

        if (windowReady && gInferenceTask != nullptr)
            xTaskNotifyGive(gInferenceTask);
    }
}

// =====================================================================
// TASK 2: INFERENCE — Core 1, priority 1
// =====================================================================
static void taskInference(void *pvParams) {
    static uint32_t inferenceCount = 0;
    static int      activityCount  = 0;
    static bool     highImpactSeen = false;

    while (true) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        xSemaphoreTake(gImuMutex, portMAX_DELAY);
        snapshotWindow(gSnapshot);
        xSemaphoreGive(gImuMutex);

        // While alarm active: skip inference but still update LED (keeps LED_ALARM)
        if (gFallAlertActive) { updateLedFromPipeline(false, 0, false, false); continue; }

        uint32_t t0 = millis();
        float fallProb       = 0.0f;
        bool  activityActive = false;
        bool  candidateActive= false;
        bool ok = runInferenceOnSnapshot(gSnapshot, fallProb, activityCount,
                                         highImpactSeen, activityActive, candidateActive);
        uint32_t latencyMs = millis() - t0;
        inferenceCount++;

        if (!ok) { Serial.println("[AI] inference error"); continue; }

        bool isFall = (fallProb >= FALL_DECISION_THRESHOLD);
        Serial.printf("[INFER] #%lu  fall_prob=%.3f  latency=%lums  -> %s\n",
                      inferenceCount, fallProb, latencyMs, isFall ? "FALL?" : "non-fall");

        bool stillnessNow = checkStillness(gSnapshot);
        updateFallStateMachine(fallProb, stillnessNow, activityActive,
                               gLastPeakAcc, gLastPeakGyro); // may trigger LED_ALARM
        updateLedFromPipeline(activityActive, activityCount, candidateActive, isFall);
    }
}

// =====================================================================
// BUTTON — debounce + dual action
// =====================================================================
static void handleButton() {
    int reading       = digitalRead(PIN_BUTTON);
    unsigned long now = millis();
    if (reading != btnLastReading) { btnLastChange = now; btnLastReading = reading; }
    if ((unsigned long)(now - btnLastChange) >= DEBOUNCE_MS && reading != btnStable) {
        btnStable = reading;
        if (btnStable != LOW) return;

        char buf[64];
        uint32_t tsSec = millis() / 1000;

        if (gFallAlertActive) {
            // Đang alarm → "I'm Safe": tắt loa, gửi SAFE
            gFallAlertActive = false;
            fallDetectState  = FDS_IDLE;
            setLedState(LED_IDLE);
            snprintf(buf, sizeof(buf), "SAFE,%lu,%lu",
                     (unsigned long)++gAlertSeq, (unsigned long)tsSec);
            notifyAlert(buf);
            Serial.printf("[BTN] Safe confirmed — sent: %s\n", buf);
        } else {
            // Bình thường → trigger fall thủ công (SOS / test)
            fallDetectState = FDS_IDLE; // cancel any pending FSM state
            snprintf(buf, sizeof(buf), "ALERT,%lu,%lu,fall,1,1.000,0.000",
                     (unsigned long)++gAlertSeq, (unsigned long)tsSec);
            gFallAlertActive = true;
            setLedState(LED_ALARM);
            notifyAlert(buf);
            Serial.printf("[BTN] Manual fall triggered — sent: %s\n", buf);
        }
    }
}

// =====================================================================
// VITALS BATCH TIMER — every 25 s (HR/SpO2 history)
// =====================================================================
static void handleVitalsBatch() {
    static uint32_t lastBatchMs = 0;
    uint32_t now = millis();
    if ((uint32_t)(now - lastBatchMs) >= 25000) {
        lastBatchMs = now;
        sendVitalsBatch();
    }
}

// =====================================================================
// BMI SNAPSHOT TIMER — every 5 s (live IMU peak from BMI160)
// =====================================================================
static void handleBmiSnapshot() {
    static uint32_t lastBmiMs = 0;
    uint32_t now = millis();
    if ((uint32_t)(now - lastBmiMs) >= 5000) {
        lastBmiMs = now;
        sendBmiSnapshot();
    }
}

// =====================================================================
// ARDUINO ENTRY
// =====================================================================
void setup() {
    Serial.begin(115200);
    delay(300);
    Serial.println();
    Serial.println("=======================================================");
    Serial.println("ESP32-S3  AIFD  S3_BLE_test_2  [integration test]");
    Serial.println("  Fall: real BMI160 + TFLite V84");
    Serial.println("  Vitals: simulated HR/SpO2 every 25s");
    Serial.println("  Button: SAFE during alarm, cycle LED otherwise");
    Serial.println("=======================================================");

    // GPIO
    pinMode(PIN_LED_GREEN,  OUTPUT);
    pinMode(PIN_LED_YELLOW, OUTPUT);
    pinMode(PIN_LED_RED,    OUTPUT);
    pinMode(PIN_BUTTON,     INPUT_PULLUP);
    pinMode(PIN_BUZZER,     OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
    tone(PIN_BUZZER, BUZZER_FREQ_HZ); noTone(PIN_BUZZER); // init LEDC at real freq (1Hz fails on S3)

    // I2C
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
    Wire.setClock(100000);
    Wire.setTimeOut(20);
    delay(50);

    // BMI160
    bmiOk = initBMI160();
    Serial.printf("[BMI]   %s (addr=0x%02X)\n", bmiOk ? "OK" : "NOT FOUND", bmi160Addr);

    // TFLite model
    modelOk = initModel();
    if (!modelOk) Serial.println("[MODEL] init failed — fall detection disabled");

    // FreeRTOS
    gImuMutex = xSemaphoreCreateMutex();
    configASSERT(gImuMutex);

    xTaskCreatePinnedToCore(taskSampling, "IMU_SAMPLE", 4096, nullptr,
                            configMAX_PRIORITIES - 1, nullptr, 0);
    xTaskCreatePinnedToCore(taskInference, "AI_INFER",  8192, nullptr,
                            1, &gInferenceTask, 1);

    // BLE setup — service registered before advertising (Android UUID filter requirement)
    NimBLEDevice::init("S3_AIFD Wearable_test");
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);
    NimBLEDevice::setSecurityAuth(BLE_SM_PAIR_AUTHREQ_BOND);
    gBleServer = NimBLEDevice::createServer();
    gBleServer->setCallbacks(new BleServerCb());

    gBleService = gBleServer->createService(AIFD_SVC_UUID);

    gCharAlert  = gBleService->createCharacteristic(CHAR_ALERT_UUID,
                      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
    gCharVitals = gBleService->createCharacteristic(CHAR_VITALS_UUID,
                      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
    auto *cCtrl = gBleService->createCharacteristic(CHAR_CONTROL_UUID,
                      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE);
    cCtrl->setCallbacks(new ControlCb());

    // Initial values — use setStr() to bypass the NimBLE template overload bug
    setStr(gCharAlert,  "ALERT,0,0,idle,0,0.000,1.000");
    setStr(gCharVitals, "BATCH,0,255|255|255|255|255,255|255|255|255|255,0|0|0|0|0");
    setStr(cCtrl,       "WAITING_READY");

    gBleService->start();

    NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
    adv->addServiceUUID(AIFD_SVC_UUID);
    adv->setScanResponse(true);
    adv->start();

    setLedState(LED_IDLE);
    Serial.println("[BOOT] Tasks started. Advertising as \"S3_AIFD Wearable_test\"");
}

void loop() {
    handleButton();
    handleBlink();
    handleVitalsBatch();
    handleBmiSnapshot();

    static uint32_t lastStatusMs = 0;
    uint32_t now = millis();
    if ((uint32_t)(now - lastStatusMs) >= 5000) {
        lastStatusMs = now;
        Serial.printf("[BLE]  status=%-11s  handshake=%-7s  sessions=%lu  uptime=%lus\n",
                      gBleConnected ? "CONNECTED" : "advertising",
                      gBleReady     ? "READY"     : "waiting",
                      (unsigned long)gConnectCount,
                      (unsigned long)(now / 1000));
    }

    delay(10);
}
