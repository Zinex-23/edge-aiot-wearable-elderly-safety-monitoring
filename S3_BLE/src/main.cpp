#include <Arduino.h>
#include <Wire.h>
#include <math.h>

#include "fall_detection_v84.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

// =====================================================
// PIN CONFIG
// =====================================================
static const int PIN_LED_GREEN  = 4;
static const int PIN_LED_YELLOW = 5;
static const int PIN_LED_RED    = 6;
static const int PIN_BUZZER     = 7;
static const int PIN_BUTTON     = 10;
static const int PIN_I2C_SDA    = 8;
static const int PIN_I2C_SCL    = 9;

// =====================================================
// BUZZER CONFIG
// 2300 Hz = tần số cộng hưởng của Loa Buzzer 5V (theo datasheet).
// Đổi sang digitalWrite(PIN_BUZZER, HIGH/LOW) nếu là active buzzer.
// =====================================================
static const unsigned int BUZZER_FREQ_HZ = 2300;

// =====================================================
// TIMING
// =====================================================
static const unsigned long DEBOUNCE_MS       = 30;
static const unsigned long BLINK_INTERVAL_MS = 300;
static const unsigned long SERIAL_BAUD       = 115200;

// =====================================================
// BMI160 REGISTERS
// =====================================================
static const uint8_t BMI160_ADDR_LOW   = 0x68;
static const uint8_t BMI160_ADDR_HIGH  = 0x69;
static const uint8_t BMI160_CHIP_ID    = 0xD1;

static const uint8_t REG_CHIP_ID   = 0x00;
static const uint8_t REG_GYR_DATA  = 0x0C;
static const uint8_t REG_ACC_DATA  = 0x12;
static const uint8_t REG_ACC_CONF  = 0x40;
static const uint8_t REG_ACC_RANGE = 0x41;
static const uint8_t REG_GYR_CONF  = 0x42;
static const uint8_t REG_GYR_RANGE = 0x43;
static const uint8_t REG_CMD       = 0x7E;

static const float ACC_LSB_PER_G   = 16384.0f;  // ±2g range
static const float GYR_LSB_PER_DPS = 16.4f;     // ±2000 dps range

// =====================================================
// SAMPLING + MODEL CONFIG
// =====================================================
static const uint32_t SAMPLE_RATE_HZ   = 50;
static const uint32_t SAMPLE_PERIOD_MS = 1000 / SAMPLE_RATE_HZ;  // 20 ms

static const int kWindowSize       = 100;   // 2s @ 50Hz
static const int kFeatureCount     = 6;
static const int kInferenceStride  = 100;   // inference mỗi 2s
static const int kTensorArenaSize  = 60 * 1024;

static const float FALL_DECISION_THRESHOLD   = 0.42f;  // V84 optimal threshold
static const float CANDIDATE_ACC_THRESHOLD   = 7.5f;   // g
static const float CANDIDATE_GYRO_THRESHOLD  = 240.0f; // dps

// --- Voting: yêu cầu N window liên tiếp đều báo fall ---
// Thực tế: window ngay sau ngã có fall_prob=0 (người đang nằm im → non-fall là đúng)
// nên không thể yêu cầu 2 window liên tiếp. 3 lớp lọc trước đã đủ chặt → 1 là đủ.
static const int   FALL_CONFIRM_COUNT        = 1;

// --- Post-fall stillness check ---
// Sau impact, người ngã thật thường nằm/ngồi im (acc ≈ 1g, gyro ≈ 0)
// Kiểm tra 0.5s cuối của window
static const int   STILLNESS_SAMPLES         = 25;     // 25 mẫu × 20ms = 0.5s
static const float STILLNESS_ACC_MIN         = 0.6f;   // g — có thể nằm nghiêng
static const float STILLNESS_ACC_MAX         = 1.7f;   // g
static const float STILLNESS_GYRO_MAX        = 100.0f; // dps

// --- Impact gyro check ---
// Ngã thật bắt buộc có rotation mạnh ở đâu đó trong 2s window (xoay người khi ngã).
// Đặt tay nhẹ vào chỗ hoặc dừng chuyển động thì gyro thấp suốt → loại false positive.
static const float FALL_IMPACT_GYRO_MIN      = 20.0f;  // dps — peak gyro trong cả window

