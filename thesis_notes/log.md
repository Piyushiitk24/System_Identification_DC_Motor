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

## 2026-05-07 - Phase 1.1 static-map interpretation

Headline finding from Plot 3:

- Static-block-only asymmetry hypothesis confirmed by Phase 1.1 sweep: V-to-RPM gain is symmetric within about 9% across direction.
- Forward motor gain: `K_fwd = 26.94 rpm/V`.
- Reverse motor gain magnitude: `K_rev = 24.52 rpm/V` (`K_rev` is negative when signed).
- The large directional asymmetry appears mainly in the PWM-to-voltage map, not in the voltage-to-RPM map.

Interpretation:

- Reverse produces about 7% more delivered motor voltage at high PWM and more than 2x the forward voltage at some low PWM points.
- Once delivered motor voltage is used as the input, forward and reverse RPM gains are close.
- This supports the cascade decomposition: the static driver block captures L298N voltage asymmetry, while the motor dynamic block is approximately direction-symmetric.
- Physical explanation: the DC motor is nearly electromagnetically symmetric, while the L298N output stages are not because different switch paths have different saturation drops.

Thesis note:

- This is a defensible result for using a cascaded structure: `PWM command -> driver/static voltage block -> motor dynamic block`.

## 2026-05-06 - Deadzone hysteresis

Phase 1.2 complete via manual ramp.

- Multiple manual ramp runs in both directions show breakaway PWM approximately 150: fwd 154, rev 144.
- Dropout PWM approximately 113: fwd 114, rev 112.
- Hysteresis band is about 32-40 PWM wide.
- Phase 1.1 staircase sweep showed breakaway at PWM=130 because the staircase steps deliver enough torque for kinetic motion above dropout but caught a stochastic breakaway.
- True breakaway is higher and stochastic.
- Model implication: deadzone block must include hysteresis.
- Phase 1.2 closed; data saved in `data/raw/deadzone_manual_run01.csv`.

## 2026-05-06 evening - Phase 2.1 complete; Phase 1.1 expanded to 3 runs

Phase 2.1 step-response data captured under `step_response_v1` firmware. 30 trials: 9 step-ups x 3 PWM levels (160, 200, 240) x 2 directions, plus 12 step-downs (240->0 and 240->160 x 2 directions x 3 runs). Ambient temp ___ deg C, PSU 12.0 V. Serial log at `data/raw/serial_logs/2026-05-06_phase21_session.log`, split CSVs at `data/raw/step_responses/`. Session metadata at `data/metadata/2026-05-07_phase21_session.md`. Firmware archived at `firmware_archive/step_response_v1.cpp`.

Phase 1.1 run02 and run03 also collected with manual-mode firmware (archived at `firmware_archive/manual_mode_v1.cpp`). Same ambient conditions as morning's run01. Reproducibility data secured before next session, per concern about driver behaviour drift across days.

2026-05-06 evening — Phase 1.1 reproducibility validated via spot-check + Phase 2.1 implicit cross-validation.
Decision: full Phase 1.1 repeats deferred. Validation strategy adopted instead:

Phase 1.2 manual ramp (multiple passes) validates the deadzone region.
Phase 2.1 step-up steady-state values (last 1 s of each trial) will validate the above-deadzone region in 18 implicit data points; comparison to be done in notebooks/03_step_responses.ipynb.
Two-point spot-check at PWM=±255 collected this evening (data at data/raw/spot_check_max_pwm_2026-05-06_evening.csv).

Spot-check results (run01 → evening, at PWM=±255):
V_motor driftRPM driftPSU current driftForward−3.8%−0.6%−4.5%Reverse+1.9% (mag)+0.8% (mag)−8.7%
Interpretation: Motor (V→RPM block) is reproducible to <1% across the session. Driver (PWM→V block) drifts ~2–4% in V_motor and ~5–9% in PSU current — consistent with L298N junction thermal drift after extended operation. This drift pattern empirically supports the cascade decomposition: instability is isolated in the driver-side static block; the motor-side dynamic block is stable. The session-bounded data-collection methodology is justified. Static-block parameters fit from this dataset are valid only at this session's ambient/thermal condition; this caveat to be stated in the thesis.
