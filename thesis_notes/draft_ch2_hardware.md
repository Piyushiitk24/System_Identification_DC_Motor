# Chapter 2 — Hardware Setup and Commissioning

> **Draft status:** first full pass, 2026-05-21. Content draft in Markdown; converts to LaTeX mechanically (tables → `tabular`, ASCII block diagram → a proper vector figure). Numbers trace to status-doc §2, `PIN_CONFIGURATION.md`, the firmware in `firmware_archive/`, and the Phase 0 entries in `thesis_notes/log.md`. This is Chapter 2 (the Introduction is Chapter 1).

## 2.1 Overview

The experimental plant is a brushed DC gearmotor driven by an L298N H-bridge under pulse-width-modulated (PWM) voltage control, with shaft velocity measured by a quadrature optical encoder. An Arduino Uno R4 Minima generates the PWM command, sets the H-bridge direction, decodes the encoder in hardware interrupts, and streams time-stamped telemetry to a host computer over USB serial. All identification data in this thesis were collected on this single rig; only the firmware behaviour changed between sessions (manual jog versus automated step sequencer, Section 2.7).

The signal path is a cascade of four physical stages, and the model identified in later chapters mirrors this same decomposition:

```
 host PC  ──USB serial──►  Arduino Uno R4 Minima
                                │  PWM duty (D9, 20 kHz)        ┌─ encoder A/B (D2/D3)
                                │  direction (D4/D5)            │
                                ▼                               │
                          L298N H-bridge ──► motor terminals ──► DC gearmotor ──► output shaft
                          (driver block)      (V_motor)          (dynamic block)   │
                                                                                   ▼
                                                                          600-PPR quadrature
                                                                          encoder (2400 cnt/rev)
                                                                                   │
                                  RPM telemetry ◄── 10 ms velocity estimate ◄──────┘
```

> *Figure 1.1 (placeholder — replace with a vector block diagram).* PWM command → static driver-voltage block (L298N) → motor dynamic block → measured RPM. The directional voltage asymmetry that motivates the cascade model (Chapter 3) originates in the L298N output stage; the encoder closes the measurement path.

## 2.2 Components

| Subsystem | Part | Key specification | Reference |
|---|---|---|---|
| Controller | Arduino Uno R4 Minima | Renesas RA4M1 (Arm Cortex-M4, 48 MHz); PlatformIO board id `uno_r4_minima` | `platformio.ini` |
| Motor driver | L298N dual H-bridge (one channel used) | Up to 2 A/channel; bipolar-transistor output stage with non-negligible saturation drop | `PIN_CONFIGURATION.md` |
| Motor | Orange–Johnson 12 V geared DC motor | 60:1 gearbox, ≈300 rpm rated output at 12 V | `datasheets/Orange-Johnson-Geared-Motor-12V-60K-300RPM…` |
| Encoder | Orange 3806-OPTI-600-AB-OC | 600 PPR, 2-channel (A/B) quadrature, open-collector output, mounted on the **output** shaft | `datasheets/User-Manual-Orange-3806-OPTI-600…` |
| Motor supply | Bench PSU | 12.0 V set-point, 1.5 A current limit | `data/metadata/2026-05-07_phase21_session.md` |
| Logic supply | Arduino 5 V rail | Feeds encoder V_CC and L298N logic 5 V | `PIN_CONFIGURATION.md` |

Static-characterisation instrumentation (Chapter 3) added a digital multimeter (DMM) for mean motor voltage and a two-channel oscilloscope with a math channel for the differential motor voltage; these are listed here for completeness as they form part of the measurement chain.

## 2.3 Wiring and pin mapping

The Arduino-to-peripheral wiring is fixed across all sessions:

| Arduino pin | Net | Function |
|---|---|---|
| D2 | Encoder A | Quadrature input (CHANGE interrupt) |
| D3 | Encoder B | Quadrature input (CHANGE interrupt) |
| D4 | L298N IN1 | Direction bit 1 |
| D5 | L298N IN2 | Direction bit 2 |
| D9 | L298N ENA | PWM speed command |
| 5V | Encoder V_CC, L298N logic 5 V | Logic supply |
| GND | Encoder GND, L298N GND, PSU − | Common (star) ground |