// --- Pre-activity gate ---
// Cần 3 window LIÊN TIẾP có acc > 2g HOẶC gyro > 50dps mới bật AI
static const float  ACTIVITY_ACC_THRESHOLD   = 2.0f;   // g
static const float  ACTIVITY_GYRO_THRESHOLD  = 50.0f;  // dps
static const int    ACTIVITY_WINDOW_COUNT    = 3;

// =====================================================
// STATE MACHINE
// =====================================================
enum State : uint8_t {
    STATE_ALL_ON = 0,    // 3 đèn sáng
    STATE_GREEN,         // chỉ đèn xanh
    STATE_YELLOW,        // chỉ đèn vàng
    STATE_RED,           // chỉ đèn đỏ
    STATE_BLINK_BUZZ,    // 3 đèn nhấp nháy + loa kêu (alarm)
    STATE_COUNT
};

static const char *STATE_NAMES[STATE_COUNT] = {
    "ALL_ON", "GREEN", "YELLOW", "RED", "BLINK_BUZZ"
};

static State currentState = STATE_ALL_ON;

// Button debounce state
static int           btnLastReading = HIGH;
static int           btnStable      = HIGH;
static unsigned long btnLastChange  = 0;

// Blink state
static bool          blinkLevel  = true;
static unsigned long blinkLastMs = 0;

// =====================================================
// BMI160 + MODEL STATE
// =====================================================
struct ImuSample {
    float ax = 0, ay = 0, az = 0;
    float gx = 0, gy = 0, gz = 0;
    uint32_t tsMs = 0;
};

static uint8_t  bmi160Addr  = BMI160_ADDR_LOW;
static bool     bmiOk       = false;
static uint32_t lastSampleMs = 0;

static ImuSample imuWindow[kWindowSize];
static int windowHead = 0;
static int windowCount = 0;
static int samplesSinceInference = 0;

namespace {
const tflite::Model*       model = nullptr;
tflite::ErrorReporter*     errorReporter = nullptr;
tflite::MicroInterpreter*  interpreter = nullptr;
TfLiteTensor*              inputTensor = nullptr;
TfLiteTensor*              outputTensor = nullptr;
uint8_t                    tensorArena[kTensorArenaSize];
int                        outputElementCount = 0;
bool                       modelOk = false;
}  // namespace

// ── Fall detection state machine ──────────────────────────────────────────
// IDLE          : bình thường, AI gated bởi activityCount
// FALL_WATCH    : AI phát hiện ngã, đang theo dõi xem có nằm im không
//                 Tồn tại tối đa FALL_WATCH_WINDOWS window (sau đó về IDLE nếu không im)
// STILL_TIMING  : đã thấy nằm im, đang đo thời gian
//                 Nếu đủ FALL_STILL_DURATION_MS → ALARM
//                 Nếu cử động → về IDLE
enum FallDetectState : uint8_t { FDS_IDLE, FDS_FALL_WATCH, FDS_STILL_TIMING };

static FallDetectState fallDetectState    = FDS_IDLE;
static int             fallWatchLeft      = 0;      // số window còn lại trong FALL_WATCH
static uint32_t        stillnessStartMs   = 0;      // thời điểm bắt đầu nằm im

static const int      FALL_WATCH_WINDOWS     = 5;    // 5 window = 10s theo dõi sau ngã
static const uint32_t FALL_STILL_DURATION_MS = 5000; // 5s nằm im liên tục → ALARM

static int      activityCount         = 0;       // lịch sử hoạt động gần đây [0, ACTIVITY_WINDOW_COUNT]

// =====================================================
// LED / BUZZER HELPERS
// =====================================================
static void setLeds(bool g, bool y, bool r) {
    digitalWrite(PIN_LED_GREEN,  g ? HIGH : LOW);
    digitalWrite(PIN_LED_YELLOW, y ? HIGH : LOW);
    digitalWrite(PIN_LED_RED,    r ? HIGH : LOW);
}

static void buzzerOn()  { tone(PIN_BUZZER, BUZZER_FREQ_HZ); }
static void buzzerOff() { noTone(PIN_BUZZER); digitalWrite(PIN_BUZZER, LOW); }

