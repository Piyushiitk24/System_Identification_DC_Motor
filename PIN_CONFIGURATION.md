# DC Motor System Identification — Pin Configuration

## Hardware

- Arduino Uno R3
- L298N motor driver
- 12 V geared DC motor
- 2-phase 600 PPR quadrature encoder
- External 12 V motor supply / bench PSU

---

## Arduino Uno Pin Map

| Arduino Pin | Connected To | Purpose |
|---|---|---|
| `D2` | Encoder channel `A` | Quadrature interrupt input `INT0` |
| `D3` | Encoder channel `B` | Quadrature interrupt input `INT1` |
| `D4` | L298N `IN1` | Motor direction input 1 |
| `D5` | L298N `IN2` | Motor direction input 2 |
| `D9` | L298N `ENA` | PWM speed command |
| `5V` | Encoder `VCC` and L298N logic `5V` | Logic supply |
| `GND` | Encoder `GND`, L298N `GND`, 12 V supply negative | Common ground reference |

---

## L298N Connections

| L298N Pin / Terminal | Connection |
|---|---|
| `12V` / `VS` | External 12 V supply positive |
| `GND` | Common ground rail |
| `5V` | Arduino `5V` logic supply |
| `ENA` | Arduino `D9` |
| `IN1` | Arduino `D4` |
| `IN2` | Arduino `D5` |
| `OUT1` | Motor terminal 1 |
| `OUT2` | Motor terminal 2 |

Do not use `OUT3`, `OUT4`, `IN3`, `IN4`, or `ENB` for this single-motor test.

---

## L298N Jumper State

| Jumper | Required State | Reason |
|---|---|---|
| `ENA` jumper | **Removed** | Allows Arduino `D9` to control PWM speed |
| `5V-EN` / regulator jumper | **Removed** when Arduino 5V feeds L298N `5V` | Prevents back-feeding the onboard regulator |

---

## Encoder Connections

| Encoder Wire / Pin | Connection |
|---|---|
| `VCC` | Arduino `5V` rail |
| `GND` | Common ground rail |
| `A` | Arduino `D2` |
| `B` | Arduino `D3` |

---

## Encoder Pull-up Resistors

Use two `4.7 kΩ` resistors.

```text
Encoder A line -----> Arduino D2
              |
              +----[4.7 kΩ]----> 5V rail

Encoder B line -----> Arduino D3
              |
              +----[4.7 kΩ]----> 5V rail
```

The pull-up resistor is placed between the signal line and `5V`, not in series with the signal line.

---

## Common Ground Rail

All grounds must meet at one common reference point.

```text
Arduino GND --------+
Encoder GND --------+
L298N GND ----------+---- Common GND rail / star node
12 V supply negative+
```

The motor current path should be kept short and direct. Do not route high motor current through thin breadboard rails if avoidable.

---

## Motor Direction Convention Used in Test Sketch

| Command | IN1 | IN2 | ENA PWM | Meaning |
|---|---|---|---|---|
| Positive PWM | HIGH | LOW | `abs(pwm)` | Forward command |
| Negative PWM | LOW | HIGH | `abs(pwm)` | Reverse command |
| Zero PWM | LOW | LOW | `0` | Coast / stop |

If the physical direction is opposite of your preferred convention, either swap motor leads at `OUT1`/`OUT2` or invert the sign convention in code.

If encoder count decreases during your chosen forward motion, either swap encoder `A`/`B` or set `ENCODER_SIGN = -1` in the test sketch.

---

## First Test Order

1. Keep 12 V motor supply OFF.
2. Connect Arduino USB.
3. Upload the test sketch.
4. Open Serial Monitor at `230400` baud.
5. Rotate motor shaft by hand and check encoder count.
6. Turn ON 12 V motor supply.
7. Send `f` for low forward PWM.
8. Send `s` to stop.
9. Send `r` for low reverse PWM.
10. Confirm motor direction and encoder sign.

---

## Serial Commands in Test Sketch

| Serial Key | Action |
|---|---|
| `s` | Stop / coast |
| `f` | Forward low PWM |
| `F` | Forward higher PWM |
| `r` | Reverse low PWM |
| `R` | Reverse higher PWM |
| `+` | Increase command by 10 PWM |
| `-` | Decrease command by 10 PWM |
| `a` | Automatic forward-stop-reverse-stop test |
| `z` | Zero encoder count |
| `?` | Print help menu |

