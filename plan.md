# DC Motor System Identification — Updated Master's Thesis Plan

**Setup:** 12V, 300 RPM, 60:1 geared DC motor + L298N driver + 600 PPR quadrature encoder (output shaft) + Arduino Uno R4 Minima + bench PSU  
**Goal:** Identify a compact model that captures:
- driver voltage loss / droop,
- deadzone and breakaway asymmetry,
- forward / reverse mismatch,
- operating-point-dependent dynamics,
- and delay,

and then show that this model improves closed-loop performance over a naive global LTI model.

**Toolchain:** macOS + VS Code + PlatformIO (firmware) + Python 3.11 + Jupyter (analysis)

---

## Repository Layout

```text
System_Identification_DC_Motor/
├── plan.md
├── manual.md
├── README.md
├── PIN_CONFIGURATION.md
├── platformio.ini
├── src/main.cpp
├── data/
│   ├── raw/
│   ├── processed/
│   ├── metadata/
│   └── templates/
├── notebooks/
│   └── 01_static_map.ipynb
├── models/
├── figures/
└── thesis_notes/
```

---

# PHASE 0 — Rig Build, Instrumentation, and Acceptance

## 0.1 Bill of Materials

| Item | Notes |
|---|---|
| Arduino Uno R4 Minima | Current PlatformIO target |
| L298N motor driver module | Standard board |
| 12V, 300 RPM, 60:1 geared DC motor with 600 PPR quadrature encoder | Confirm exact encoder spec in datasheet |
| Bench PSU, 0–30V / 0–5A | **Mandatory for ID runs** |
| INA219 breakout | Optional future Phase 2 supply-current monitor |
| Resistors: 10 kΩ × 6, 3.3 kΩ × 3, 4.7 kΩ × 2 | Dividers + encoder pull-ups |
| Capacitors: 100 nF ceramic × 6, 470 µF electrolytic × 1 | Decoupling + ADC low-pass + motor suppression |
| Breadboard / terminal blocks / wires | Keep power and signal wiring physically separated |
| DMM / multimeter | Mandatory for Phase 0-1 average motor-voltage readings |
| Oscilloscope | Optional sanity check only; not required for Phase 0-1 raw data |

### Important note on current sensing
The INA219 on the supply rail measures **supply current**, not true instantaneous armature current.  
This is useful for:
- supply droop,
- thermal drift,
- power trends,

but it is **not** a clean motor-current sensor for detailed grey-box electrical identification.

---

## 0.2 Pin Assignments (Arduino Uno R4 Minima)

| Arduino Pin | Function | Connected To |
|---|---|---|
| D2 (INT0) | Encoder A | Encoder channel A, with 4.7 kΩ pull-up to 5V |
| D3 (INT1) | Encoder B | Encoder channel B, with 4.7 kΩ pull-up to 5V |
| D4 | L298N IN1 | Direction |
| D5 | L298N IN2 | Direction |
| D9 (PWM) | L298N ENA | PWM output |
| A0 | OUT1 average voltage | Via 10k / 3.3k divider + 100 nF low-pass cap |
| A1 | OUT2 average voltage | Via 10k / 3.3k divider + 100 nF low-pass cap |
| A2 | Supply voltage | Via 10k / 3.3k divider |
| A4 | INA219 SDA | I²C |
| A5 | INA219 SCL | I²C |
| 5V | Logic power | Arduino → L298N logic 5V, encoder VCC, INA219 VCC |
| GND | Common signal ground | Returned to a **single physical star point** |

### PWM frequency
Use D9 and keep PWM frequency fixed for the entire study. Phase 0-1 firmware
sets 20 kHz for stable DMM readings.

---

## 0.3 Wiring — Power Path

### Correct grounding philosophy
Use a **true star ground**, not a daisy chain.

**Physical star point:** one common ground junction near the PSU negative terminal or a short terminal block.

From that single point, run separate ground branches to:
- L298N power ground
- Arduino ground
- INA219 ground
- encoder ground

### Power wiring
```text
Bench PSU (+12V) ──→ INA219 VIN+ ──[shunt]──→ INA219 VIN- ──→ L298N VS
Bench PSU (GND)  ──→ STAR GROUND NODE
STAR NODE ──→ L298N GND
STAR NODE ──→ Arduino GND
STAR NODE ──→ INA219 GND
STAR NODE ──→ Encoder GND
```

