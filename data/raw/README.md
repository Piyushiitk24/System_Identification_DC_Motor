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
static_sweep_fwd_run01.csv
static_sweep_rev_run01.csv
dmm_stability_check_run01.csv
```
