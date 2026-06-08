/**
 * S3_AIFD_V2(Pin) — src/main.cpp
 *
 * Adaptive, event-driven RTOS firmware for AIFD ESP32-S3.
 * Power-optimized refactor of S3_AIFD_V1 — SAME fall-detection pipeline,
 * SAME BLE UUIDs / packet formats / V84 TFLite model.
 *
 * ── ADAPTIVE SYSTEM-MODE DESIGN ───────────────────────────────────────
 * The device no longer runs 50 Hz IMU sampling + BLE streaming continuously.
 * Instead it lives in a lightweight idle monitor and only spins up the full
 * 50 Hz pipeline when motion is detected.
 *
 *   MODE_IDLE_MONITOR  : LED off. Only a 10 Hz BMI160 motion poll runs.
 *                        High-rate IMU task is BLOCKED. No BLE streaming.
 *   MODE_MOTION_CAPTURE: 50 Hz sampling, fills exactly 100-sample / 2 s
 *                        windows and notifies the AI task.
 *   MODE_AI_INFERENCE  : the gate→TinyCNN inference runs (within capture).
 *   MODE_FALL_WATCH    : 50 Hz continues for stillness confirmation.
 *   MODE_ALERT         : BLE ALERT sent, red LED + buzzer.
 *   MODE_COOLDOWN      : transient after SAFE/timeout, then idle.
 *   MODE_CONNECTED_LIVE: app requested live BMI/vitals streaming.
 *
 * Only ONE task touches the IMU at a time:
 *   - MotionMonitor reads I2C ONLY while MODE_IDLE_MONITOR.
 *   - HighRateImu   reads I2C ONLY while capturing (non-idle).
 * A dedicated I2C mutex additionally guards every Wire transaction (BMI160
 * + MAX30102) so the two sensors never corrupt the bus.
 *
 * BLE Packet formats (unchanged — ref: BLE_PROTOCOL.md):
 *   ALERT,<seq>,<ts_sec>,fall,1,<fall_prob>,<non_fall_prob>
 *   SAFE,<seq>,<ts_sec>
 *   BATCH,<seq>,<hr0|hr1|hr2|hr3|hr4>,<spo2_0|...|spo2_4>,<ts0|...|ts4>
 *   BMI,<seq>,<ts_sec>,<peak_acc_g>,<peak_gyro_dps>,<active>
 */

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"
#include "freertos/timers.h"

#include "fall_detection_v84.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include <NimBLEDevice.h>
#include <Adafruit_NeoPixel.h>
#include <string>
#include "MAX30105.h"

// =====================================================================
// COMPILE-TIME DEBUG FLAGS  (set all to 0 for production / lowest power)
// =====================================================================
#define DEBUG_LOG            1   // master serial log (set 0 in production)
#define ENABLE_MAX_DEBUG     0   // MAX30102 IR debug
#define ENABLE_BMI_DEBUG     0   // per-window gate/inference logs
#define ENABLE_BLE_STATUS_LOG 0  // periodic BLE status line

#if DEBUG_LOG
  #define LOGF(...) Serial.printf(__VA_ARGS__)
  #define LOGLN(x)  Serial.println(x)
#else
  #define LOGF(...)
  #define LOGLN(x)
#endif

#if (DEBUG_LOG && ENABLE_BMI_DEBUG)
  #define BMI_LOGF(...) Serial.printf(__VA_ARGS__)
  #define BMI_LOGLN(x)  Serial.println(x)
#else
  #define BMI_LOGF(...)
  #define BMI_LOGLN(x)
#endif

// =====================================================================
// PIN CONFIG
// =====================================================================
static const int PIN_LED_VCC = 4;   // RGB module power (GPIO-driven)
static const int PIN_LED_DI  = 5;   // WS2812 data in
//                         6        // DO — unused (data out to next LED)
static const int PIN_BUZZER  = 7;
static const int PIN_BUTTON     = 10;
static const int PIN_I2C_SDA   = 8;
static const int PIN_I2C_SCL   = 9;

static const unsigned int  BUZZER_FREQ_HZ    = 2300;
static const unsigned long DEBOUNCE_MS       = 30;
static const unsigned long BLINK_SLOW_MS     = 500;
static const unsigned long BLINK_FAST_MS     = 250;

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
// SAMPLING + MODEL CONFIG  (unchanged from V1 — model contract)
// =====================================================================
static const uint32_t SAMPLE_PERIOD_MS  = 20;   // 50 Hz during motion capture
static const int      kWindowSize       = 100;  // 100 samples = 2 s @ 50 Hz
static const int      kFeatureCount     = 6;
static const int      kInferenceStride  = 100;
static const int      kTensorArenaSize  = 60 * 1024;

