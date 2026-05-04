/*
  DC Motor system identification manual-mode firmware

  Target: Arduino Uno R4 Minima
  Driver: L298N
  Encoder: 600 PPR quadrature encoder on motor output shaft

  Serial monitor: 230400 baud

  Commands:
    f       : set forward direction
    r       : set reverse direction
    s       : stop / coast
    z       : zero encoder count
    ?       : print help
    0..255  : set PWM magnitude

  Telemetry:
    t_ms,pwm_cmd,dir,enc_count,rpm
*/

#include <Arduino.h>
#include "pwm.h"

// ---------------- Pin configuration ----------------
constexpr uint8_t PIN_ENC_A = 2;
constexpr uint8_t PIN_ENC_B = 3;
constexpr uint8_t PIN_IN1 = 4;
constexpr uint8_t PIN_IN2 = 5;
constexpr uint8_t PIN_ENA = 9;

// ---------------- Encoder configuration ----------------
// 600 PPR quadrature encoder with 4x decoding: 600 * 4 = 2400 counts/rev.
constexpr float COUNTS_PER_REV = 2400.0f;

// If forward command produces negative RPM, set this to -1.
constexpr int8_t ENCODER_SIGN = 1;

volatile long encoderCount = 0;
volatile uint8_t prevAB = 0;

constexpr int8_t QUAD_TABLE[16] = {
    0, -1, 1, 0,
    1, 0, 0, -1,
    -1, 0, 0, 1,
    0, 1, -1, 0};

// ---------------- Manual command state ----------------
int pwmMagnitude = 0; // 0..255, always the typed PWM magnitude
int direction = 0;    // +1 forward, -1 reverse, 0 stopped
PwmOut motorPwm(PIN_ENA);
bool pwmReady = false;

// ---------------- Telemetry timing ----------------
constexpr uint32_t PRINT_PERIOD_MS = 100;
uint32_t lastPrintMs = 0;
long lastPrintCount = 0;

String inputBuffer;

void updateEncoder() {
  uint8_t a = digitalRead(PIN_ENC_A) ? 1 : 0;
  uint8_t b = digitalRead(PIN_ENC_B) ? 1 : 0;
  uint8_t ab = (a << 1) | b;
  uint8_t idx = (prevAB << 2) | ab;

  encoderCount += ENCODER_SIGN * QUAD_TABLE[idx];
  prevAB = ab;
}

long getEncoderCountAtomic() {
  noInterrupts();
  long count = encoderCount;
  interrupts();
  return count;
}

void zeroEncoderCount() {
  noInterrupts();
  encoderCount = 0;
  interrupts();
  lastPrintCount = 0;
}

void applyMotor() {
  pwmMagnitude = constrain(pwmMagnitude, 0, 255);
  int activePwm = pwmMagnitude;
  if (direction == 0) activePwm = 0;
  float dutyPercent = (static_cast<float>(activePwm) * 100.0f) / 255.0f;

  if (pwmReady) {
    motorPwm.pulse_perc(dutyPercent);
  }

  if (direction > 0 && pwmMagnitude > 0) {
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, LOW);
  } else if (direction < 0 && pwmMagnitude > 0) {
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, HIGH);
  } else {
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);
  }
}

bool parsePwmMagnitude(const String &token, int &valueOut) {
  if (token.length() == 0) return false;

  for (uint16_t i = 0; i < token.length(); ++i) {
    if (!isDigit(token.charAt(i))) return false;
  }

  long value = token.toInt();
  if (value < 0 || value > 255) return false;

  valueOut = static_cast<int>(value);
  return true;
}

void printHelp() {
  Serial.println();
  Serial.println(F("=== DC Motor System Identification Manual Mode ==="));
  Serial.println(F("Target: Arduino Uno R4 Minima"));
  Serial.println(F("Serial baud: 230400"));
  Serial.println(F("PWM frequency: 20000 Hz"));
  Serial.println();
  Serial.println(F("Commands:"));
  Serial.println(F("  f       : set forward direction"));
  Serial.println(F("  r       : set reverse direction"));
  Serial.println(F("  s       : stop / coast"));
  Serial.println(F("  z       : zero encoder count"));
  Serial.println(F("  ?       : print this help"));
  Serial.println(F("  0..255  : set PWM magnitude"));
  Serial.println();
  Serial.println(F("CSV output:"));
  Serial.println(F("  t_ms,pwm_cmd,dir,enc_count,rpm"));
  Serial.println();
}

