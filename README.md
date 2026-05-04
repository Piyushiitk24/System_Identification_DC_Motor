# DC Motor System Identification

Root-level PlatformIO project for Phase 0-1 manual characterization of a
12 V geared DC motor driven by an L298N and measured with a quadrature encoder.

## Target

- Board: Arduino Uno R4 Minima
- PlatformIO board id: `uno_r4_minima`
- Serial monitor: `230400` baud
- PWM output: D9 at 20 kHz

## Build And Monitor

```bash
pio run
pio run -t upload
pio device monitor -b 230400
```

For the Phase 1 notebook:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/jupyter notebook notebooks/01_static_map.ipynb
```

The firmware prints:

```text
t_ms,pwm_cmd,dir,enc_count,rpm
```

Manual commands:

| Command | Meaning |
|---|---|
| `f` | Set forward direction |
| `r` | Set reverse direction |
| `s` | Stop / coast |
| `z` | Zero encoder count |
| `?` | Print help |
| `0..255` | Set PWM magnitude |

## Phase 0-1 Data Workflow

1. Build and upload the firmware.
2. Run the PSU-off encoder sign check.
3. Run the PWM=150 forward/reverse DMM smoke test and record it in
   `thesis_notes/log.md`.
4. Fill `data/templates/dmm_stability_check_template.csv` for the PWM=200 DMM
   stability check.
5. Copy `data/templates/static_sweep_template.csv` to `data/raw/` for each
   sweep run and fill only measured values:

```text
pwm_cmd,direction,vmean_v,rpm,notes
```

`pwm_cmd` is always the typed magnitude from 0 to 255. `direction` is `fwd` or
`rev`. Keep derived values out of raw CSV files.