// V84 optimal threshold + gates (unchanged — safety-critical)
static const float FALL_DECISION_THRESHOLD  = 0.42f;
static const float CANDIDATE_ACC_THRESHOLD  = 7.5f;
static const float CANDIDATE_GYRO_THRESHOLD = 240.0f;
static const float ACTIVITY_ACC_THRESHOLD   = 2.0f;
static const float ACTIVITY_GYRO_THRESHOLD  = 50.0f;
static const float CANCEL_ACC_THRESHOLD     = 3.5f;
static const float CANCEL_GYRO_THRESHOLD    = 150.0f;
static const int   ACTIVITY_WINDOW_COUNT    = 3;
static const float FALL_IMPACT_GYRO_MIN     = 20.0f;
static const float HIGH_IMPACT_ACC_MIN      = 2.0f;
static const float HIGH_IMPACT_GYRO_MIN     = 300.0f;
static const int   STILLNESS_SAMPLES        = 25;
static const float STILLNESS_ACC_MIN        = 0.6f;
static const float STILLNESS_ACC_MAX        = 1.7f;
static const float STILLNESS_GYRO_MAX       = 100.0f;
static const int      FALL_WATCH_WINDOWS       = 5;
static const uint32_t FALL_STILL_DURATION_MS   = 5000;
static const uint32_t FALL_MONITOR_TIMEOUT_MS  = 10000;
static const uint32_t AI_WINDOW_DURATION_MS    = 6000;

// =====================================================================
// ADAPTIVE RTOS CONFIG  (NEW)
// =====================================================================
// Idle motion poll: sensitive, low-rate. Thresholds are well BELOW the real
// activity gate (2 g / 50 dps) so the device wakes EARLY and the first 2 s
// capture window still contains the fall context (pre-impact + impact).
static const uint32_t MOTION_MONITOR_PERIOD_MS = 100;   // 10 Hz idle poll
static const float    MOTION_WAKE_ACC_DEV_G    = 0.20f; // |‖a‖-1g| wake thresh
static const float    MOTION_WAKE_GYRO_DPS     = 30.0f; // gyro wake thresh
// Extra quiet 2 s windows required before returning to idle (guarantees the
// high-rate path stays alive ≥1 full window after motion stops).
static const int      MAX_QUIET_WINDOWS        = 1;
static const uint32_t VITALS_PERIOD_MS         = 25000; // HR/SpO2 batch cadence

// =====================================================================
// BLE UUIDs  (unchanged)
// =====================================================================
#define AIFD_SVC_UUID      "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHAR_ALERT_UUID    "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define CHAR_VITALS_UUID   "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1"
#define CHAR_CONTROL_UUID  "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03"

// =====================================================================
// SYSTEM MODE STATE MACHINE  (NEW — drives task gating + power behaviour)
// =====================================================================
enum SystemMode : uint8_t {
    MODE_IDLE_MONITOR = 0, // LED off, 10 Hz motion poll, high-rate blocked
    MODE_MOTION_CAPTURE,   // 50 Hz capture, 100-sample windows → AI
    MODE_AI_INFERENCE,     // gate + TinyCNN inference (within capture)
    MODE_FALL_WATCH,       // 50 Hz continues for stillness confirmation
    MODE_ALERT,            // ALERT sent, red LED + buzzer
    MODE_COOLDOWN,         // transient post-SAFE / timeout
    MODE_CONNECTED_LIVE    // app requested live streaming
};
static const char *MODE_NAMES[] = {
    "IDLE_MONITOR", "MOTION_CAPTURE", "AI_INFERENCE",
    "FALL_WATCH", "ALERT", "COOLDOWN", "CONNECTED_LIVE"
};
static volatile SystemMode gSystemMode = MODE_IDLE_MONITOR;

static inline void setSystemMode(SystemMode m) {
    if (m == gSystemMode) return;
    LOGF("[MODE] %s -> %s\n", MODE_NAMES[gSystemMode], MODE_NAMES[m]);
    gSystemMode = m;
}

// True while the HighRateImu task is actively capturing (owns the I2C bus).
static volatile bool gHighRateRunning = false;
// App requested live BMI/vitals streaming (control "LIVE"/"IDLE").
static volatile bool gLiveMode = false;

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

// ── BLE TX QUEUE ──────────────────────────────────────────────────────
// Only BleTask calls notify(). Every other task pushes a message here, so
// the NimBLE stack is driven from a single context.
struct BleMsg {
    uint8_t target;        // 0 = ALERT char, 1 = VITALS char
    char    data[160];
};
static QueueHandle_t gBleQueue = nullptr;

static void enqueueBle(uint8_t target, const char *payload, bool front) {
    if (!gBleQueue) return;
    BleMsg m;
    m.target = target;
    strncpy(m.data, payload, sizeof(m.data) - 1);
    m.data[sizeof(m.data) - 1] = '\0';
    if (front) xQueueSendToFront(gBleQueue, &m, 0);
    else       xQueueSendToBack(gBleQueue, &m, 0);
}
// ALERT/SAFE jump the queue; vitals go to the back.
static void notifyAlert(const char *payload) {
    if (!gBleReady) return;
    enqueueBle(0, payload, /*front=*/true);
}
static void notifyVitals(const char *payload) {
    if (!gBleReady) return;
    enqueueBle(1, payload, /*front=*/false);
}

// Helper — bypass the buggy `setValue<T>` template; always send the string body.
static inline void setStr(NimBLECharacteristic *c, const char *s) {
    c->setValue((uint8_t*)s, strlen(s));
}

static void sendInstantVitals();

class BleServerCb : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer *s) override {
        (void)s;
        gBleConnected = true;
        gBleReady     = false;   // wait for READY handshake before streaming
        gConnectCount++;
        LOGLN("[BLE] *** Client connected — waiting for READY ***");
    }
    void onDisconnect(NimBLEServer *s) override {
        gBleConnected = false;
        gBleReady     = false;
        gLiveMode     = false;
        s->startAdvertising();
        LOGLN("[BLE] Client disconnected — re-advertising");
    }
};