static void applyState() {
    switch (currentState) {
        case STATE_ALL_ON:
            setLeds(true, true, true);   buzzerOff(); break;
        case STATE_GREEN:
            setLeds(true, false, false); buzzerOff(); break;
        case STATE_YELLOW:
            setLeds(false, true, false); buzzerOff(); break;
        case STATE_RED:
            setLeds(false, false, true); buzzerOff(); break;
        case STATE_BLINK_BUZZ:
            blinkLevel  = true;
            blinkLastMs = millis();
            setLeds(true, true, true);
            buzzerOn();
            break;
        default:
            break;
    }
}

static void goToState(State next, const char *reason) {
    if (next == currentState) return;
    Serial.printf("[STATE] %s -> %s (%s)\n",
                  STATE_NAMES[currentState], STATE_NAMES[next], reason);
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

    if (reading != btnLastReading) {
        btnLastChange  = now;
        btnLastReading = reading;
    }

    if ((now - btnLastChange) >= DEBOUNCE_MS && reading != btnStable) {
        btnStable = reading;
        if (btnStable == LOW) {
            State next = (State)((currentState + 1) % STATE_COUNT);
            goToState(next, "button");
        }
    }
}

// =====================================================
// BMI160 I2C ACCESS
// =====================================================
static int16_t toInt16(uint8_t lsb, uint8_t msb) {
    return (int16_t)((msb << 8) | lsb);
}

static bool writeReg(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(bmi160Addr);
    Wire.write(reg);
    Wire.write(value);
    return Wire.endTransmission() == 0;
}

