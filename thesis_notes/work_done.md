# Work Done

## 2026-05-06 - Phase 0 and Phase 1.1

- Diagnosed encoder sign mismatch during the PWM=150 oscilloscope gate.
- Updated firmware encoder sign so forward command corresponds to positive RPM and reverse command corresponds to negative RPM.
- Integrated completed static sweep data as one combined raw CSV:
  - `data/raw/static_sweep_20260506_run1.csv`
  - 52 rows total
  - 26 forward rows and 26 reverse rows
  - PWM range 10 to 255 in both directions
- Rebuilt `notebooks/01_static_map.ipynb` around the combined CSV workflow.
- Added figure outputs for:
  - PWM command vs motor voltage
  - PWM command vs steady-state RPM
  - motor voltage vs steady-state RPM with through-origin gain estimates
  - forward/reverse asymmetry ratio