### Decoupling / suppression
- 470 µF electrolytic across L298N `VS` and `GND`, physically close to module supply pins
- 100 nF ceramic in parallel with it
- 100 nF ceramic directly across motor terminals
- 100 nF ceramic across encoder VCC and GND near encoder

### L298N 5V jumper
If your board allows external 5V logic input when the jumper is removed, remove it and power logic 5V from the Arduino.  
**Verify the board’s exact behavior first.**

---

## 0.4 Wiring — Logic Path

```text
Arduino D4 ──→ L298N IN1
Arduino D5 ──→ L298N IN2
Arduino D9 ──→ L298N ENA
Arduino 5V ──→ L298N logic 5V, Encoder VCC, INA219 VCC
```

### Command conventions
- `IN1=HIGH, IN2=LOW` → forward
- `IN1=LOW, IN2=HIGH` → reverse
- `IN1=LOW, IN2=LOW` → coast
- `IN1=HIGH, IN2=HIGH` → brake

For this thesis, use:
- **coast at zero PWM**
- do **not** use brake mode in the identification datasets

Brake introduces different dynamics and should not be mixed into the main model.

---

## 0.5 Wiring — Encoder

```text
Encoder A ──[4.7k]──┬──→ Arduino D2
                    └──→ 5V
Encoder B ──[4.7k]──┬──→ Arduino D3
                    └──→ 5V
Encoder VCC ──→ Arduino 5V
Encoder GND ──→ STAR GROUND
```

### Wiring rules
- Twist A and B together
- Keep encoder wires away from motor power wires
- Keep motor loop area small
- Add 100 nF at encoder supply pins

---

## 0.6 Wiring — Voltage Dividers and ADC Filtering

For each measured node:

```text
Measured node ──[10 kΩ]──┬──→ Arduino analog pin
                         ├──[3.3 kΩ]──→ GND
                         └──[100 nF]──→ GND
```

### Why this matters
The outputs of the H-bridge are PWM-switched.  
The ADC is **not simultaneous**, so `analogRead(A0) - analogRead(A1)` only makes sense if A0 and A1 are measuring a **low-pass average**, not raw switching edges.

### Interpretation of motor voltage
Define:

```text
V_motor_avg = V_OUT1_avg - V_OUT2_avg
```

This is the **average differential motor voltage**, not the instantaneous waveform.

### Calibration
Do a one-time divider calibration with a DMM and store the scale factors in firmware.

---

## 0.7 Firmware Structure

### PlatformIO `platformio.ini`
```ini
[env:uno_r4_minima]
platform = renesas-ra
board = uno_r4_minima
framework = arduino
monitor_speed = 230400
```

### Phase 0-1 scheduling philosophy
- Manual command entry from Serial Monitor
- Firmware telemetry every `100 ms`
- PWM on D9 at `20 kHz` for stable DMM average-voltage readings
- No autonomous trajectory playback or host logger in Phase 0-1

### `src/main.cpp` responsibilities

1. **Setup**
   - Configure PWM on D9 at `20 kHz`
   - Initialize Serial at `230400`
   - Attach encoder interrupts

2. **Quadrature decoding**
   - Use ISR-based count update
   - Keep ISR extremely small

3. **Manual control**
   - `f` sets forward direction
   - `r` sets reverse direction
   - `s` stops / coasts
   - `z` zeros encoder count
   - numeric `0..255` input sets PWM magnitude

4. **Telemetry output every 100 ms**
```text
t_ms,pwm_cmd,dir,enc_count,rpm
```

Phase 2 may later add autonomous trajectory playback and host logging, but
those are intentionally out of scope for the current Phase 0-1 scaffold.

---

## 0.8 Speed Estimation Strategy

### In firmware
Do **not** treat one RPM sample as the final modeling truth.

For Phase 0-1, firmware prints cumulative `enc_count` and an operator-facing
RPM estimate every 100 ms. Static sweep raw files copy the settled RPM reading.

### Offline speed estimation
Use two offline speed signals:
1. **fast speed estimate** for step/transient analysis
2. **slow filtered speed estimate** for deadzone detection near zero