static bool readRegs(uint8_t reg, uint8_t *buf, size_t len) {
    Wire.beginTransmission(bmi160Addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;

    size_t got = Wire.requestFrom((int)bmi160Addr, (int)len, (int)true);
    if (got != len) return false;
    for (size_t i = 0; i < len; ++i) buf[i] = Wire.read();
    return true;
}

static bool readReg(uint8_t reg, uint8_t &value) {
    return readRegs(reg, &value, 1);
}

static bool probeAddress(uint8_t addr) {
    Wire.beginTransmission(addr);
    return Wire.endTransmission() == 0;
}

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

    // Normal mode for accel + gyro
    if (!writeReg(REG_CMD, 0x11)) return false;
    delay(10);
    if (!writeReg(REG_CMD, 0x15)) return false;
    delay(80);

    // 0x28 = ODR 100Hz, normal averaging
    if (!writeReg(REG_ACC_CONF,  0x28)) return false;
    if (!writeReg(REG_ACC_RANGE, 0x03)) return false;   // ±2g
    if (!writeReg(REG_GYR_CONF,  0x28)) return false;
    if (!writeReg(REG_GYR_RANGE, 0x00)) return false;   // ±2000 dps

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

// =====================================================
// WINDOW (ring buffer 100 mẫu = 2s @50Hz)
// =====================================================
static void resetWindow() {
    windowHead = 0;
    windowCount = 0;
    samplesSinceInference = 0;
}

static void pushSample(const ImuSample &s) {
    imuWindow[windowHead] = s;
    windowHead = (windowHead + 1) % kWindowSize;
    if (windowCount < kWindowSize) windowCount++;
    samplesSinceInference++;
}

static int oldestIndex() {
    return (windowCount < kWindowSize) ? 0 : windowHead;
}

static const ImuSample &orderedSampleAt(int idx) {
    int start = oldestIndex();
    return imuWindow[(start + idx) % kWindowSize];
}

static bool windowIsCandidate() {
    float maxAcc = 0, maxGyr = 0;
    for (int i = 0; i < kWindowSize; ++i) {
        const ImuSample &s = orderedSampleAt(i);
        float a = sqrtf(s.ax*s.ax + s.ay*s.ay + s.az*s.az);
        float g = sqrtf(s.gx*s.gx + s.gy*s.gy + s.gz*s.gz);
        if (a > maxAcc) maxAcc = a;
        if (g > maxGyr) maxGyr = g;
    }
    bool pass = (maxAcc > CANDIDATE_ACC_THRESHOLD) || (maxGyr > CANDIDATE_GYRO_THRESHOLD);
    Serial.printf("[PEAK]  acc=%.2fg gyro=%.1fdps -> %s\n",
                  maxAcc, maxGyr, pass ? "candidate" : "skip");
    return pass;
}

// Cập nhật lịch sử hoạt động sau mỗi window.
// Điều kiện "active": gyro > 50dps (xoay người — đặc trưng chuyển động thực sự).
// Điều kiện "high impact": acc > 10g VÀ gyro > 400dps trong cùng 1 window.
// AI chỉ chạy khi cả 2 điều kiện đều thoả: 3 window gyro liên tiếp + ít nhất 1 high impact.
static void updateActivityCount() {
    float maxAcc = 0, maxGyr = 0;
    for (int i = 0; i < kWindowSize; ++i) {
        const ImuSample &s = orderedSampleAt(i);
        float a = sqrtf(s.ax*s.ax + s.ay*s.ay + s.az*s.az);
        float g = sqrtf(s.gx*s.gx + s.gy*s.gy + s.gz*s.gz);
        if (a > maxAcc) maxAcc = a;
        if (g > maxGyr) maxGyr = g;
    }

    bool active = (maxAcc > ACTIVITY_ACC_THRESHOLD) || (maxGyr > ACTIVITY_GYRO_THRESHOLD);
    if (active) {
        activityCount = min(activityCount + 1, ACTIVITY_WINDOW_COUNT);
    } else {
        activityCount = 0;
    }
    bool aiEnabled = (activityCount >= ACTIVITY_WINDOW_COUNT);
    Serial.printf("[ACT]   acc=%.2fg gyro=%.1fdps -> %s (count=%d/%d) AI=%s\n",
                  maxAcc, maxGyr, active ? "active" : "idle",
                  activityCount, ACTIVITY_WINDOW_COUNT,
                  aiEnabled ? "ON" : "OFF");
}

// =====================================================
// TFLITE MICRO
// =====================================================
static int8_t quantizeInput(float v) {
    float scale = inputTensor->params.scale;
    int   zp    = inputTensor->params.zero_point;
    int   q     = (int)lroundf(v / scale) + zp;
    if (q > 127)  q = 127;
    if (q < -128) q = -128;
    return (int8_t)q;
}

static float dequantizeOutput(int8_t v) {
    return (v - outputTensor->params.zero_point) * outputTensor->params.scale;
}

static int countTensorElements(const TfLiteTensor *t) {
    int c = 1;
    for (int i = 0; i < t->dims->size; ++i) c *= t->dims->data[i];
    return c;
}

static bool initModel() {
    model = tflite::GetModel(fall_detection_model_tflite);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.println("[MODEL] schema mismatch");
        return false;
    }

    static tflite::MicroErrorReporter microErrorReporter;
    errorReporter = &microErrorReporter;
    static tflite::AllOpsResolver resolver;
    static tflite::MicroInterpreter staticInterpreter(
        model, resolver, tensorArena, kTensorArenaSize, errorReporter);
    interpreter = &staticInterpreter;

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        Serial.println("[MODEL] AllocateTensors failed");
        return false;
    }

    inputTensor  = interpreter->input(0);
    outputTensor = interpreter->output(0);

    if (inputTensor->type != kTfLiteInt8 || outputTensor->type != kTfLiteInt8) {
        Serial.println("[MODEL] tensor type != int8");
        return false;
    }
    if (inputTensor->dims->size != 3 ||
        inputTensor->dims->data[0] != 1 ||
        inputTensor->dims->data[1] != kWindowSize ||
        inputTensor->dims->data[2] != kFeatureCount) {
        Serial.println("[MODEL] unexpected input shape");
        return false;
    }

    outputElementCount = countTensorElements(outputTensor);
    Serial.printf("[MODEL] ready (in scale=%.6f zp=%d, out scale=%.6f zp=%d, out=%d)\n",
                  inputTensor->params.scale, inputTensor->params.zero_point,
                  outputTensor->params.scale, outputTensor->params.zero_point,
                  outputElementCount);
    return true;
}

// Kiểm tra peak gyro trong toàn bộ 2s window: ngã thật có rotation mạnh, đặt nhẹ thì không.
static bool checkImpactInWindow() {
    float peakGyro = 0, peakAcc = 0;
    for (int i = 0; i < kWindowSize; ++i) {
        const ImuSample &s = orderedSampleAt(i);
        float a = sqrtf(s.ax*s.ax + s.ay*s.ay + s.az*s.az);
        float g = sqrtf(s.gx*s.gx + s.gy*s.gy + s.gz*s.gz);
        if (a > peakAcc) peakAcc = a;
        if (g > peakGyro) peakGyro = g;
    }
    bool hasImpact = peakGyro >= FALL_IMPACT_GYRO_MIN;
    Serial.printf("[IMPACT] peak_acc=%.2fg peak_gyro=%.1fdps -> %s\n",
                  peakAcc, peakGyro, hasImpact ? "OK" : "reject (no rotation)");
    return hasImpact;
}

