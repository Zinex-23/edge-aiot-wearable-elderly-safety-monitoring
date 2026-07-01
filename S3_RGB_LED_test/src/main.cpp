/**
 * S3_RGB_LED_test — src/main.cpp
 *
 * WS2812 RGB LED module test on ESP32-S3.
 *
 * Pin mapping:
 *   GPIO 4 — VCC  (module powered from GPIO; keep brightness ≤ 30 to stay within 12 mA limit)
 *   GPIO 5 — DI   (data in — NeoPixel signal)
 *   GPIO 6 — DO   (data out — not used for single LED)
 *
 * Sequence (loops):  GREEN → YELLOW → RED, 2 s each
 */

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

#define PIN_VCC      4
#define PIN_DI       5
#define NUM_LEDS     1
#define BRIGHTNESS   30          // ~12% — stays within GPIO 12 mA drive limit
#define INTERVAL_MS  2000

Adafruit_NeoPixel led(NUM_LEDS, PIN_DI, NEO_GRB + NEO_KHZ800);

struct ColorEntry {
    uint8_t     r, g, b;
    const char *name;
};

static const ColorEntry STATES[] = {
    { 0,   255,   0, "GREEN"  },
    { 255, 255,   0, "YELLOW" },
    { 255,   0,   0, "RED"    },
};
static const int NUM_STATES = sizeof(STATES) / sizeof(STATES[0]);

static void showColor(int idx) {
    led.setPixelColor(0, led.Color(STATES[idx].r, STATES[idx].g, STATES[idx].b));
    led.show();
    Serial.printf("[LED] -> %s\n", STATES[idx].name);
}

void setup() {
    Serial.begin(115200);
    delay(300);
    Serial.println("=== S3_RGB_LED_test ===");

    pinMode(PIN_VCC, OUTPUT);
    digitalWrite(PIN_VCC, HIGH);
    delay(10);

    led.begin();
    led.setBrightness(BRIGHTNESS);
    showColor(0);
}

void loop() {
    static int      stateIdx = 0;
    static uint32_t lastMs   = 0;

    if (lastMs == 0) lastMs = millis();

    if ((uint32_t)(millis() - lastMs) >= INTERVAL_MS) {
        stateIdx = (stateIdx + 1) % NUM_STATES;
        showColor(stateIdx);
        lastMs = millis();
    }
}