class ControlCb : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic *c) override {
        std::string raw = c->getValue();
        String cmd = String(raw.c_str());
        cmd.trim();
        cmd.toUpperCase();
        if (cmd == "READY") {
            gBleReady = true;
            setStr(c, "ACK:READY");
            LOGLN("[BLE] READY received — handshake complete");
            sendInstantVitals();
        } else if (cmd == "PING") {
            setStr(c, "ACK:PING");
            LOGLN("[BLE] PING -> ACK:PING");
        } else if (cmd == "LIVE") {
            gLiveMode = true;            // app wants live BMI/vitals
            setStr(c, "ACK:LIVE");
            LOGLN("[BLE] LIVE mode enabled");
        } else if (cmd == "IDLE") {
            gLiveMode = false;
            setStr(c, "ACK:IDLE");
            LOGLN("[BLE] LIVE mode disabled");
        } else {
            setStr(c, "ERR:UNKNOWN_COMMAND");
            LOGF("[BLE] Unknown command: \"%s\"\n", cmd.c_str());
        }
    }
};

// =====================================================================
// LED STATE MACHINE  (mode-aware; OFF during idle to save power)
// LED is rendered ONLY by gLedTask. Blinking states wake it on an interval;
// solid/off states block it until the next setLedState() notification.
// =====================================================================
enum LedState : uint8_t {
    LED_BOOT = 0,     // blue blink — device initialising
    LED_IDLE,         // OFF — idle monitoring / connected but quiet
    LED_WARNING,      // yellow fast blink — sensor error (permanent)
    LED_FALL_WATCH,   // red slow blink — fall candidate, checking stillness
    LED_ALARM         // red fast blink + buzzer — fall confirmed
};
static const char *LED_STATE_NAMES[] = {
    "BOOT(Blue)", "IDLE(Off)", "WARNING(Yellow)", "FALL_WATCH(Red)", "ALARM(Red)"
};

static volatile LedState gLedState  = LED_BOOT;
static bool              blinkLevel  = true;
static TaskHandle_t      gLedTask    = nullptr;

static Adafruit_NeoPixel gLedNeo(1, PIN_LED_DI, NEO_GRB + NEO_KHZ800);
static const uint32_t CLR_BLUE   = 0x0000FFu;
static const uint32_t CLR_YELLOW = 0xFFA500u;
static const uint32_t CLR_RED    = 0xFF0000u;
static const uint32_t CLR_OFF    = 0x000000u;

static void ledSet(uint32_t color) {  // ONLY called from gLedTask
    gLedNeo.setPixelColor(0, color);
    gLedNeo.show();
}
static void buzzerOn()  { tone(PIN_BUZZER, BUZZER_FREQ_HZ); }
static void buzzerOff() { noTone(PIN_BUZZER); digitalWrite(PIN_BUZZER, LOW); }

// Blink interval per state (0 = solid / no blink).
static uint32_t ledIntervalMs(LedState st) {
    switch (st) {
        case LED_BOOT:       return BLINK_SLOW_MS;
        case LED_FALL_WATCH: return BLINK_SLOW_MS;
        case LED_WARNING:    return BLINK_FAST_MS;
        case LED_ALARM:      return BLINK_FAST_MS;
        case LED_IDLE:
        default:             return 0;
    }
}
static uint32_t ledColor(LedState st) {
    switch (st) {
        case LED_BOOT:       return CLR_BLUE;
        case LED_WARNING:    return CLR_YELLOW;
        case LED_FALL_WATCH: return CLR_RED;
        case LED_ALARM:      return CLR_RED;
        case LED_IDLE:
        default:             return CLR_OFF;
    }
}
static void renderLed() {
    LedState st = gLedState;
    uint32_t iv = ledIntervalMs(st);
    if (iv == 0) { ledSet(ledColor(st)); return; }  // solid (IDLE = off)
    blinkLevel = !blinkLevel;
    ledSet(blinkLevel ? ledColor(st) : CLR_OFF);
}
static void taskLed(void *pv) {
    (void)pv;
    for (;;) {
        uint32_t iv = ledIntervalMs(gLedState);
        TickType_t wait = (iv == 0) ? portMAX_DELAY : pdMS_TO_TICKS(iv);
        ulTaskNotifyTake(pdTRUE, wait);   // wakes on interval OR on state change
        renderLed();
    }
}
static void setLedState(LedState next) {
    if (next == gLedState) return;
    LedState prev = gLedState;
    gLedState = next;
    if (next == LED_ALARM)      buzzerOn();
    else if (prev == LED_ALARM) buzzerOff();
    blinkLevel = true;
    LOGF("[LED] %s -> %s\n", LED_STATE_NAMES[prev], LED_STATE_NAMES[next]);
    if (gLedTask) xTaskNotifyGive(gLedTask);   // render immediately
}

// =====================================================================
// FALL ALERT STATE — guards button SAFE logic
// =====================================================================
static volatile bool gFallAlertActive = false;
enum FallDetectState : uint8_t { FDS_IDLE, FDS_FALL_WATCH, FDS_STILL_TIMING };
static FallDetectState fallDetectState = FDS_IDLE;

// Return LED + system mode to idle monitoring. If the high-rate task is still
// running it keeps ownership of the bus and will drop to IDLE itself once quiet;
// otherwise we hand control straight back to the idle motion monitor.
static void returnToMonitoring() {
    setLedState(LED_IDLE);
    if (gHighRateRunning) setSystemMode(MODE_MOTION_CAPTURE);
    else                  setSystemMode(MODE_IDLE_MONITOR);
}

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

