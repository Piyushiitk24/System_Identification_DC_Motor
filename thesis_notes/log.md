# Lab Log

Append one entry for every bench session. Keep raw observations here even if
they look unimportant at the time.

## 2026-05-04 - Phase 0 acceptance

- PSU setting: ___ V, current limit ___ A
- Board: Arduino Uno R4 Minima
- Firmware build: `pio run` passed: yes / no
- PWM frequency command: 20 kHz
- DMM: __________________

Single-point DMM check:

| Direction | PWM | DMM Vmean (V) | RPM from serial | Notes |
|---|---:|---:|---:|---|
| fwd | 150 |  |  |  |
| rev | 150 |  |  |  |

Decision:

- Ready for Day 2 sweep: yes / no
- Notes:

## 2026-05-06 - Phase 0 oscilloscope single-point check

- PSU voltage display: 12 V
- Motor supply current: 0.21-0.22 A
- Scope setup: CH1 on L298N OUT1 to common ground, CH2 on L298N OUT2 to common ground
- Math channel: CH1 - CH2, used as average motor voltage
- Firmware state during this run: pre-fix encoder sign, `ENCODER_SIGN = 1`

Single-point scope check:

| Command | PWM | CH1 Mean (V) | CH2 Mean (V) | MATH Mean (V) | RPM from serial | PSU current (A) | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| fwd | 150 | 7.66-7.77 | 5.37-5.76 | 1.74-2.10 | -57.75 to -59.00 | 0.22 | Motor voltage polarity positive, RPM sign negative |
| rev | 150 | 5.75-5.80 | 8.27-8.48 | -2.48 to -3.00 | 55.75 to 61.00 | 0.21 | Motor voltage polarity negative, RPM sign positive |

Diagnosis:

- Voltage polarity is consistent: forward command gives positive CH1-CH2 motor voltage, reverse command gives negative CH1-CH2 motor voltage.
- Encoder sign was reversed relative to the command convention.
- Firmware updated after this run: `ENCODER_SIGN` changed from `1` to `-1` in `src/main.cpp`.
- `pio run` passed after the firmware sign change.

Decision:

- Not ready for full static sweep until the PWM=150 gate is repeated after uploading the fixed firmware.

## 2026-05-06 - Phase 1.1 static sweep ingestion

- Raw data file added: `data/raw/static_sweep_20260506_run1.csv`
- Source file copied from: `/Users/piyush/Downloads/static_sweep_20260506_run1.csv`
- File format: single combined forward/reverse CSV with `direction` column
- Schema: `pwm_cmd,direction,vmean_v,rpm,notes`
- Row count: 52 total rows
- Direction counts: 26 `fwd`, 26 `rev`
- PWM range: 10 to 255 for both directions
- Measured fields retained in raw data: PWM command, direction, motor average voltage, steady RPM, and notes with CH1/CH2/math/current details
- Confirmed deadzone boundary used for first analysis notebook: +/-130 PWM

Work completed:

- Replaced generic static-map notebook with dataset-specific `notebooks/01_static_map.ipynb`.
- Notebook outputs four figures under `figures/`.
- Derived slopes and asymmetry ratios remain in notebook outputs, not in the raw CSV.
