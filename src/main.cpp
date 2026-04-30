/*
  DC Motor + L298N + Quadrature Encoder Setup Test

  Board: Arduino Uno
  Framework: Arduino / PlatformIO

  Pin map:
    D2  <- Encoder A
    D3  <- Encoder B
    D4  -> L298N IN1
    D5  -> L298N IN2
    D9  -> L298N ENA PWM
    5V  -> Encoder VCC and L298N logic 5V
    GND -> Common ground

  Serial monitor: 230400 baud

  Commands:
    s : stop / coast
    f : forward low PWM
    F : forward higher PWM
    r : reverse low PWM
    R : reverse higher PWM
    + : increase PWM command by 10
    - : decrease PWM command by 10
    a : automatic forward-stop-reverse-stop test
    z : zero encoder count
    ? : help
*/

#include <Arduino.h>

// ---------------- Pin configuration ----------------
constexpr uint8_t ENC_A_PIN = 2;   // INT0
constexpr uint8_t ENC_B_PIN = 3;   // INT1
constexpr uint8_t IN1_PIN   = 4;
constexpr uint8_t IN2_PIN   = 5;
constexpr uint8_t ENA_PIN   = 9;   // Timer1 PWM

// ---------------- Encoder configuration ----------------
// 600 PPR quadrature encoder => 600 pulses/channel/rev.
// With 4x decoding: 600 * 4 = 2400 counts/rev.
constexpr float COUNTS_PER_REV = 2400.0f;

// If encoder count decreases during your chosen forward direction,
// change this to -1.
constexpr int8_t ENCODER_SIGN = 1;

volatile long encoderCount = 0;
volatile uint8_t prevAB = 0;

// ---------------- Motor test configuration ----------------
constexpr int PWM_LOW  = 80;   // Use 70-90 if your motor deadzone is high
constexpr int PWM_HIGH = 140;  // Still safe for first test
int currentCmd = 0;            // signed PWM command: -255 ... +255

// ---------------- Auto-test state ----------------
bool autoTestActive = false;
uint8_t autoStage = 0;
unsigned long autoStageStartMs = 0;

// ---------------- Print timing ----------------
unsigned long lastPrintMs = 0;
long lastPrintCount = 0;

// Fast quadrature update. Use direct port access on AVR for speed,
// fall back to digitalRead() on non-AVR architectures (e.g., UNO R4).
void updateEncoder() {
#if defined(ARDUINO_ARCH_AVR)
  uint8_t a = (PIND >> 2) & 0x01;  // D2
  uint8_t b = (PIND >> 3) & 0x01;  // D3
#else
  uint8_t a = digitalRead(ENC_A_PIN) ? 1 : 0;
  uint8_t b = digitalRead(ENC_B_PIN) ? 1 : 0;
#endif
  uint8_t ab = (a << 1) | b;

  uint8_t transition = (prevAB << 2) | ab;

  // Valid quadrature transitions.
  // Depending on your A/B wiring, positive sign may be opposite.
  switch (transition) {
    case 0b0001:
    case 0b0111:
    case 0b1110:
    case 0b1000:
      encoderCount += ENCODER_SIGN;
      break;

    case 0b0010:
    case 0b0100:
    case 0b1101:
    case 0b1011:
      encoderCount -= ENCODER_SIGN;
      break;

    default:
      // 00->00, 01->01, invalid skips, or noise: ignore
      break;
  }

  prevAB = ab;
}

long getEncoderCountAtomic() {
  noInterrupts();
  long c = encoderCount;
  interrupts();
  return c;
}

void zeroEncoderCount() {
  noInterrupts();
  encoderCount = 0;
  interrupts();
  lastPrintCount = 0;
}

void setMotor(int signedPwm) {
  signedPwm = constrain(signedPwm, -255, 255);
  currentCmd = signedPwm;

  if (signedPwm > 0) {
    digitalWrite(IN1_PIN, HIGH);
    digitalWrite(IN2_PIN, LOW);
    analogWrite(ENA_PIN, signedPwm);
  } else if (signedPwm < 0) {
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, HIGH);
    analogWrite(ENA_PIN, -signedPwm);
  } else {
    // Coast mode for zero command.
    analogWrite(ENA_PIN, 0);
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, LOW);
  }
}

void printHelp() {
  Serial.println();
  Serial.println(F("=== DC Motor + L298N + Encoder Setup Test ==="));
  Serial.println(F("Serial baud: 230400"));
  Serial.println(F("Pin map:"));
  Serial.println(F("  D2 <- Encoder A"));
  Serial.println(F("  D3 <- Encoder B"));
  Serial.println(F("  D4 -> L298N IN1"));
  Serial.println(F("  D5 -> L298N IN2"));
  Serial.println(F("  D9 -> L298N ENA PWM"));
  Serial.println();
  Serial.println(F("Commands:"));
  Serial.println(F("  s : stop / coast"));
  Serial.println(F("  f : forward low PWM"));
  Serial.println(F("  F : forward higher PWM"));
  Serial.println(F("  r : reverse low PWM"));
  Serial.println(F("  R : reverse higher PWM"));
  Serial.println(F("  + : increase PWM command by 10"));
  Serial.println(F("  - : decrease PWM command by 10"));
  Serial.println(F("  a : automatic forward-stop-reverse-stop test"));
  Serial.println(F("  z : zero encoder count"));
  Serial.println(F("  ? : print this help"));
  Serial.println();
  Serial.println(F("CSV output:"));
  Serial.println(F("  t_ms,cmd_pwm,enc_count,delta_count,rpm_est"));
  Serial.println();
}