void handleCommand(String token) {
  token.trim();
  if (token.length() == 0) return;

  if (token == "f") {
    direction = 1;
    applyMotor();
    Serial.println(F("# direction=fwd"));
    return;
  }

  if (token == "r") {
    direction = -1;
    applyMotor();
    Serial.println(F("# direction=rev"));
    return;
  }

  if (token == "s") {
    direction = 0;
    pwmMagnitude = 0;
    applyMotor();
    Serial.println(F("# stop"));
    return;
  }

  if (token == "z") {
    zeroEncoderCount();
    Serial.println(F("# encoder_count_zeroed"));
    return;
  }

  if (token == "?") {
    printHelp();
    return;
  }

  int requestedPwm = 0;
  if (parsePwmMagnitude(token, requestedPwm)) {
    pwmMagnitude = requestedPwm;
    if (direction == 0 && pwmMagnitude > 0) {
      direction = 1;
    }
    applyMotor();
    Serial.print(F("# pwm_cmd="));
    Serial.print(pwmMagnitude);
    Serial.print(F(",dir="));
    Serial.println(direction);
    return;
  }

  Serial.print(F("# unknown_command="));
  Serial.println(token);
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char ch = static_cast<char>(Serial.read());

    if (ch == '\n' || ch == '\r') {
      handleCommand(inputBuffer);
      inputBuffer = "";
    } else if (ch == ' ' || ch == '\t') {
      handleCommand(inputBuffer);
      inputBuffer = "";
    } else {
      inputBuffer += ch;
    }
  }
}

void printTelemetry() {
  uint32_t now = millis();
  if (now - lastPrintMs < PRINT_PERIOD_MS) return;

  uint32_t dtMs = now - lastPrintMs;
  lastPrintMs = now;

  long count = getEncoderCountAtomic();
  long delta = count - lastPrintCount;
  lastPrintCount = count;

  float rpm = 0.0f;
  if (dtMs > 0) {
    rpm = (static_cast<float>(delta) / COUNTS_PER_REV) *
          (60000.0f / static_cast<float>(dtMs));
  }

  Serial.print(now);
  Serial.print(',');
  Serial.print(pwmMagnitude);
  Serial.print(',');
  Serial.print(direction);
  Serial.print(',');
  Serial.print(count);
  Serial.print(',');
  Serial.println(rpm, 2);
}

void setup() {
  pinMode(PIN_ENC_A, INPUT_PULLUP);
  pinMode(PIN_ENC_B, INPUT_PULLUP);
  pinMode(PIN_IN1, OUTPUT);
  pinMode(PIN_IN2, OUTPUT);
  pinMode(PIN_ENA, OUTPUT);
  digitalWrite(PIN_ENA, LOW);

  analogWriteResolution(8);
  pwmReady = motorPwm.begin(20000.0f, 0.0f); // 20 kHz for stable DMM readings.
  applyMotor();

  uint8_t a = digitalRead(PIN_ENC_A) ? 1 : 0;
  uint8_t b = digitalRead(PIN_ENC_B) ? 1 : 0;
  prevAB = (a << 1) | b;

  attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_B), updateEncoder, CHANGE);

  Serial.begin(230400);
  while (!Serial && millis() < 3000) {
  }

  printHelp();
  if (!pwmReady) {
    Serial.println(F("# ERROR: pwm_20khz_init_failed"));
  }
  Serial.println(F("t_ms,pwm_cmd,dir,enc_count,rpm"));

  lastPrintMs = millis();
  lastPrintCount = getEncoderCountAtomic();
}

void loop() {
  readSerialCommands();
  printTelemetry();
}