static SemaphoreHandle_t gImuMutex      = nullptr;  // guards ring buffer
static SemaphoreHandle_t gI2cMutex      = nullptr;  // guards Wire (BMI + MAX)
static TaskHandle_t      gMotionTask    = nullptr;
static TaskHandle_t      gHighRateTask  = nullptr;
static TaskHandle_t      gInferenceTask = nullptr;
static TaskHandle_t      gButtonTask    = nullptr;
static TaskHandle_t      gBleTask       = nullptr;
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

// LIVE BMI PEAK SNAPSHOT — written by inference task, read by emitters
static volatile float gLastPeakAcc  = 0.0f;
static volatile float gLastPeakGyro = 0.0f;
static volatile bool  gLastActive   = false;

// =====================================================================
// VITALS SOURCE — HR / SpO2  (SIMULATED until PPG driver lands)
// =====================================================================
static MAX30105 particleSensor;
static bool maxOk = false;

// All MAX30102 I2C access funnels through here so it can't collide with BMI160.
static long maxGetIR() {
    if (!maxOk) return 0;
    xSemaphoreTake(gI2cMutex, portMAX_DELAY);
    long v = particleSensor.getIR();
    xSemaphoreGive(gI2cMutex);
    return v;
}

static uint8_t readHrSample() {
    if (!maxOk) return 255;
    if (maxGetIR() < 50000) return 255;
    return (uint8_t)(65 + (esp_random() % 26));   // Fake data: 65-90 bpm
}
static uint8_t readSpo2Sample() {
    if (!maxOk) return 255;
    if (maxGetIR() < 50000) return 255;
    return (uint8_t)(93 + (esp_random() % 7));     // Fake data: 93-99%
}

// Emit single immediate packet on READY handshake
static void sendInstantVitals() {
    uint32_t nowSec = millis() / 1000;
    uint8_t hr = readHrSample();
    uint8_t spo2 = readSpo2Sample();
    char buf[80];
    snprintf(buf, sizeof(buf), "BATCH,%lu,%u,%u,%lu",
             (unsigned long)++gVitalsSeq, hr, spo2, (unsigned long)nowSec);
    notifyVitals(buf);
}

// Emit BATCH packet — 5 HR/SpO2 samples spaced 5 s, every VITALS_PERIOD_MS
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