void handleSerial() {
  while (Serial.available() > 0) {
    char ch = static_cast<char>(Serial.read());

    switch (ch) {
      case 's':
        autoTestActive = false;
        setMotor(0);
        Serial.println(F("# STOP / COAST"));
        break;

      case 'f':
        autoTestActive = false;
        setMotor(PWM_LOW);
        Serial.println(F("# FORWARD LOW"));
        break;

      case 'F':
        autoTestActive = false;
        setMotor(PWM_HIGH);
        Serial.println(F("# FORWARD HIGH"));
        break;

      case 'r':
        autoTestActive = false;
        setMotor(-PWM_LOW);
        Serial.println(F("# REVERSE LOW"));
        break;

      case 'R':
        autoTestActive = false;
        setMotor(-PWM_HIGH);
        Serial.println(F("# REVERSE HIGH"));
        break;

      case '+':
        autoTestActive = false;
        setMotor(currentCmd + 10);
        Serial.print(F("# CMD = "));
        Serial.println(currentCmd);
        break;

      case '-':
        autoTestActive = false;
        setMotor(currentCmd - 10);
        Serial.print(F("# CMD = "));
        Serial.println(currentCmd);
        break;

      case 'a':
        autoTestActive = true;
        autoStage = 0;
        autoStageStartMs = millis();
        setMotor(PWM_LOW);
        Serial.println(F("# AUTO TEST START: forward -> stop -> reverse -> stop"));
        break;

      case 'z':
        zeroEncoderCount();
        Serial.println(F("# ENCODER COUNT ZEROED"));
        break;

      case '?':
        printHelp();
        break;

      case '\n':
      case '\r':
      case ' ':
        break;

      default:
        Serial.print(F("# Unknown command: "));
        Serial.println(ch);
        Serial.println(F("# Send ? for help."));
        break;
    }
  }
}

void updateAutoTest() {
  if (!autoTestActive) return;

  unsigned long now = millis();
  unsigned long elapsed = now - autoStageStartMs;

  switch (autoStage) {
    case 0: // forward for 2 s
      if (elapsed >= 2000) {
        setMotor(0);
        autoStage = 1;
        autoStageStartMs = now;
        Serial.println(F("# AUTO: stop"));
      }
      break;

    case 1: // stop for 1 s
      if (elapsed >= 1000) {
        setMotor(-PWM_LOW);
        autoStage = 2;
        autoStageStartMs = now;
        Serial.println(F("# AUTO: reverse"));
      }
      break;

    case 2: // reverse for 2 s
      if (elapsed >= 2000) {
        setMotor(0);
        autoStage = 3;
        autoStageStartMs = now;
        Serial.println(F("# AUTO: final stop"));
      }
      break;

    case 3: // final stop
    default:
      autoTestActive = false;
      setMotor(0);
      Serial.println(F("# AUTO TEST DONE"));
      break;
  }
}

void printStatus() {
  unsigned long now = millis();
  if (now - lastPrintMs < 200) return;

  unsigned long dt = now - lastPrintMs;
  lastPrintMs = now;

  long count = getEncoderCountAtomic();
  long delta = count - lastPrintCount;
  lastPrintCount = count;

  float rpm = 0.0f;
  if (dt > 0) {
    rpm = (static_cast<float>(delta) / COUNTS_PER_REV) * (60000.0f / static_cast<float>(dt));
  }

  Serial.print(now);
  Serial.print(',');
  Serial.print(currentCmd);
  Serial.print(',');
  Serial.print(count);
  Serial.print(',');
  Serial.print(delta);
  Serial.print(',');
  Serial.println(rpm, 2);
}

void setup() {
  pinMode(ENC_A_PIN, INPUT_PULLUP);  // external 4.7k pull-ups are still recommended
  pinMode(ENC_B_PIN, INPUT_PULLUP);

  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  pinMode(ENA_PIN, OUTPUT);

  setMotor(0);

  // On AVR we set Timer1 prescaler to 1 for high-frequency PWM on D9/D10.
  // On non-AVR platforms (e.g., UNO R4) the timer registers are different,
  // so skip this AVR-specific tweak.
#if defined(ARDUINO_ARCH_AVR)
  TCCR1B = (TCCR1B & 0b11111000) | 0x01;
#endif

  uint8_t a = digitalRead(ENC_A_PIN) ? 1 : 0;
  uint8_t b = digitalRead(ENC_B_PIN) ? 1 : 0;
  prevAB = (a << 1) | b;

  attachInterrupt(digitalPinToInterrupt(ENC_A_PIN), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_B_PIN), updateEncoder, CHANGE);

  Serial.begin(230400);
  delay(300);

  printHelp();
  Serial.println(F("t_ms,cmd_pwm,enc_count,delta_count,rpm_est"));

  lastPrintMs = millis();
  lastPrintCount = getEncoderCountAtomic();
}

void loop() {
  handleSerial();
  updateAutoTest();
  printStatus();
}
