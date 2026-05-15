#include <Arduino.h>

// =====================================================
// PIN CONFIG
// =====================================================
static const int PIN_LED_GREEN  = 4;
static const int PIN_LED_YELLOW = 5;
static const int PIN_LED_RED    = 6;
static const int PIN_BUZZER     = 7;
static const int PIN_BUTTON     = 10;

// =====================================================
// BUZZER CONFIG
// 2300 Hz = tần số cộng hưởng của Loa Buzzer 5V (theo datasheet).
// Dùng tone() cho passive buzzer; với active buzzer có thể đổi
// sang digitalWrite(PIN_BUZZER, HIGH/LOW) — xem document.
// =====================================================
static const unsigned int BUZZER_FREQ_HZ = 2300;

// =====================================================
// TIMING
// =====================================================
static const unsigned long DEBOUNCE_MS       = 30;
static const unsigned long BLINK_INTERVAL_MS = 300;

// =====================================================
// STATE MACHINE
// =====================================================
enum State : uint8_t {
    STATE_ALL_ON = 0,    // 3 đèn sáng
    STATE_GREEN,         // chỉ đèn xanh
    STATE_YELLOW,        // chỉ đèn vàng
    STATE_RED,           // chỉ đèn đỏ
    STATE_BLINK_BUZZ,    // 3 đèn nhấp nháy + loa kêu
    STATE_COUNT
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
// HELPERS
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
            setLeds(true, true, true);
            buzzerOff();
            break;
        case STATE_GREEN:
            setLeds(true, false, false);
            buzzerOff();
            break;
        case STATE_YELLOW:
            setLeds(false, true, false);
            buzzerOff();
            break;
        case STATE_RED:
            setLeds(false, false, true);
            buzzerOff();
            break;
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
        // INPUT_PULLUP → nhấn = LOW (cạnh xuống)
        if (btnStable == LOW) {
            currentState = (State)((currentState + 1) % STATE_COUNT);
            applyState();
        }
    }
}

// =====================================================
// ARDUINO ENTRY
// =====================================================
void setup() {
    pinMode(PIN_LED_GREEN,  OUTPUT);
    pinMode(PIN_LED_YELLOW, OUTPUT);
    pinMode(PIN_LED_RED,    OUTPUT);
    pinMode(PIN_BUZZER,     OUTPUT);
    pinMode(PIN_BUTTON,     INPUT_PULLUP);

    applyState();
}

void loop() {
    handleButton();
    handleBlink();
}