// Kiểm tra 0.5s cuối window: người có đang nằm/ngồi im không?
// Ngã thật: impact spike ở đầu/giữa window → nằm im cuối window.
// Chuyển động giả: vung tay / va chạm nhẹ → tiếp tục di chuyển.
static bool checkPostFallStillness() {
    if (windowCount < kWindowSize) return false;

    float accSum = 0, gyrSum = 0;
    int   start  = kWindowSize - STILLNESS_SAMPLES;

    for (int i = start; i < kWindowSize; ++i) {
        const ImuSample &s = orderedSampleAt(i);
        accSum += sqrtf(s.ax*s.ax + s.ay*s.ay + s.az*s.az);
        gyrSum += sqrtf(s.gx*s.gx + s.gy*s.gy + s.gz*s.gz);
    }

    float meanAcc = accSum / STILLNESS_SAMPLES;
    float meanGyr = gyrSum / STILLNESS_SAMPLES;

    bool still = (meanAcc >= STILLNESS_ACC_MIN && meanAcc <= STILLNESS_ACC_MAX)
              && (meanGyr <= STILLNESS_GYRO_MAX);

    Serial.printf("[STILL] mean_acc=%.2fg mean_gyro=%.1fdps -> %s\n",
                  meanAcc, meanGyr, still ? "STILL (pass)" : "moving (reject)");
    return still;
}

static bool runInference(float &fallProb) {
    fallProb = 0.0f;
    if (!modelOk || windowCount < kWindowSize) return false;

    if (!windowIsCandidate()) {
        // chuyển động yếu — bỏ qua inference để tiết kiệm CPU
        return true;
    }

    for (int t = 0; t < kWindowSize; ++t) {
        const ImuSample &s = orderedSampleAt(t);
        inputTensor->data.int8[t * kFeatureCount + 0] = quantizeInput(s.ax);
        inputTensor->data.int8[t * kFeatureCount + 1] = quantizeInput(s.ay);
        inputTensor->data.int8[t * kFeatureCount + 2] = quantizeInput(s.az);
        inputTensor->data.int8[t * kFeatureCount + 3] = quantizeInput(s.gx);
        inputTensor->data.int8[t * kFeatureCount + 4] = quantizeInput(s.gy);
        inputTensor->data.int8[t * kFeatureCount + 5] = quantizeInput(s.gz);
    }

    if (interpreter->Invoke() != kTfLiteOk) {
        Serial.println("[MODEL] invoke failed");
        return false;
    }

    if (outputElementCount == 1) {
        float p = dequantizeOutput(outputTensor->data.int8[0]);
        fallProb = constrain(p, 0.0f, 1.0f);
    } else {
        fallProb = dequantizeOutput(outputTensor->data.int8[1]);
    }
    return true;
}

