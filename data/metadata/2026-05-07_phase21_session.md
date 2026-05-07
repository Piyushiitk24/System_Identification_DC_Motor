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

[Note any anomalies, retries, board resets, motor stalls, etc.]

---

## Post-run verification (tick after capture)

- [ ] Serial log file contains `=== SEQUENCE COMPLETE ===`
- [ ] `split_log.py` reports 30 trials found
- [ ] All 30 CSV files present in `data/raw/step_responses/`
- [ ] Step-up trials: ~550 data rows each (5.5 s @ 10 ms)
- [ ] Step-down trials: ~800 data rows each (8.0 s @ 10 ms)
- [ ] `step_up_fwd_*` files: RPM positive after step
- [ ] `step_up_rev_*` files: RPM negative after step
- [ ] No CSV has truncated content or stray non-numeric rows

## Quick-look spot checks (open one of each in a viewer)

- [ ] `step_up_fwd_240_run01.csv`: RPM rises from ~0 to ~225, smooth curve
- [ ] `step_up_rev_240_run01.csv`: RPM falls from ~0 to ~−235
- [ ] `step_down_fwd_240to0_run01.csv`: RPM holds ~225 then decays toward 0

## Notes

[Anything to remember when analysing or interpreting this dataset]