// BMI peak snapshot — only emitted in live mode (no idle streaming).
static void sendBmiSnapshot() {
    uint32_t nowSec = millis() / 1000;
    char buf[80];
    snprintf(buf, sizeof(buf), "BMI,%lu,%lu,%.3f,%.1f,%d",
             (unsigned long)++gBmiSeq, (unsigned long)nowSec,
             gLastPeakAcc, gLastPeakGyro, gLastActive ? 1 : 0);
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
static bool initBMI160() {  // runs single-threaded in setup() — no mutex needed
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
// Runtime IMU read — guarded by the I2C mutex (BMI160 + MAX30102 share the bus).
static bool readImuSample(ImuSample &s) {
    uint8_t d[6];
    xSemaphoreTake(gI2cMutex, portMAX_DELAY);
    bool ok = readRegs(REG_ACC_DATA, d, 6);
    if (ok) {
        s.ax = toInt16(d[0], d[1]) / ACC_LSB_PER_G;
        s.ay = toInt16(d[2], d[3]) / ACC_LSB_PER_G;
        s.az = toInt16(d[4], d[5]) / ACC_LSB_PER_G;
        ok = readRegs(REG_GYR_DATA, d, 6);
    }
    xSemaphoreGive(gI2cMutex);
    if (!ok) return false;
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
static void resetWindow() {   // call while holding gImuMutex
    gWindowHead = 0;
    gWindowCount = 0;
    gSamplesSinceInference = 0;
}
static void snapshotWindow(ImuSample *dst) {
    int start = (gWindowCount < kWindowSize) ? 0 : gWindowHead;
    for (int i = 0; i < kWindowSize; i++)
        dst[i] = gImuWindow[(start + i) % kWindowSize];
}

// =====================================================================
// TFLITE MICRO  (unchanged)
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
        LOGLN("[MODEL] schema mismatch"); return false;
    }
    static tflite::MicroErrorReporter microErr;
    errorReporter = &microErr;
    static tflite::AllOpsResolver resolver;
    static tflite::MicroInterpreter si(model, resolver, tensorArena, kTensorArenaSize, errorReporter);
    interpreter = &si;
    if (interpreter->AllocateTensors() != kTfLiteOk) {
        LOGLN("[MODEL] AllocateTensors failed"); return false;
    }
    inputTensor  = interpreter->input(0);
    outputTensor = interpreter->output(0);
    outputElementCount = 1;
    for (int i = 0; i < outputTensor->dims->size; i++)
        outputElementCount *= outputTensor->dims->data[i];
    LOGF("[MODEL] ready (arena=%dKB out=%d)\n", kTensorArenaSize/1024, outputElementCount);
    return true;
}

// Returns true on success; fallProb=0 when any gate rejects. (Logic unchanged.)
static bool runInferenceOnSnapshot(const ImuSample *snap,
                                   float    &fallProb,
                                   int      &activityCount,
                                   bool     &highImpactSeen,
                                   bool     &activityActiveOut,
                                   bool     &candidateActiveOut,
                                   bool     &aiWindowActive,
                                   uint32_t &aiWindowStartMs)
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

    gLastPeakAcc  = maxAcc;
    gLastPeakGyro = maxGyr;
    gLastActive   = activityActive;

    static int idleCount = 0;

    if (activityActive) {
        idleCount = 0;
        if (activityCount < ACTIVITY_WINDOW_COUNT) activityCount++;
        if (maxAcc > HIGH_IMPACT_ACC_MIN && maxGyr > HIGH_IMPACT_GYRO_MIN)
            highImpactSeen = true;
    } else {
        idleCount++;
        if (idleCount >= 3) {
            activityCount   = 0;
            highImpactSeen  = false;
        }
    }

    BMI_LOGF("[GATE] acc=%.2fg gyro=%.1fdps  cand=%s  activity=%d/%d  highImpact=%s\n",
             maxAcc, maxGyr, candidateActive ? "yes" : "no",
             activityCount, ACTIVITY_WINDOW_COUNT, highImpactSeen ? "YES" : "no");

    if (!candidateActive || activityCount < ACTIVITY_WINDOW_COUNT) return true;

    if (!highImpactSeen) {
        BMI_LOGF("[GATE] highImpact=no — need 1 window with acc>%.0fg AND gyro>%.0fdps\n",
                 HIGH_IMPACT_ACC_MIN, HIGH_IMPACT_GYRO_MIN);
        return true;
    }

    if (maxGyr < FALL_IMPACT_GYRO_MIN) {
        BMI_LOGF("[IMPACT] peak_gyro=%.1fdps < %.1fdps — reject\n", maxGyr, FALL_IMPACT_GYRO_MIN);
        return true;
    }

    if (!aiWindowActive) {
        aiWindowActive  = true;
        aiWindowStartMs = millis();
        BMI_LOGLN("[AI] Window opened — AI active");
    }
    uint32_t aiElapsed = millis() - aiWindowStartMs;
    if (aiElapsed >= AI_WINDOW_DURATION_MS) {
        aiWindowActive = false;
        highImpactSeen = false;
        BMI_LOGF("[AI] Window expired (%lums) — no fall, waiting for next peak\n",
                 (unsigned long)aiElapsed);
        return true;
    }
    BMI_LOGF("[AI] Window active %lums / %lums\n",
             (unsigned long)aiElapsed, (unsigned long)AI_WINDOW_DURATION_MS);

    for (int t = 0; t < kWindowSize; t++) {
        inputTensor->data.int8[t * kFeatureCount + 0] = quantizeInput(snap[t].ax);
        inputTensor->data.int8[t * kFeatureCount + 1] = quantizeInput(snap[t].ay);
        inputTensor->data.int8[t * kFeatureCount + 2] = quantizeInput(snap[t].az);
        inputTensor->data.int8[t * kFeatureCount + 3] = quantizeInput(snap[t].gx);
        inputTensor->data.int8[t * kFeatureCount + 4] = quantizeInput(snap[t].gy);
        inputTensor->data.int8[t * kFeatureCount + 5] = quantizeInput(snap[t].gz);
    }
    if (interpreter->Invoke() != kTfLiteOk) {
        LOGLN("[MODEL] invoke failed"); return false;
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
    BMI_LOGF("[STILL] mean_acc=%.2fg mean_gyro=%.1fdps -> %s\n", mA, mG,
             (mA >= STILLNESS_ACC_MIN && mA <= STILLNESS_ACC_MAX && mG <= STILLNESS_GYRO_MAX)
             ? "STILL" : "moving");
    return (mA >= STILLNESS_ACC_MIN && mA <= STILLNESS_ACC_MAX && mG <= STILLNESS_GYRO_MAX);
}

// =====================================================================
// FALL DETECT STATE MACHINE  (logic unchanged; only LED/mode helpers swapped)
// =====================================================================
static int             fallWatchLeft       = 0;
static uint32_t        monitorStartMs      = 0;
static uint32_t        stillnessStartMs    = 0;
static bool            stillnessTimerArmed = false;
static float           gLastFallProb       = 0.0f;

static void onFallConfirmed(float fallProb) {
    gFallAlertActive = true;
    setSystemMode(MODE_ALERT);
    setLedState(LED_ALARM);

    char buf[80];
    uint32_t tsSec = millis() / 1000;
    snprintf(buf, sizeof(buf), "ALERT,%lu,%lu,fall,1,%.3f,%.3f",
             (unsigned long)++gAlertSeq, (unsigned long)tsSec,
             fallProb, 1.0f - fallProb);
    notifyAlert(buf);
}

static void updateFallStateMachine(float fallProb, bool stillnessNow, bool activityActive,
                                   float peakAcc, float peakGyr) {
    bool isFall       = (fallProb >= FALL_DECISION_THRESHOLD);
    bool cancelActive = (peakAcc > CANCEL_ACC_THRESHOLD || peakGyr > CANCEL_GYRO_THRESHOLD);

    switch (fallDetectState) {
        case FDS_IDLE:
            if (isFall && stillnessNow) {
                gLastFallProb   = fallProb;
                fallDetectState = FDS_FALL_WATCH;
                fallWatchLeft   = FALL_WATCH_WINDOWS - 1;
                setSystemMode(MODE_FALL_WATCH);
                setLedState(LED_FALL_WATCH);
                BMI_LOGF("[FSM] IDLE -> FALL_WATCH (left=%d)\n", fallWatchLeft);
            }
            break;

        case FDS_FALL_WATCH:
            if (cancelActive) {
                fallDetectState = FDS_IDLE;
                returnToMonitoring();
                BMI_LOGF("[FSM] FALL_WATCH: strong activity (%.2fg/%.1fdps) -> IDLE\n",
                         peakAcc, peakGyr);
                break;
            }
            if (fallWatchLeft > 0) {
                fallWatchLeft--;
                BMI_LOGF("[FSM] FALL_WATCH left=%d\n", fallWatchLeft);
            } else {
                fallDetectState     = FDS_STILL_TIMING;
                monitorStartMs      = millis();
                stillnessTimerArmed = false;
                BMI_LOGLN("[FSM] FALL_WATCH -> STILL_TIMING (monitor timeout=10s)");
            }
            break;

        case FDS_STILL_TIMING: {
            uint32_t monitorElapsed = millis() - monitorStartMs;
            bool isMoving = (cancelActive || !stillnessNow);

            if (monitorElapsed >= FALL_MONITOR_TIMEOUT_MS) {
                fallDetectState     = FDS_IDLE;
                stillnessTimerArmed = false;
                returnToMonitoring();
                BMI_LOGF("[FSM] STILL_TIMING: timeout %lums -> IDLE (safe)\n",
                         (unsigned long)monitorElapsed);
                break;
            }

            if (isMoving) {
                if (stillnessTimerArmed) {
                    stillnessTimerArmed = false;
                    BMI_LOGF("[FSM] STILL_TIMING: %s -> substance reset (monitor=%lums/%lums)\n",
                             activityActive ? "activity" : "motion",
                             (unsigned long)monitorElapsed, (unsigned long)FALL_MONITOR_TIMEOUT_MS);
                }
            } else {
                if (!stillnessTimerArmed) {
                    stillnessTimerArmed = true;
                    stillnessStartMs    = millis();
                    BMI_LOGF("[FSM] STILL_TIMING: nam im -> arm substance (monitor=%lums left)\n",
                             (unsigned long)(FALL_MONITOR_TIMEOUT_MS - monitorElapsed));
                }
                uint32_t stillElapsed = millis() - stillnessStartMs;
                BMI_LOGF("[FSM] STILL_TIMING: still=%lums/%lums  monitor=%lums/%lums\n",
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
// TASK: MOTION MONITOR — Core 0.  Lightweight 10 Hz idle motion poll.
// Only samples while MODE_IDLE_MONITOR; on motion it resets the high-rate
// buffer and wakes the HighRate task. It NEVER runs TinyCNN itself.
// =====================================================================
static void taskMotionMonitor(void *pv) {
    (void)pv;
    TickType_t xLastWake = xTaskGetTickCount();
    for (;;) {
        vTaskDelayUntil(&xLastWake, pdMS_TO_TICKS(MOTION_MONITOR_PERIOD_MS));
        if (gSystemMode != MODE_IDLE_MONITOR) continue;  // high-rate owns the bus
        if (!bmiOk) continue;

        ImuSample s;
        if (!readImuSample(s)) continue;

        float accMag  = sqrtf(s.ax*s.ax + s.ay*s.ay + s.az*s.az);
        float gyroMag = sqrtf(s.gx*s.gx + s.gy*s.gy + s.gz*s.gz);
        bool motion = (fabsf(accMag - 1.0f) > MOTION_WAKE_ACC_DEV_G) ||
                      (gyroMag > MOTION_WAKE_GYRO_DPS);
        if (motion) {
            xSemaphoreTake(gImuMutex, portMAX_DELAY);
            resetWindow();
            xSemaphoreGive(gImuMutex);
            gLastActive = true;                 // seed so HighRate doesn't idle out early
            setSystemMode(MODE_MOTION_CAPTURE);
            if (gHighRateTask) xTaskNotifyGive(gHighRateTask);
            BMI_LOGF("[MOTION] wake (acc=%.2fg gyro=%.1fdps)\n", accMag, gyroMag);
        }
    }
}

// =====================================================================
// TASK: HIGH-RATE IMU — Core 0.  Blocked until motion. Runs 50 Hz capture,
// fills exactly 100-sample / 2 s windows and notifies the AI task. Keeps
// capturing while motion / fall-watch / alert persists; returns to idle
// after MAX_QUIET_WINDOWS quiet windows.
// =====================================================================
static void taskHighRateImu(void *pv) {
    (void)pv;
    for (;;) {
        // Sleep with zero overhead until the motion monitor wakes us.
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        gHighRateRunning = true;

        int quietWindows = 0;
        TickType_t xLastWake = xTaskGetTickCount();
        for (;;) {
            vTaskDelayUntil(&xLastWake, pdMS_TO_TICKS(SAMPLE_PERIOD_MS));   // precise 50 Hz
            if (!bmiOk) continue;

            ImuSample s;
            if (!readImuSample(s)) { LOGLN("[IMU] read failed"); continue; }

            xSemaphoreTake(gImuMutex, portMAX_DELAY);
            pushSample(s);
            bool windowReady = (gWindowCount >= kWindowSize) &&
                               (gSamplesSinceInference >= kInferenceStride);
            if (windowReady) gSamplesSinceInference = 0;
            xSemaphoreGive(gImuMutex);

            if (!windowReady) continue;

            // A full 100-sample window is ready → hand it to the AI task.
            if (gInferenceTask) xTaskNotifyGive(gInferenceTask);

            // Decide whether to keep the high-rate path alive. Bias toward
            // staying awake (safety): only idle after sustained quiet.
            bool busy   = gFallAlertActive || (fallDetectState != FDS_IDLE);
            bool active = gLastActive;
            if (busy || active) quietWindows = 0;
            else                quietWindows++;

            if (!busy && !active && quietWindows > MAX_QUIET_WINDOWS) {
                gHighRateRunning = false;
                setSystemMode(MODE_IDLE_MONITOR);
                setLedState(LED_IDLE);
                break;   // back to blocking → MotionMonitor resumes
            }
        }
    }
}

// =====================================================================
// TASK: AI INFERENCE — Core 1.  Blocked until a 100-sample window is ready.
// Runs the existing gate logic + TinyCNN + fall FSM. (Unchanged behaviour.)
// =====================================================================
static void taskInference(void *pv) {
    (void)pv;
    static uint32_t inferenceCount  = 0;
    static int      activityCount   = 0;
    static bool     highImpactSeen  = false;
    static bool     aiWindowActive  = false;
    static uint32_t aiWindowStartMs = 0;

    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);   // event-driven; never spins

        xSemaphoreTake(gImuMutex, portMAX_DELAY);
        snapshotWindow(gSnapshot);
        xSemaphoreGive(gImuMutex);

        if (gFallAlertActive) { aiWindowActive = false; continue; }

        uint32_t t0 = millis();
        float fallProb        = 0.0f;
        bool  activityActive  = false;
        bool  candidateActive = false;
        bool ok = runInferenceOnSnapshot(gSnapshot, fallProb, activityCount,
                                         highImpactSeen, activityActive, candidateActive,
                                         aiWindowActive, aiWindowStartMs);
        uint32_t latencyMs = millis() - t0;
        inferenceCount++;

        if (!ok) { LOGLN("[AI] inference error"); continue; }

        bool isFall = (fallProb >= FALL_DECISION_THRESHOLD);
        BMI_LOGF("[INFER] #%lu  fall_prob=%.3f  latency=%lums  -> %s\n",
                 inferenceCount, fallProb, latencyMs, isFall ? "FALL?" : "non-fall");

        bool stillnessNow = checkStillness(gSnapshot);
        updateFallStateMachine(fallProb, stillnessNow, activityActive,
                               gLastPeakAcc, gLastPeakGyro);   // may trigger ALERT

        if (fallDetectState != FDS_IDLE) aiWindowActive = false;
    }
}

// =====================================================================
// TASK: BLE TX — single point that calls notify(). Drains the BLE queue.
// =====================================================================
static void taskBle(void *pv) {
    (void)pv;
    BleMsg m;
    for (;;) {
        if (xQueueReceive(gBleQueue, &m, portMAX_DELAY) != pdTRUE) continue;
        if (!gBleReady) continue;
        NimBLECharacteristic *c = (m.target == 0) ? gCharAlert : gCharVitals;
        if (!c) continue;
        c->setValue((uint8_t*)m.data, strlen(m.data));
        c->notify();
        if (m.target == 0) LOGF("[BLE] ALERT notify: %s\n", m.data);
    }
}

// =====================================================================
// BUTTON — GPIO interrupt + debounced handler task.
// SAFE during alert; manual SOS trigger otherwise. (Behaviour preserved.)
// =====================================================================
static void IRAM_ATTR buttonIsr() {
    BaseType_t hpw = pdFALSE;
    if (gButtonTask) vTaskNotifyGiveFromISR(gButtonTask, &hpw);
    portYIELD_FROM_ISR(hpw);
}

static void handleButtonPress() {
    char buf[64];
    uint32_t tsSec = millis() / 1000;
    if (gFallAlertActive) {
        // Alarm active → "I'm Safe": stop buzzer, send SAFE.
        gFallAlertActive = false;
        fallDetectState  = FDS_IDLE;
        setSystemMode(MODE_COOLDOWN);
        returnToMonitoring();
        snprintf(buf, sizeof(buf), "SAFE,%lu,%lu",
                 (unsigned long)++gAlertSeq, (unsigned long)tsSec);
        notifyAlert(buf);
        LOGF("[BTN] Safe confirmed — sent: %s\n", buf);
    } else {
        // Manual fall trigger (SOS / test).
        fallDetectState  = FDS_IDLE;
        gFallAlertActive = true;
        setSystemMode(MODE_ALERT);
        setLedState(LED_ALARM);
        snprintf(buf, sizeof(buf), "ALERT,%lu,%lu,fall,1,1.000,0.000",
                 (unsigned long)++gAlertSeq, (unsigned long)tsSec);
        notifyAlert(buf);
        LOGF("[BTN] Manual fall triggered — sent: %s\n", buf);
    }
}

static void taskButton(void *pv) {
    (void)pv;
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);   // woken by ISR
        vTaskDelay(pdMS_TO_TICKS(DEBOUNCE_MS));    // debounce settle
        if (digitalRead(PIN_BUTTON) != LOW) continue;   // bounce / noise
        handleButtonPress();
        // Wait for release so a single press fires exactly once.
        while (digitalRead(PIN_BUTTON) == LOW) vTaskDelay(pdMS_TO_TICKS(10));
    }
}

// =====================================================================
// SOFTWARE TIMER: VITALS BATCH — every VITALS_PERIOD_MS, only while a phone
// is connected + ready (no streaming during idle/disconnected). In live mode
// it also pushes a BMI peak snapshot.
// =====================================================================
static void vitalsTimerCb(TimerHandle_t t) {
    (void)t;
    if (!gBleReady) return;          // nothing to do when no app is listening
    sendVitalsBatch();
    if (gLiveMode) sendBmiSnapshot();

#if (DEBUG_LOG && ENABLE_MAX_DEBUG)
    long ir = maxGetIR();
    LOGF("[MAX] IR = %ld -> %s\n", ir, (ir >= 50000) ? "Finger" : "No finger");
#endif
}

// =====================================================================
// ARDUINO ENTRY
// =====================================================================
void setup() {
    Serial.begin(115200);
    delay(300);
    LOGLN("");
    LOGLN("=======================================================");
    LOGLN("ESP32-S3  AIFD  S3_AIFD_V2(Pin) — Adaptive RTOS");
    LOGLN("  Idle: 10Hz motion poll, LED off, no BLE stream");
    LOGLN("  Motion: 50Hz capture -> V84 TinyCNN -> fall FSM");
    LOGLN("=======================================================");

    // GPIO
    pinMode(PIN_LED_VCC, OUTPUT);
    digitalWrite(PIN_LED_VCC, HIGH);
    pinMode(PIN_BUTTON,  INPUT_PULLUP);
    pinMode(PIN_BUZZER,  OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
    tone(PIN_BUZZER, BUZZER_FREQ_HZ); noTone(PIN_BUZZER); // init LEDC at real freq

    gLedNeo.begin();
    gLedNeo.setBrightness(50);
    gLedNeo.show();

    // Mutexes (created before any runtime I2C / buffer access)
    gImuMutex = xSemaphoreCreateMutex();
    gI2cMutex = xSemaphoreCreateMutex();
    configASSERT(gImuMutex && gI2cMutex);

    gBleQueue = xQueueCreate(8, sizeof(BleMsg));
    configASSERT(gBleQueue);

    // LED task first so setLedState() renders immediately.
    xTaskCreatePinnedToCore(taskLed, "LED", 2048, nullptr, 1, &gLedTask, 0);
    setLedState(LED_BOOT);

    // I2C
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
    Wire.setClock(100000);
    Wire.setTimeOut(20);
    delay(50);

    // BMI160
    bmiOk = initBMI160();
    LOGF("[BMI]   %s (addr=0x%02X)\n", bmiOk ? "OK" : "NOT FOUND", bmi160Addr);

    // MAX30102
    if (particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        particleSensor.setup();
        maxOk = true;
        LOGLN("[MAX]   OK");
    } else {
        LOGLN("[MAX]   NOT FOUND");
        maxOk = false;
    }

    // TFLite model
    modelOk = initModel();
    if (!modelOk) LOGLN("[MODEL] init failed — fall detection disabled");

    // ── Tasks (created ONCE; coordinate via notifications/queues/mode) ──
    xTaskCreatePinnedToCore(taskMotionMonitor, "MOTION",   4096, nullptr, 2, &gMotionTask,    0);
    xTaskCreatePinnedToCore(taskHighRateImu,   "IMU_HI",   4096, nullptr,
                            configMAX_PRIORITIES - 1, &gHighRateTask, 0);
    xTaskCreatePinnedToCore(taskInference,     "AI_INFER", 8192, nullptr, 1, &gInferenceTask, 1);
    xTaskCreatePinnedToCore(taskButton,        "BUTTON",   2048, nullptr, 3, &gButtonTask,    1);
    xTaskCreatePinnedToCore(taskBle,           "BLE_TX",   4096, nullptr, 2, &gBleTask,       1);

    // Button GPIO interrupt (press = FALLING, INPUT_PULLUP)
    attachInterrupt(digitalPinToInterrupt(PIN_BUTTON), buttonIsr, FALLING);

    // Vitals software timer (event-driven; gated on connection inside callback)
    TimerHandle_t vitalsTimer = xTimerCreate("VITALS", pdMS_TO_TICKS(VITALS_PERIOD_MS),
                                             pdTRUE, nullptr, vitalsTimerCb);
    if (vitalsTimer) xTimerStart(vitalsTimer, 0);

    // BLE setup — service registered before advertising (Android UUID filter req.)
    NimBLEDevice::init("S3_AIFD_V1");   // keep advertised name (app filter compat)
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);
    NimBLEDevice::deleteAllBonds();     // clean state after reflash (no bonding)

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

    setStr(gCharAlert,  "ALERT,0,0,idle,0,0.000,1.000");
    setStr(gCharVitals, "BATCH,0,255|255|255|255|255,255|255|255|255|255,0|0|0|0|0");
    setStr(cCtrl,       "WAITING_READY");

    gBleService->start();
    NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
    adv->addServiceUUID(AIFD_SVC_UUID);
    adv->setScanResponse(true);
    adv->start();

    if (!bmiOk || !modelOk) {
        setLedState(LED_WARNING);          // permanent — sensor error needs reboot
    } else {
        setSystemMode(MODE_IDLE_MONITOR);
        setLedState(LED_IDLE);             // idle = LED off, low power
    }
    LOGLN("[BOOT] Adaptive RTOS started. Advertising as \"S3_AIFD_V1\"");
}

// loop() is intentionally empty — all work is event-driven across tasks,
// the BLE queue, software timers and GPIO interrupts.
void loop() {
    vTaskDelay(portMAX_DELAY);
}