Only one L298N channel is used: OUT1/OUT2 drive the motor, ENA/IN1/IN2 are the control inputs, and ENB/IN3/IN4/OUT3/OUT4 are left unconnected. Two jumper changes on the L298N board are required and were verified before every session:

- **ENA jumper removed**, so the Arduino D9 PWM signal — rather than a fixed on-board pull-up — controls channel-A speed.
- **5 V regulator (5V-EN) jumper removed**, because the Arduino 5 V rail supplies the L298N logic; leaving it in would back-feed the on-board regulator.

The encoder is open-collector, so each channel uses a 4.7 kΩ pull-up to the 5 V rail (placed between the signal line and 5 V, not in series). All grounds — Arduino, encoder, L298N, and the PSU negative — meet at one star node, and the high-current motor path is kept short and direct rather than routed through thin breadboard rails, to avoid ground-bounce on the shared logic reference.

## 2.4 PWM generation

Speed is commanded as an 8-bit duty value (0–255) on D9 at a fixed **20 kHz** carrier. The Uno R4 PlatformIO core does not expose a global `analogWriteFrequency()`, so the carrier is configured directly through the Renesas `PwmOut` API (`motorPwm.begin(20000.0f, 0.0f)`; duty applied with `pulse_perc()`). Twenty kilohertz is chosen deliberately: it sits at the top of the audible band so the motor does not whine, and — more importantly for this study — it makes the H-bridge output a clean high-frequency square wave whose **time-average** is a stable, well-defined motor voltage. That averaging is what allows the DMM and oscilloscope math channel to read a repeatable `V_motor` during the static sweeps of Chapter 3; at a low carrier the average reading wanders and the static map becomes unmeasurable.

## 2.5 Encoder interface and velocity estimation

The encoder produces 600 pulses per revolution per channel. Both channels are decoded in full quadrature: A and B each trigger an interrupt on every edge (`CHANGE`), and a 16-entry state-transition lookup table converts each (previous, current) two-bit state pair into a step of −1, 0, or +1. Four edges per pulse period yield **2400 counts per output-shaft revolution**, i.e. an angular resolution of 360°/2400 = **0.15° per count** at the output shaft.

Velocity is not measured directly; it is estimated by finite difference of the accumulated count over the fixed 10 ms telemetry interval,

$$\text{RPM} = \frac{\Delta\text{count}\;\times\;60\times10^{6}}{2400\;\times\;\Delta t_{\mu s}},$$

evaluated once per sample. The single-count change over a 10 ms window therefore corresponds to a velocity quantisation of

$$\frac{60\times10^{6}}{2400\times10^{4}} = 2.5\ \text{rpm/count},$$

which sets the noise floor of the RPM signal and is the reason the dynamic-fitting code (Chapter 4) treats sub-≈2 rpm excursions as quantisation rather than motion. The encoder ISR is short and non-blocking; count reads in the main loop are taken inside a brief interrupt-disabled critical section to avoid tearing the 32-bit counter.

## 2.6 Direction and sign conventions

Direction is set by the IN1/IN2 pair: forward drives IN1 high / IN2 low, reverse drives IN1 low / IN2 high, and IN1 low / IN2 low coasts. The convention adopted throughout the thesis is **forward → positive RPM, reverse → negative RPM**. Each telemetry row carries the direction explicitly as a character — `F`, `R`, or `N` (neutral/coast) — so that the unsigned PWM magnitude and the signed velocity can always be reconstructed unambiguously by the analysis code via `signed = pwm × {F:+1, R:−1, N:0}`.

## 2.7 Firmware architecture

Two firmware behaviours were used, sharing identical pin definitions, encoder decoding, PWM setup, and telemetry format, and differing only in how transitions are commanded:

