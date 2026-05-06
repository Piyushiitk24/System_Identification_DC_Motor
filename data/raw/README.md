# Raw Data

Store hand-entered bench measurements here.

Raw static sweep CSV files must use this schema:

```text
pwm_cmd,direction,vmean_v,rpm,notes
```

Rules:

- `pwm_cmd` is the typed PWM magnitude, always `0..255`.
- `direction` is `fwd` or `rev`.
- `vmean_v` is the DMM average motor voltage reading.
- `rpm` is copied from firmware telemetry and keeps its natural sign.
- `notes` records deadzone, unstable DMM reading, temperature concern, or other
  bench observations.
- Do not add derived columns to raw files.

Suggested filenames:

```text
static_sweep_YYYYMMDD_runN.csv
dmm_stability_check_run01.csv
```

For Phase 1.1, prefer one combined static sweep file containing both
directions and using the `direction` column to distinguish `fwd` from `rev`.
The first completed run is:

```text
static_sweep_20260506_run1.csv
```