This avoids trying to detect 1 RPM from one tiny count difference in firmware.

---

## 0.9 Host Logging Script

Not part of Phase 0-1. Static sweeps are hand-entered from DMM and serial
readings.

For Phase 2, create one logger that saves:
- raw CSV
- a sidecar metadata JSON or CSV row

Metadata fields:
- run name
- date/time
- firmware git commit
- ambient temperature if known
- motor warm/cold state
- PSU voltage setting
- current limit
- notes

---

## 0.10 Acceptance Tests — ALL MUST PASS

### Electrical / instrumentation
- [ ] A1. PWM = 0 → motor still, no unintended creep
- [ ] A2. `v_motor_avg` at fixed PWM is stable and repeatable
- [ ] A3. `v_motor_avg` agrees reasonably with DMM average reading at PWM = 50, 150, 250
- [ ] A4. DMM reading is stable enough at PWM = 200 across five readings
- [ ] A5. Supply rail stays stable under load

### Encoder / timing
- [ ] A6. 10 slow manual shaft revolutions → encoder count matches expected count
- [ ] A7. Direction sign flips correctly
- [ ] A8. No missed counts at max speed
- [ ] A9. Logging loop does not overrun
- [ ] A10. Firmware uses fixed 20 kHz PWM for DMM stability
- [ ] A11. No dangerous spikes / wiring noise issue on motor terminals

### Thermal / repeatability
- [ ] A12. A fixed command repeated 3 times gives similar speed and voltage results
- [ ] A13. Run order and warm-up effects are observable and documented

Do **not** proceed until Phase 0 is trustworthy.

---

# PHASE 1 — Static Characterization

## 1.1 Static Sweep (combined forward/reverse CSV)

### Raw files
- `static_sweep_YYYYMMDD_runN.csv`
- First completed run: `static_sweep_20260506_run1.csv`

Use typed PWM magnitudes for both directions:
- `pwm_cmd`: `0, 10, 20, ..., 250, 255`
- `direction`: `fwd` or `rev`

Store both directions in one file. Do not split forward and reverse into
separate raw files unless there is a bench-process reason to do so.

Raw CSV schema:
```text
pwm_cmd,direction,vmean_v,rpm,notes
```

Do not store scope-only fields such as `vmax` or `duty` in raw files.

### Hold per level
Use **4 seconds per level**:
- first `1.0 s` discarded
- next `3.0 s` averaged

Repeat each full sweep **3 times**, but do not run all repeats back-to-back without noting temperature / warmness.

### Analysis (`01_static_map.ipynb`)
For each step compute:
- mean `pwm_cmd`
- mean measured `vmean_v`
- mean `rpm`

### Plots
1. `pwm_cmd` vs `rpm`
2. `pwm_cmd` vs `vmean_v`
3. `vmean_v` vs `rpm`
4. forward and reverse overlaid on shared axes

### Phase 0-1 output
Plot only. Do not fit models until the static sweeps are complete and reviewed.

### Important interpretation
Do **not** call Plot 4 “output impedance”.  
Call it:
- **driver droop / load interaction**
or
- **supply current vs delivered average motor voltage**

---

## 1.2 Deadzone and Breakaway Hysteresis

### Trajectories
- `slow_ramp_fwd.csv`
- `slow_ramp_rev.csv`

Ramp by `1 PWM count` every `500 ms` up to `100`, then back to zero.  
Repeat each direction **5 times**, with brief rest between repeats.

### Detection logic
Use **filtered speed**, not raw 10 ms speed.

Define:
- `start threshold` = first command where filtered speed exceeds `3 RPM` for at least `150 ms`
- `stop threshold` = last command before filtered speed drops below `3 RPM` for at least `150 ms`

Save:
- `PWM_start_fwd`
- `PWM_stop_fwd`
- `PWM_start_rev`
- `PWM_stop_rev`

Also store mean and std across repeats.

### Interpretation
- `start > stop` indicates breakaway / kinetic mismatch
- forward/reverse mismatch indicates asymmetry

---

# PHASE 2 — Dynamic Experiments

## 2.1 Main Staircase Dataset

### Trajectory `staircase_main.csv`
Hold each level for **5 seconds**.