- **Manual-mode firmware** (`firmware_archive/manual_mode_v1.cpp`) accepts single-character serial commands (set forward / reverse / stop, zero the counter, print help) and an integer PWM magnitude, and streams telemetry continuously. It was used for the operator-driven static sweeps and deadzone ramps of Chapter 3.
- **Automated step-sequencer firmware** (`firmware_archive/step_response_v1.cpp` for Phase 2.1; `step_response_v2.cpp` for the gap-fill session, mirrored into the active `src/main.cpp`) executes a pre-programmed array of step trials hands-off on a single `GO` command, emitting each trial as a delimited block (`=== START <name> ===` … `=== END ===`). This removed operator timing variability from the dynamic step-response data of Chapter 4.

All telemetry is emitted at **230400 baud** as comma-separated rows `t_ms, pwm_cmd, dir, enc_count, rpm` at a 10 ms cadence. A host-side capture script logs the stream, and a splitter script cuts the delimited blocks into per-trial CSV files; raw CSVs are treated as immutable and all derived quantities are written separately under `data/processed/`.

## 2.8 Commissioning and acceptance (Phase 0)

Before any identification data were trusted, the rig passed an acceptance gate confirming a clean firmware build, the 12.0 V / 1.5 A supply setting, and the 20 kHz PWM command. The substantive commissioning finding concerned the **encoder sign**.

A single-operating-point check was run at PWM = 150 in both directions, with oscilloscope CH1 on OUT1, CH2 on OUT2, and a math channel computing CH1 − CH2 as the differential motor voltage:

| Command | Math (CH1−CH2) mean | Serial RPM | PSU current |
|---|---|---|---|
| Forward | +1.7 to +2.1 V | −58 to −59 rpm | 0.22 A |
| Reverse | −2.5 to −3.0 V | +56 to +61 rpm | 0.21 A |

The motor-voltage polarity was internally consistent — a forward command produced a positive differential voltage and a reverse command a negative one — but the **reported RPM sign was inverted relative to the command**: forward drive read negative, reverse read positive. The diagnosis was that the encoder A/B phasing was reversed with respect to the chosen command convention, not a wiring or polarity fault in the power path. The fix was a one-line firmware change setting the encoder decode sign to −1 (`ENCODER_SIGN = -1`), after which the build was rebuilt successfully and the PWM = 150 gate was repeated to confirm forward → positive RPM and reverse → negative RPM. This sign correction is baked into every firmware variant used for the data in this thesis, and it establishes the directional convention used uniformly from Chapter 3 onward.

A separate within-session repeatability spot-check at PWM = ±255 (morning versus evening of the same day) confirmed the measurement chain was stable: the motor-side velocity reproduced to within ≈1 %, while the driver-side motor voltage and PSU current drifted by a few percent — an early, direct indication that what little instability the rig exhibits lives in the L298N (driver) stage rather than the motor, foreshadowing the cascade decomposition developed in Chapter 3.

## 2.9 Summary

The plant is a 12 V, 60:1 DC gearmotor driven by one channel of an L298N at a 20 kHz, 8-bit PWM command, with direction set by two logic lines and velocity measured by a 600-PPR quadrature encoder decoded to 2400 counts/rev (0.15°/count) on the output shaft. An Arduino Uno R4 Minima performs PWM generation, direction control, interrupt-driven encoder decoding, and 10 ms telemetry at 230400 baud; velocity is a finite-difference estimate with a 2.5 rpm quantisation floor. Commissioning fixed an inverted encoder sign and established the forward-positive / reverse-negative convention, and an early repeatability check localised the rig's only measurable drift to the driver stage. This hardware is the fixed substrate for the static characterisation (Chapter 3), dynamic characterisation (Chapter 4), and validation (Chapter 5) that follow.

---

### Sources for this chapter
`PIN_CONFIGURATION.md` (pin map, jumpers, pull-ups, grounding, direction table) · `firmware_archive/step_response_v2.cpp` and `…manual_mode_v1.cpp` (encoder decode, 2400 cnt/rev, RPM formula, 20 kHz PwmOut, telemetry/baud) · `thesis_notes/log.md` 2026-05-04 / 2026-05-06 (Phase 0 acceptance, scope check, encoder-sign fix, ±255 spot-check) · `data/metadata/2026-05-07_phase21_session.md` (PSU set-point/limit) · `datasheets/` (motor, encoder) · status-doc §2.
