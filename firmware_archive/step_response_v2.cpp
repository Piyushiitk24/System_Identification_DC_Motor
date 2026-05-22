// =============================================================================
// step_response_v2.cpp
// Phase 2 gap-fill step-response firmware for DC motor system identification
//
// Identical to step_response_v1.cpp except for the trials[] array.
// 46 trials total (~7.3 min hands-off sequence):
//   - 8 piggyback  (Phase 2.1 conditions re-run; bounds session-to-session drift)
//   - 20 new accel (PWM 180, 220 x fwd/rev x 5 runs)
//   - 18 new decel (240->{100,180,220} x fwd/rev x 3 runs)
//
// Hardware: Arduino Uno R4 Minima + L298N + 12V geared DC motor
// Pins:     ENC_A=D2, ENC_B=D3, IN1=D4, IN2=D5, ENA=D9 (PWM @ 20 kHz)
// Encoder:  600 PPR quadrature, 4x decoded -> 2400 counts/rev
//
// Usage:
//   1. Flash this firmware
//   2. Run scripts/capture_serial.py <port> <log_path>
//   3. capture_serial.py sends GO automatically after 3 s
//   4. Sequence runs hands-off for ~7.3 min
//   5. Run scripts/split_log.py <log_path> data/raw/step_responses_gapfill/
//
// Output format per trial:
//   === START <trial_name> ===
//   t_ms,pwm_cmd,dir,enc_count,rpm
//   <data rows at 10 ms intervals>
//   === END ===
// =============================================================================

#include <Arduino.h>
#include "pwm.h"

// ----- Pin definitions -----
constexpr int PIN_ENC_A = 2;
constexpr int PIN_ENC_B = 3;
constexpr int PIN_IN1   = 4;
constexpr int PIN_IN2   = 5;
constexpr int PIN_ENA   = 9;

// ----- Encoder -----
constexpr int8_t ENCODER_SIGN   = -1;
constexpr float  COUNTS_PER_REV = 2400.0f;

volatile int32_t enc_count = 0;
volatile uint8_t enc_state = 0;

const int8_t ENC_LOOKUP[16] = {
     0, -1,  1,  0,
     1,  0,  0, -1,
    -1,  0,  0,  1,
     0,  1, -1,  0
};

void encISR() {
    uint8_t new_state = (digitalRead(PIN_ENC_A) << 1) | digitalRead(PIN_ENC_B);
    int8_t  delta     = ENC_LOOKUP[(enc_state << 2) | new_state];
    enc_count += ENCODER_SIGN * delta;
    enc_state  = new_state;
}

// ----- PWM -----
PwmOut motorPwm(PIN_ENA);

void setPwmDuty(int pwm_0_255) {
    if (pwm_0_255 < 0)   pwm_0_255 = 0;
    if (pwm_0_255 > 255) pwm_0_255 = 255;
    motorPwm.pulse_perc((float)pwm_0_255 * 100.0f / 255.0f);
}

void setDirection(int dir) {
    if (dir > 0) {
        digitalWrite(PIN_IN1, HIGH);
        digitalWrite(PIN_IN2, LOW);
    } else if (dir < 0) {
        digitalWrite(PIN_IN1, LOW);
        digitalWrite(PIN_IN2, HIGH);
    } else {
        digitalWrite(PIN_IN1, LOW);
        digitalWrite(PIN_IN2, LOW);
    }
}

void stopMotor() {
    setPwmDuty(0);
    setDirection(0);
}

// ----- Trial definition -----
struct Trial {
    const char* name;
    int      start_pwm;
    int      target_pwm;
    int      direction;     // +1 fwd, -1 rev
    uint32_t pre_step_ms;
    uint32_t post_step_ms;
};