Example:
```text
0, 60, 40, 90, 70, 120, 100, 160, 130, 200, 150, 255, 180, 100, 0,
-60, -40, -90, -70, -120, -100, -160, -130, -200, -150, -255, 0
```

Purpose:
- within-quadrant up/down steps
- forward/reverse asymmetry
- approach to zero from both sides

Run **5 times**, but record warm/cold state and allow thermal notes.

---

## 2.2 Reversal Stress Dataset

### Trajectory `staircase_reversal.csv`
Use only strong reversal cases, for example:
```text
0, 80, -80, 0, 180, -180, 0, 120, -120, 0
```

Purpose:
- isolate reversal behavior
- do not let these dominate the main identification dataset

Run **3–5 times**.

---

## 2.3 Local PRBS Datasets

### Operating-point selection
Do **not** choose operating points directly in PWM.

First use the static map to choose commands corresponding approximately to:
- `±50 RPM`
- `±100 RPM`
- `±150 RPM`
- `±200 RPM`

Create files like:
- `prbs_rpm50.csv`
- `prbs_rpm100.csv`
- etc.

### Structure
For each operating point:
- settle at the operating command for `3 s`
- apply PRBS perturbation around that operating point
- bit period: `50 ms`
- duration: `40–60 s`

### Perturbation size
Choose perturbation small enough to stay local:
- lower operating speeds: smaller perturbation
- higher operating speeds: slightly larger perturbation

The perturbation should not repeatedly slam into deadzone if the purpose is local linearization.

---

## 2.4 Held-Out Validation Datasets — SEAL THESE

Generate and store, but do not use them for tuning model structure.

### Validation files
- `val_unseen_staircase.csv`
- `val_chirp_pos.csv`
- `val_chirp_neg.csv`
- `val_crosszero_random.csv`

### Meaning
- `val_unseen_staircase.csv` → unseen step pattern
- `val_chirp_pos.csv` → within positive quadrant
- `val_chirp_neg.csv` → within negative quadrant
- `val_crosszero_random.csv` → explicit zero-crossing stress test

Keep these sealed until the main models are frozen.

---

# PHASE 3 — Data Analysis and Identification

## 3.1 Preprocessing

In preprocessing:
- reconstruct speed from `enc_count` and `t_us`
- create fast and slow speed estimates
- align all channels to a common time base
- mark step boundaries from the known trajectory
- tag each segment with:
  - direction
  - step sign
  - initial speed bin
  - final speed bin
  - run index
  - warm/cold state

---

## 3.2 Static Block Definition

### Core choice
Define the static block as:

```text
u_cmd  →  v_motor_avg
```

not as `u_cmd → steady-state RPM`.

This keeps the dynamic block physically meaningful and allows `K` to remain part of the dynamic model.

### Static-block outputs
Use:
- deadzone thresholds
- direction asymmetry
- measured average delivered motor voltage

Optional second map:
```text
v_motor_avg → rpm_ss
```

for interpretation and controller feedforward later.

---

## 3.3 Model Families

## Model A — Global LTI baseline
A single global first-order-plus-delay model:
```text
u_cmd → rpm
```

Purpose:
- straw-man baseline
- expected to fit poorly across all regions

---

## Model B — Static block + one global dynamic block
Structure:
```text
u_cmd → static block → v_eff → first-order + delay → rpm
```

Where `v_eff` is based on the measured / fitted average motor voltage behavior.

Parameters:
- `K`
- `tau`
- `delay`

Fit on the main staircase dataset.

---

## Model C — Static block + region-dependent dynamic block
Same static block as Model B, but allow the dynamic block to vary by region.

### Predefined regions
Use physics-based regions only:
- forward accelerating
- forward decelerating
- reverse accelerating
- reverse decelerating

Optional refinement:
- low / mid / high speed bins within each direction

Do **not** search arbitrary overlapping regions after looking at the results.

### Output
This becomes the main “scheduled” model candidate.

---

## Model D — Optional appendix only
A physics-inspired friction model may be attempted only if time remains.

This is **not** part of the thesis critical path.

Reason:
- armature current is not directly measured
- parameter identifiability is weak
- it can become a time sink

If attempted, it goes to appendix / stretch goal.

---

## 3.4 Local Step Feature Extraction

