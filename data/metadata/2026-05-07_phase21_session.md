# Phase 2.1 Step-Response Session

**Date:**         2026-05-06
**Operator:**     [your name]
**Start time:**   __:__
**End time:**     __:__
**Firmware:**     `step_response_v1` (archived at `firmware_archive/step_response_v1.cpp`)

---

## Environment

| Item | Value |
|---|---|
| Ambient temperature | ___ °C |
| PSU voltage (set)   | 12.0 V |
| PSU current limit   | 1.5 A |
| Motor warm-up time  | ___ s |

## Hardware verification (tick before starting)

- [ ] PSU set to 12.0 V, current limit 1.5 A
- [ ] Scope CH1 probe tip on **OUT1**, CH2 probe tip on **OUT2**
- [ ] Both probes set to **10x**
- [ ] Both probe ground clips on the breadboard GND rail
- [ ] PSU −, Arduino GND, L298N GND all on the same rail (star ground)
- [ ] Motor spins freely by hand (no mechanical bind)
- [ ] Encoder responds when shaft turned by hand (`enc_count` changes in serial)
- [ ] Serial monitor at 230400 baud shows `# step_response_v1 ready`

## Run

| Item | Value |
|---|---|
| Total trials                | 30 |
| Raw serial log              | `data/raw/serial_logs/2026-05-06_phase21_session.log` |
| Split CSVs directory        | `data/raw/step_responses/` |
| Trial sequence reference    | `firmware_archive/step_response_v1.cpp` (Trial array) |

## Issues encountered

- No capture anomaly observed in the final run.
- Note for quick-look interpretation: step-down trials begin logging immediately after the start PWM is applied, so the first ~500 ms show spin-up to the 240 PWM hold speed before the 3000 ms step down.

---

## Post-run verification (tick after capture)

- [x] Serial log file contains `=== SEQUENCE COMPLETE ===`
- [x] `split_log.py` reports 30 trials found
- [x] All 30 CSV files present in `data/raw/step_responses/`
- [x] Step-up trials: ~550 data rows each (5.5 s @ 10 ms)
- [x] Step-down trials: ~800 data rows each (8.0 s @ 10 ms)
- [x] `step_up_fwd_*` files: RPM positive after step
- [x] `step_up_rev_*` files: RPM negative after step
- [x] No CSV has truncated content or stray non-numeric rows

## Quick-look spot checks (open one of each in a viewer)

- [x] `step_up_fwd_240_run01.csv`: RPM rises from ~0 and settles near 205 rpm, smooth curve
- [x] `step_up_rev_240_run01.csv`: RPM falls from ~0 and settles near -220 rpm
- [x] `step_down_fwd_240to0_run01.csv`: RPM reaches hold speed during pre-step interval, holds until 3000 ms, then decays toward 0

## Notes

- Source serial log: `data/raw/serial_logs/2026-05-06_phase21_session.log`.
- Split verification: 30 CSVs exactly match the 30 `=== START ... ===` blocks in the serial log.
- Row counts verified: step-up trials have 550-551 data rows; step-down trials have 800-801 data rows.
- Spot-check window means:
  - `step_up_fwd_240_run01.csv`: 0 rpm before 500 ms; settled final 1 s mean about 205.5 rpm.
  - `step_up_rev_240_run01.csv`: 0 rpm before 500 ms; settled final 1 s mean about -219.9 rpm.
  - `step_down_fwd_240to0_run01.csv`: 2500-3000 ms mean about 215.2 rpm; final 1 s mean 0 rpm.