// =====================================================
// SAMPLING + INFERENCE PIPELINE
// =====================================================
static void runSamplingAndInference() {
    if (!bmiOk) return;

    uint32_t now = millis();
    if ((uint32_t)(now - lastSampleMs) < SAMPLE_PERIOD_MS) return;
    lastSampleMs += SAMPLE_PERIOD_MS;

    ImuSample s;
    if (!readImuSample(s)) {
        Serial.println("[IMU]  read failed");
        return;
    }
    pushSample(s);

    if (windowCount < kWindowSize || samplesSinceInference < kInferenceStride) {
        return;
    }
    samplesSinceInference = 0;

    // Cập nhật lịch sử hoạt động mỗi window (luôn chạy, trước mọi gate khác)
    updateActivityCount();

    // ── FALL_WATCH: đang theo dõi xem có nằm im không sau ngã ──
    // Bypass activity gate — người đang nằm sau ngã thì activityCount = 0.
    if (fallDetectState == FDS_FALL_WATCH) {
        bool isStill = checkPostFallStillness();
        fallWatchLeft--;
        Serial.printf("[WATCH] window %d left, still=%s\n",
                      fallWatchLeft + 1, isStill ? "YES" : "NO");
        if (isStill) {
            fallDetectState  = FDS_STILL_TIMING;
            stillnessStartMs = millis();
            Serial.println("[FALL]  stillness detected → bắt đầu tính thời gian");
        } else if (fallWatchLeft <= 0) {
            Serial.println("[FALL]  watch expired — không nằm im → IDLE");
            fallDetectState = FDS_IDLE;
        }
        return;
    }

    // ── STILL_TIMING: đang đo thời gian nằm im ─────────────────
    // Tiếp tục cho đến khi đủ FALL_STILL_DURATION_MS hoặc cử động.
    if (fallDetectState == FDS_STILL_TIMING) {
        bool isStill  = checkPostFallStillness();
        uint32_t elapsed = millis() - stillnessStartMs;
        if (isStill) {
            Serial.printf("[STILL] nằm im %lus / %lus\n",
                          elapsed / 1000, FALL_STILL_DURATION_MS / 1000);
            if (elapsed >= FALL_STILL_DURATION_MS) {
                fallDetectState = FDS_IDLE;
                if (currentState != STATE_BLINK_BUZZ)
                    goToState(STATE_BLINK_BUZZ, "still >5s → fall confirmed");
            }
        } else {
            Serial.printf("[STILL] cử động sau %lus → IDLE\n", elapsed / 1000);
            fallDetectState = FDS_IDLE;
        }
        return;
    }

    // ── Pre-activity gate (chỉ áp dụng khi FDS_IDLE) ───────────
    if (activityCount < ACTIVITY_WINDOW_COUNT) {
        Serial.printf("[ACT]   gate blocked (count=%d/%d)\n",
                      activityCount, ACTIVITY_WINDOW_COUNT);
        return;
    }

    // ── AI inference ────────────────────────────────────────────
    float fallProb = 0.0f;
    if (!runInference(fallProb)) return;

    bool isFall = fallProb >= FALL_DECISION_THRESHOLD;
    Serial.printf("[INFER] fall_prob=%.3f -> %s\n",
                  fallProb, isFall ? "FALL?" : "non-fall");
    if (!isFall) return;

    // Impact check
    if (!checkImpactInWindow()) return;

    // Fall xác nhận → vào FALL_WATCH, không cần stillness ngay
    Serial.printf("[FALL]  detected! Entering FALL_WATCH (%d windows = %ds)\n",
                  FALL_WATCH_WINDOWS, FALL_WATCH_WINDOWS * 2);
    fallDetectState = FDS_FALL_WATCH;
    fallWatchLeft   = FALL_WATCH_WINDOWS;
}

// =====================================================
// ARDUINO ENTRY
// =====================================================
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(200);
    Serial.println();
    Serial.println("===============================================");
    Serial.println("ESP32-S3  LED + Buzzer + Button + BMI160 + AI");
    Serial.println("===============================================");

    pinMode(PIN_LED_GREEN,  OUTPUT);
    pinMode(PIN_LED_YELLOW, OUTPUT);
    pinMode(PIN_LED_RED,    OUTPUT);
    pinMode(PIN_BUTTON,     INPUT_PULLUP);
    // Buzzer: init LEDC trước khi gọi tone()/noTone()
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
    tone(PIN_BUZZER, 1);   // khởi tạo LEDC channel
    noTone(PIN_BUZZER);

    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
    Wire.setClock(100000);
    Wire.setTimeOut(20);
    delay(50);

    Serial.printf("[I2C]  probe 0x68: %s\n", probeAddress(0x68) ? "OK" : "FAIL");
    Serial.printf("[I2C]  probe 0x69: %s\n", probeAddress(0x69) ? "OK" : "FAIL");

    bmiOk = initBMI160();
    Serial.printf("[BMI]  %s\n", bmiOk ? "ready" : "NOT FOUND");

    modelOk = initModel();
    if (!modelOk) {
        Serial.println("[MODEL] init failed — chỉ chạy state machine, không phát hiện ngã");
    }

    resetWindow();
    lastSampleMs = millis();

    applyState();
    Serial.printf("[STATE] init -> %s\n", STATE_NAMES[currentState]);
    Serial.println("[BOOT] OK. Nhấn nút để chuyển state. Té ngã -> tự bật alarm.");
}

void loop() {
    handleButton();
    handleBlink();
    runSamplingAndInference();
}