For every relevant step, extract:
- initial speed
- final steady speed
- step size
- response onset
- apparent delay
- local time constant
- local gain

Plot these against:
- direction
- accelerating / decelerating
- initial speed bin
- run index / warmness

This step will justify why Model C is needed.

---

## 3.5 Fitting Procedure

### General rule
Fit using **simulation-based loss on full time series**, not isolated formula fitting unless explicitly segment-based.

### Train / validation split
Use:
- some runs for fitting
- separate runs for model selection
- sealed validation only at the very end

This avoids optimistic bias.

### Regional fitting
Regions must be **predefined**, not mined after the fact.

Save results to:
- `models/model_A.json`
- `models/model_B.json`
- `models/model_C.json`

and if attempted:
- `models/model_D_optional.json`

---

## 3.6 Scoring

In `06_validation_scoring.ipynb`, compute:
- RMSE
- MAE
- FIT%
- VAF

### Also compute per-region metrics
Bin by:
- direction
- accelerating / decelerating
- low / mid / high speed
- zero-crossing vs non-zero-crossing

This table is one of the central thesis results.

---

# PHASE 4 — Closed-Loop Validation

## 4.1 Controller Set

Compare three practical controller structures:

1. **Controller A**  
   PID tuned from Model A

2. **Controller B**  
   PID + static inverse / compensation based on Model B

3. **Controller C**  
   scheduled PID or region-aware controller based on Model C

### Common rules
All controllers must share:
- same sample time
- same output limits
- same anti-windup strategy
- same test trajectory

Do not let trivial windup differences dominate the comparison.

---

## 4.2 Closed-Loop Test Trajectory

Use one reference that includes:
- within-quadrant steps
- small oscillation
- zero crossing
- reversals

This should be the same for all controller comparisons.

### Metrics
- tracking RMSE
- overshoot
- settling time
- error near zero crossing
- direction-dependent error

### Expected story
- Controller A: weakest around deadzone and reversals
- Controller B: better overall
- Controller C: best uniformity across regions

---

# Pitfalls Checklist

- [ ] True physical star ground used
- [ ] Encoder pull-up value consistent everywhere
- [ ] `v_motor_avg` measured as a low-pass average, not raw PWM edge subtraction
- [ ] Serial logging does not overrun the loop
- [ ] Timestamps are microsecond-based
- [ ] Speed is reconstructed offline from cumulative counts
- [ ] Deadzone detection uses sustained filtered motion, not one noisy sample
- [ ] Warm/cold state recorded for every run
- [ ] Validation files remain sealed until models are frozen
- [ ] Main thesis path uses Models A/B/C only
- [ ] Model D is optional appendix only

---

# Thesis Narrative

1. **Introduction**  
   Low-cost motor rigs in labs often use nonideal drivers and show behavior that a single LTI model cannot capture.

2. **Related Work**  
   Existing work on DC motor identification, deadzone effects, and nonlinear compensation.

3. **Hardware and Instrumentation**  
   Bench PSU, driver, encoder, averaged voltage measurement, logging architecture.

4. **Static Characterization**  
   Driver voltage loss, deadzone, breakaway hysteresis, asymmetry.

5. **Dynamic Identification**  
   Global model, static-block model, region-dependent model.

6. **Validation**  
   Held-out datasets and per-region scoring.

7. **Closed-Loop Comparison**  
   Show that better model structure leads to better control behavior.

8. **Discussion and Limitations**  
   Temperature, low-cost hardware variability, unmeasured true armature current.

9. **Conclusion**  
   A compact asymmetric structured model is more useful than one global LTI fit for low-cost DC motor rigs.

---

# Open Tasks Tracker

- [ ] Phase 0 build complete
- [ ] Phase 0 acceptance all pass
- [ ] Phase 1 static sweeps complete
- [ ] Phase 1 deadzone ramps complete
- [ ] Phase 2 main staircase complete
- [ ] Phase 2 reversal staircase complete
- [ ] Phase 2 PRBS datasets complete
- [ ] Validation datasets generated and sealed
- [ ] Model A fit
- [ ] Model B fit
- [ ] Model C fit
- [ ] Held-out scoring complete
- [ ] Closed-loop comparison complete
- [ ] Optional Model D appendix attempted only if time remains
