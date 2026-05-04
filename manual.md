# DC Motor System Identification - Phase 0-1 Lab Manual

This is the operational checklist for the current root-level PlatformIO repo.
Follow it in order. Do not start a full sweep until the Phase 0 acceptance gate
passes.

## Current Project Layout

```text
System_Identification_DC_Motor/
├── platformio.ini
├── src/main.cpp
├── README.md
├── manual.md
├── plan.md
├── PIN_CONFIGURATION.md
├── data/
│   ├── raw/
│   ├── processed/
│   ├── metadata/
│   └── templates/
├── notebooks/
├── figures/
├── models/
└── thesis_notes/log.md
```

Target board:

```ini
[env:uno_r4_minima]
platform = renesas-ra
board = uno_r4_minima
framework = arduino
monitor_speed = 230400
```

## Firmware Protocol

Build, upload, and monitor from the repo root:

```bash
pio run
pio run -t upload
pio device monitor -b 230400
```

The firmware prints:

```text
t_ms,pwm_cmd,dir,enc_count,rpm
```

Commands:

| Command | Action |
|---|---|
| `f` | Set forward direction |
| `r` | Set reverse direction |
| `s` | Stop / coast |
| `z` | Zero encoder count |
| `?` | Print help |
| `0..255` | Set PWM magnitude |

Important convention:

- Type only positive PWM magnitudes: `0..255`.
- Direction comes from `f` or `r`.
- Raw sweep CSVs store `pwm_cmd` as the typed magnitude and `direction` as
  `fwd` or `rev`.
- RPM keeps its natural sign from firmware telemetry.

## Lab Notebook Discipline

Append to `thesis_notes/log.md` for every bench session. Include PSU setting,
current limit, DMM model, motor warm/cold state, and anything unusual.

## Day 1 - Firmware And Phase 0 Acceptance

### Step 1.1: Build And Upload

```bash
pio run
pio run -t upload
pio device monitor -b 230400
```

Expected startup:

```text
=== DC Motor System Identification Manual Mode ===
t_ms,pwm_cmd,dir,enc_count,rpm
```

The Uno R4 PlatformIO core used here does not expose a global
`analogWriteFrequency()` API. The firmware sets D9 PWM to 20 kHz with the
Renesas `PwmOut` API:

```cpp
motorPwm.begin(20000.0f, 0.0f);
```

This is required for stable DMM average-voltage readings.

### Step 1.2: Encoder Smoke Test With PSU Off

1. Keep the 12 V motor PSU off.
2. Connect Arduino USB and open the serial monitor.
3. Send `z`.
4. Rotate the motor output shaft one full forward revolution by hand.
5. Confirm encoder count changes by about `+2400`.
6. Rotate back and confirm count returns near zero.

If forward motion gives negative count, either swap encoder A/B or set
`ENCODER_SIGN = -1` in firmware and rebuild.

### Step 1.3: Power Smoke Test With PSU On

1. Set PSU to 12.00 V and current limit to a safe bench value.
2. Send `f`, then `150`.
3. Confirm forward rotation and positive RPM.
4. Send `s`.
5. Send `r`, then `150`.
6. Confirm reverse rotation and negative RPM.
7. Send `s`.

Stop here if motor direction, encoder sign, or stop/coast behavior is wrong.

### Step 1.4: Single-Point DMM Gate

Measure average motor voltage with the DMM across the motor terminals.

Record this in `thesis_notes/log.md` under `Phase 0 acceptance`:

| Direction | PWM | DMM Vmean (V) | RPM from serial | Notes |
|---|---:|---:|---:|---|
| fwd | 150 | ___ | ___ | ___ |
| rev | 150 | ___ | ___ | ___ |

Do not start Day 2 until these readings are plausible and repeatable.

### Step 1.5: DMM Stability Check

Copy the template:

```bash
cp data/templates/dmm_stability_check_template.csv data/raw/dmm_stability_check_run01.csv
```

At PWM 200, take five DMM readings after the motor settles. Fill:

```text
reading_idx,pwm_cmd,direction,vmean_v,timestamp,notes
```

Use this check to decide whether the DMM reading is stable enough for a full
sweep.

## Day 2 - Phase 1.1 Static Sweep

### Raw CSV Schema

Raw files contain only measured values:

```text
pwm_cmd,direction,vmean_v,rpm,notes
```

Do not add scope-only fields such as `vmax` or `duty`. Do not add derived
columns to raw data.

### Forward Sweep

Create the raw file:

```bash
cp data/templates/static_sweep_template.csv data/raw/static_sweep_fwd_run01.csv
```

Fill `direction` as `fwd` for every row.

Procedure for each PWM value:

1. Send `f`.
2. Send the PWM magnitude from the row.
3. Wait 4 seconds.
4. Read DMM average voltage across the motor terminals.
5. Copy the latest RPM from serial telemetry.
6. Fill `vmean_v`, `rpm`, and `notes`.

### Reverse Sweep

Create the raw file:

```bash
cp data/templates/static_sweep_template.csv data/raw/static_sweep_rev_run01.csv
```

Fill `direction` as `rev` for every row.

Procedure for each PWM value:

1. Send `r`.
2. Send the PWM magnitude from the row.
3. Wait 4 seconds.
4. Read DMM average voltage across the motor terminals.
5. Copy the latest RPM from serial telemetry.
6. Fill `vmean_v`, `rpm`, and `notes`.

For reverse runs, `pwm_cmd` remains positive because it is the typed command.
The `direction` column records reverse, and RPM should be negative.

### Repeat Runs

Collect at least three runs per direction:

```text
static_sweep_fwd_run01.csv
static_sweep_fwd_run02.csv
static_sweep_fwd_run03.csv
static_sweep_rev_run01.csv
static_sweep_rev_run02.csv
static_sweep_rev_run03.csv
```

Record warm/cold state and any bench changes in `thesis_notes/log.md`.

## Quick Plot

After at least one real sweep exists:

```bash
jupyter notebook notebooks/01_static_map.ipynb
```

The notebook validates the raw schema and plots forward and reverse data on
shared axes. It is plot-only for this phase.

## Do Not Do Yet

- Do not write autonomous trajectory firmware.
- Do not write a host logger.
- Do not fit models.
- Do not generate validation datasets.

One phase at a time.