// 46-trial gap-fill sequence
const Trial trials[] = {
    // ----- Block 1: Piggyback (8 trials, ~68 s) -----
    // Phase 2.1 conditions re-run; comparison goes against original Phase 2.1 CSVs
    {"step_up_fwd_200_run01", 0, 200, +1,  500, 5000},
    {"step_up_fwd_200_run02", 0, 200, +1,  500, 5000},
    {"step_up_fwd_240_run01", 0, 240, +1,  500, 5000},
    {"step_up_fwd_240_run02", 0, 240, +1,  500, 5000},
    {"step_up_rev_200_run01", 0, 200, -1,  500, 5000},
    {"step_up_rev_200_run02", 0, 200, -1,  500, 5000},
    {"step_up_rev_240_run01", 0, 240, -1,  500, 5000},
    {"step_up_rev_240_run02", 0, 240, -1,  500, 5000},

    // ----- Block 2: New accel (20 trials, ~170 s) -----
    // PWM 180 fwd
    {"step_up_fwd_180_run01", 0, 180, +1,  500, 5000},
    {"step_up_fwd_180_run02", 0, 180, +1,  500, 5000},
    {"step_up_fwd_180_run03", 0, 180, +1,  500, 5000},
    {"step_up_fwd_180_run04", 0, 180, +1,  500, 5000},
    {"step_up_fwd_180_run05", 0, 180, +1,  500, 5000},
    // PWM 220 fwd
    {"step_up_fwd_220_run01", 0, 220, +1,  500, 5000},
    {"step_up_fwd_220_run02", 0, 220, +1,  500, 5000},
    {"step_up_fwd_220_run03", 0, 220, +1,  500, 5000},
    {"step_up_fwd_220_run04", 0, 220, +1,  500, 5000},
    {"step_up_fwd_220_run05", 0, 220, +1,  500, 5000},
    // PWM 180 rev
    {"step_up_rev_180_run01", 0, 180, -1,  500, 5000},
    {"step_up_rev_180_run02", 0, 180, -1,  500, 5000},
    {"step_up_rev_180_run03", 0, 180, -1,  500, 5000},
    {"step_up_rev_180_run04", 0, 180, -1,  500, 5000},
    {"step_up_rev_180_run05", 0, 180, -1,  500, 5000},
    // PWM 220 rev
    {"step_up_rev_220_run01", 0, 220, -1,  500, 5000},
    {"step_up_rev_220_run02", 0, 220, -1,  500, 5000},
    {"step_up_rev_220_run03", 0, 220, -1,  500, 5000},
    {"step_up_rev_220_run04", 0, 220, -1,  500, 5000},
    {"step_up_rev_220_run05", 0, 220, -1,  500, 5000},

    // ----- Block 3: New decel (18 trials, ~198 s) -----
    // 240 -> 100 fwd
    {"step_down_fwd_240to100_run01", 240, 100, +1, 3000, 5000},
    {"step_down_fwd_240to100_run02", 240, 100, +1, 3000, 5000},
    {"step_down_fwd_240to100_run03", 240, 100, +1, 3000, 5000},
    // 240 -> 180 fwd
    {"step_down_fwd_240to180_run01", 240, 180, +1, 3000, 5000},
    {"step_down_fwd_240to180_run02", 240, 180, +1, 3000, 5000},
    {"step_down_fwd_240to180_run03", 240, 180, +1, 3000, 5000},
    // 240 -> 220 fwd
    {"step_down_fwd_240to220_run01", 240, 220, +1, 3000, 5000},
    {"step_down_fwd_240to220_run02", 240, 220, +1, 3000, 5000},
    {"step_down_fwd_240to220_run03", 240, 220, +1, 3000, 5000},
    // 240 -> 100 rev
    {"step_down_rev_240to100_run01", 240, 100, -1, 3000, 5000},
    {"step_down_rev_240to100_run02", 240, 100, -1, 3000, 5000},
    {"step_down_rev_240to100_run03", 240, 100, -1, 3000, 5000},
    // 240 -> 180 rev
    {"step_down_rev_240to180_run01", 240, 180, -1, 3000, 5000},
    {"step_down_rev_240to180_run02", 240, 180, -1, 3000, 5000},
    {"step_down_rev_240to180_run03", 240, 180, -1, 3000, 5000},
    // 240 -> 220 rev
    {"step_down_rev_240to220_run01", 240, 220, -1, 3000, 5000},
    {"step_down_rev_240to220_run02", 240, 220, -1, 3000, 5000},
    {"step_down_rev_240to220_run03", 240, 220, -1, 3000, 5000},
};
const int NUM_TRIALS = sizeof(trials) / sizeof(trials[0]);

// ----- Trial runner -----
constexpr uint32_t LOG_INTERVAL_US     = 10000;  // 10 ms telemetry
constexpr uint32_t INTER_TRIAL_REST_MS = 3000;
constexpr uint32_t READY_PRINT_MS      = 3000;

void printReadyBanner() {
    Serial.println(F("# step_response_v2 ready"));
    Serial.print  (F("# Total trials: "));
    Serial.println(NUM_TRIALS);
    Serial.println(F("# Send 'GO' to start the full sequence"));
    Serial.println(F("# Send 'STOP' between trials to halt"));
}

