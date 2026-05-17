/**
 * S3_BLE — ESP32-S3 Fall Detection Firmware
 *
 * Architecture: FreeRTOS dual-task
 *   taskSampling  (Core 0, priority MAX-1): reads BMI160 at EXACTLY 50Hz via
 *                 vTaskDelayUntil — never blocked by inference, zero sample loss.
 *   taskInference (Core 1, priority 1):    waits for full 100-sample window signal,
 *                 snapshots the ring buffer (brief mutex), then runs TFLite Micro
 *                 inference on the snapshot — inference duration does not affect sampling.
 *
 * This guarantees the model always receives 100 properly-spaced samples (2s @ 50Hz).
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

static const unsigned int  BUZZER_FREQ_HZ   = 2300;
static const unsigned long DEBOUNCE_MS      = 30;
static const unsigned long BLINK_INTERVAL_MS= 300;
static const unsigned long SERIAL_BAUD      = 115200;

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
static const uint32_t SAMPLE_PERIOD_MS    = 20;    // 50 Hz
static const int      kWindowSize         = 100;   // 2s @ 50Hz
static const int      kFeatureCount       = 6;
static const int      kInferenceStride    = 100;   // trigger every 100 new samples
static const int      kTensorArenaSize    = 60 * 1024;

static const float FALL_DECISION_THRESHOLD = 0.42f;
static const float CANDIDATE_ACC_THRESHOLD = 7.5f;
static const float CANDIDATE_GYRO_THRESHOLD= 240.0f;
static const float FALL_IMPACT_GYRO_MIN    = 20.0f;
static const int   STILLNESS_SAMPLES       = 25;
static const float STILLNESS_ACC_MIN       = 0.6f;
static const float STILLNESS_ACC_MAX       = 1.7f;
static const float STILLNESS_GYRO_MAX      = 100.0f;

// =====================================================================
// STATE MACHINE (LED + Buzzer)
// =====================================================================
enum State : uint8_t {
    STATE_ALL_ON = 0,
    STATE_GREEN,
    STATE_YELLOW,
    STATE_RED,
    STATE_BLINK_BUZZ,
    STATE_COUNT
};
static const char *STATE_NAMES[STATE_COUNT] = {
    "ALL_ON", "GREEN", "YELLOW", "RED", "BLINK_BUZZ"
};
static State         currentState  = STATE_ALL_ON;
static int           btnLastReading= HIGH;
static int           btnStable     = HIGH;
static unsigned long btnLastChange = 0;
static bool          blinkLevel    = true;
static unsigned long blinkLastMs   = 0;

// =====================================================================
// IMU RING BUFFER — shared between taskSampling and taskInference
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

// =====================================================================
// FREERTOS SYNC PRIMITIVES
// =====================================================================
static SemaphoreHandle_t gImuMutex      = nullptr; // protects ring buffer
static TaskHandle_t      gInferenceTask = nullptr; // notified by sampling task

// Snapshot: inference task copies window here BEFORE releasing mutex,
// then runs slow inference on this copy — sampling task never waits.
static ImuSample gSnapshot[kWindowSize];

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
// LED / BUZZER HELPERS
// =====================================================================
static void setLeds(bool g, bool y, bool r) {
    digitalWrite(PIN_LED_GREEN,  g ? HIGH : LOW);
    digitalWrite(PIN_LED_YELLOW, y ? HIGH : LOW);
    digitalWrite(PIN_LED_RED,    r ? HIGH : LOW);
}
static void buzzerOn()  { tone(PIN_BUZZER, BUZZER_FREQ_HZ); }
static void buzzerOff() { noTone(PIN_BUZZER); digitalWrite(PIN_BUZZER, LOW); }

static void applyState() {
    switch (currentState) {
        case STATE_ALL_ON:    setLeds(true,  true,  true);  buzzerOff(); break;
        case STATE_GREEN:     setLeds(true,  false, false); buzzerOff(); break;
        case STATE_YELLOW:    setLeds(false, true,  false); buzzerOff(); break;
        case STATE_RED:       setLeds(false, false, true);  buzzerOff(); break;
        case STATE_BLINK_BUZZ:
            blinkLevel = true; blinkLastMs = millis();
            setLeds(true, true, true); buzzerOn(); break;
        default: break;
    }
}

static void goToState(State next, const char *reason) {
    if (next == currentState) return;
    Serial.printf("[STATE] %s -> %s (%s)\n", STATE_NAMES[currentState], STATE_NAMES[next], reason);
    currentState = next;
    applyState();
}

static void handleBlink() {
    if (currentState != STATE_BLINK_BUZZ) return;
    unsigned long now = millis();
    if (now - blinkLastMs >= BLINK_INTERVAL_MS) {
        blinkLastMs = now;
        blinkLevel  = !blinkLevel;
        setLeds(blinkLevel, blinkLevel, blinkLevel);
    }
}

static void handleButton() {
    int reading       = digitalRead(PIN_BUTTON);
    unsigned long now = millis();
    if (reading != btnLastReading) { btnLastChange = now; btnLastReading = reading; }
    if ((now - btnLastChange) >= DEBOUNCE_MS && reading != btnStable) {
        btnStable = reading;
        if (btnStable == LOW)
            goToState((State)((currentState + 1) % STATE_COUNT), "button");
    }
}

// =====================================================================
// BMI160 I2C ACCESS
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
static int oldestIndex() {
    return (gWindowCount < kWindowSize) ? 0 : gWindowHead;
}
// Copy ordered window into dst[0..kWindowSize-1] (call while holding mutex)
static void snapshotWindow(ImuSample *dst) {
    int start = oldestIndex();
    for (int i = 0; i < kWindowSize; i++)
        dst[i] = gImuWindow[(start + i) % kWindowSize];
}

// =====================================================================
// TFLITE MICRO — inference on a snapshot (no ring buffer access)
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
    if (inputTensor->type != kTfLiteInt8 || outputTensor->type != kTfLiteInt8) {
        Serial.println("[MODEL] tensor type != int8"); return false;
    }
    if (inputTensor->dims->data[1] != kWindowSize || inputTensor->dims->data[2] != kFeatureCount) {
        Serial.println("[MODEL] unexpected input shape"); return false;
    }
    outputElementCount = 1;
    for (int i = 0; i < outputTensor->dims->size; i++)
        outputElementCount *= outputTensor->dims->data[i];
    Serial.printf("[MODEL] ready (arena=%dKB out=%d)\n", kTensorArenaSize/1024, outputElementCount);
    return true;
}

// Run inference on a pre-copied snapshot — safe to call without any mutex held.
static bool runInferenceOnSnapshot(const ImuSample *snap, float &fallProb) {
    fallProb = 0.0f;
    if (!modelOk) return false;

    // Candidate gate: skip inference if no significant motion
    float maxAcc = 0, maxGyr = 0;
    for (int i = 0; i < kWindowSize; i++) {
        float a = sqrtf(snap[i].ax*snap[i].ax + snap[i].ay*snap[i].ay + snap[i].az*snap[i].az);
        float g = sqrtf(snap[i].gx*snap[i].gx + snap[i].gy*snap[i].gy + snap[i].gz*snap[i].gz);
        if (a > maxAcc) maxAcc = a;
        if (g > maxGyr) maxGyr = g;
    }
    if (maxAcc <= CANDIDATE_ACC_THRESHOLD && maxGyr <= CANDIDATE_GYRO_THRESHOLD) {
        Serial.printf("[SKIP] acc=%.2fg gyro=%.1fdps — below candidate threshold\n", maxAcc, maxGyr);
        return true;  // fallProb stays 0.0
    }

    // Fill input tensor from snapshot
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

// Post-fall stillness check on snapshot
static bool checkStillness(const ImuSample *snap) {
    float accSum = 0, gyrSum = 0;
    int   start  = kWindowSize - STILLNESS_SAMPLES;
    for (int i = start; i < kWindowSize; i++) {
        accSum += sqrtf(snap[i].ax*snap[i].ax + snap[i].ay*snap[i].ay + snap[i].az*snap[i].az);
        gyrSum += sqrtf(snap[i].gx*snap[i].gx + snap[i].gy*snap[i].gy + snap[i].gz*snap[i].gz);
    }
    float mA = accSum / STILLNESS_SAMPLES;
    float mG = gyrSum / STILLNESS_SAMPLES;
    return (mA >= STILLNESS_ACC_MIN && mA <= STILLNESS_ACC_MAX && mG <= STILLNESS_GYRO_MAX);
}

// =====================================================================
// TASK 1: IMU SAMPLING — Core 0, priority MAX-1
// Uses vTaskDelayUntil for EXACT 20ms period regardless of inference time.
// Ring buffer is protected by gImuMutex (held for < 0.1ms per sample).
// =====================================================================
static void taskSampling(void *pvParams) {
    TickType_t xLastWake = xTaskGetTickCount();

    while (true) {
        // Precise 50Hz timing — wakes up exactly every 20ms
        vTaskDelayUntil(&xLastWake, pdMS_TO_TICKS(SAMPLE_PERIOD_MS));

        if (!bmiOk) continue;

        ImuSample s;
        if (!readImuSample(s)) {
            Serial.println("[IMU] read failed");
            continue;
        }

        // Critical section: push to ring buffer (held < 0.1ms)
        xSemaphoreTake(gImuMutex, portMAX_DELAY);
        pushSample(s);
        bool windowReady = (gWindowCount >= kWindowSize)
                        && (gSamplesSinceInference >= kInferenceStride);
        if (windowReady) gSamplesSinceInference = 0; // reset before releasing
        xSemaphoreGive(gImuMutex);

        // Signal inference task — non-blocking for this task
        if (windowReady && gInferenceTask != nullptr)
            xTaskNotifyGive(gInferenceTask);
    }
}

// =====================================================================
// TASK 2: INFERENCE — Core 1, priority 1 (low)
// Waits for notification, snapshots window (brief mutex), then runs
// slow inference on the copy — sampling task NEVER waits for this.
// =====================================================================
static void taskInference(void *pvParams) {
    static uint32_t inferenceCount = 0;

    while (true) {
        // Block until sampling task signals a full window
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        // Snapshot window quickly (mutex held for < 1ms)
        xSemaphoreTake(gImuMutex, portMAX_DELAY);
        snapshotWindow(gSnapshot);
        xSemaphoreGive(gImuMutex);
        // From this point, sampling continues unblocked on Core 0

        uint32_t t0 = millis();
        float fallProb = 0.0f;
        bool ok = runInferenceOnSnapshot(gSnapshot, fallProb);
        uint32_t latencyMs = millis() - t0;
        inferenceCount++;

        if (!ok) { Serial.println("[AI] inference error"); continue; }

        bool isFall = (fallProb >= FALL_DECISION_THRESHOLD);
        Serial.printf("[INFER] #%lu  fall_prob=%.3f  latency=%lums  -> %s\n",
                      inferenceCount, fallProb, latencyMs, isFall ? "FALL!" : "non-fall");

        if (isFall && checkStillness(gSnapshot)) {
            // Fall confirmed: sustained stillness after impact
            goToState(STATE_BLINK_BUZZ, "fall confirmed");
        }
    }
}

// =====================================================================
// ARDUINO ENTRY
// =====================================================================
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(300);
    Serial.println();
    Serial.println("=======================================================");
    Serial.println("ESP32-S3  AIFD Fall Detection  [FreeRTOS dual-task]");
    Serial.println("  Core 0: IMU sampling @ 50Hz (vTaskDelayUntil)");
    Serial.println("  Core 1: TFLite inference (snapshot, non-blocking)");
    Serial.println("=======================================================");

    // GPIO
    pinMode(PIN_LED_GREEN,  OUTPUT);
    pinMode(PIN_LED_YELLOW, OUTPUT);
    pinMode(PIN_LED_RED,    OUTPUT);
    pinMode(PIN_BUTTON,     INPUT_PULLUP);
    pinMode(PIN_BUZZER,     OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
    tone(PIN_BUZZER, 1); noTone(PIN_BUZZER); // init LEDC channel

    // I2C
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
    Wire.setClock(100000);
    Wire.setTimeOut(20);
    delay(50);

    // Sensors
    bmiOk = initBMI160();
    Serial.printf("[BMI]   %s (addr=0x%02X)\n", bmiOk ? "OK" : "NOT FOUND", bmi160Addr);

    // Model
    modelOk = initModel();
    if (!modelOk) Serial.println("[MODEL] init failed — fall detection disabled");

    // FreeRTOS
    gImuMutex = xSemaphoreCreateMutex();
    configASSERT(gImuMutex);

    // Task 1: Sampling — Core 0, highest priority
    xTaskCreatePinnedToCore(
        taskSampling, "IMU_SAMPLE",
        4096, nullptr,
        configMAX_PRIORITIES - 1,
        nullptr, 0);

    // Task 2: Inference — Core 1, low priority
    xTaskCreatePinnedToCore(
        taskInference, "AI_INFER",
        8192, nullptr,
        1,
        &gInferenceTask, 1);

    applyState();
    Serial.println("[BOOT] Tasks started. Monitoring for falls...");
}

void loop() {
    // loop() runs on Core 1 at idle priority.
    // All time-critical work is in the FreeRTOS tasks above.
    handleButton();
    handleBlink();
    delay(10);
}