void runTrial(const Trial& t) {
    // Inter-trial rest
    stopMotor();
    delay(INTER_TRIAL_REST_MS);

    // Header
    Serial.print(F("=== START "));
    Serial.print(t.name);
    Serial.println(F(" ==="));
    Serial.println(F("t_ms,pwm_cmd,dir,enc_count,rpm"));

    // Reset encoder
    noInterrupts();
    enc_count = 0;
    interrupts();
    int32_t prev_count = 0;

    // Apply start condition
    int current_pwm = t.start_pwm;
    int current_dir = t.direction;
    setDirection(current_pwm > 0 ? current_dir : 0);
    setPwmDuty(current_pwm);

    // Timing
    uint32_t trial_start_us = micros();
    uint32_t prev_us        = trial_start_us;
    uint32_t step_time_us   = trial_start_us + t.pre_step_ms * 1000UL;
    uint32_t end_time_us    = step_time_us   + t.post_step_ms * 1000UL;
    uint32_t next_log_us    = trial_start_us;

    bool stepped = false;

    while ((int32_t)(micros() - end_time_us) < 0) {
        uint32_t now_us = micros();

        // Apply the step
        if (!stepped && (int32_t)(now_us - step_time_us) >= 0) {
            current_pwm = t.target_pwm;
            setDirection(current_pwm > 0 ? current_dir : 0);
            setPwmDuty(current_pwm);
            stepped = true;
        }

        // Log at 10 ms intervals
        if ((int32_t)(now_us - next_log_us) >= 0) {
            int32_t cnt;
            noInterrupts();
            cnt = enc_count;
            interrupts();

            int32_t  delta_cnt = cnt - prev_count;
            uint32_t delta_us  = now_us - prev_us;
            float    rpm       = 0.0f;
            if (delta_us > 0) {
                rpm = ((float)delta_cnt * 60.0e6f) / (COUNTS_PER_REV * (float)delta_us);
            }

            uint32_t t_ms = (now_us - trial_start_us) / 1000;
            char dir_char = (current_pwm == 0) ? 'N' : (current_dir > 0 ? 'F' : 'R');

            Serial.print(t_ms);
            Serial.print(',');
            Serial.print(current_pwm);
            Serial.print(',');
            Serial.print(dir_char);
            Serial.print(',');
            Serial.print(cnt);
            Serial.print(',');
            Serial.println(rpm, 2);

            prev_count   = cnt;
            prev_us      = now_us;
            next_log_us += LOG_INTERVAL_US;
        }
    }

    stopMotor();
    Serial.println(F("=== END ==="));
    Serial.flush();
}

// ----- Setup / loop -----
void setup() {
    pinMode(PIN_ENC_A, INPUT_PULLUP);
    pinMode(PIN_ENC_B, INPUT_PULLUP);
    pinMode(PIN_IN1,   OUTPUT);
    pinMode(PIN_IN2,   OUTPUT);

    enc_state = (digitalRead(PIN_ENC_A) << 1) | digitalRead(PIN_ENC_B);

    attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), encISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_B), encISR, CHANGE);

    Serial.begin(230400);
    while (!Serial && millis() < 3000) {}

    motorPwm.begin(20000.0f, 0.0f);
    motorPwm.pulse_perc(0.0f);
    stopMotor();
    delay(2000);

    printReadyBanner();
}

void loop() {
    static uint32_t last_ready_print_ms = 0;

    if (millis() - last_ready_print_ms >= READY_PRINT_MS) {
        printReadyBanner();
        last_ready_print_ms = millis();
    }

    if (Serial.available() > 0) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd == "GO") {
            Serial.println(F("# === SEQUENCE START ==="));
            for (int i = 0; i < NUM_TRIALS; i++) {
                Serial.print(F("# Trial "));
                Serial.print(i + 1);
                Serial.print(F(" of "));
                Serial.print(NUM_TRIALS);
                Serial.print(F(": "));
                Serial.println(trials[i].name);
                runTrial(trials[i]);
            }
            stopMotor();
            Serial.println(F("# === SEQUENCE COMPLETE ==="));
        } else if (cmd == "STOP") {
            stopMotor();
            Serial.println(F("# Motor stopped"));
        } else if (cmd == "?") {
            printReadyBanner();
        } else if (cmd.length() > 0) {
            Serial.print(F("# Unknown command: "));
            Serial.println(cmd);
        }
    }
}
