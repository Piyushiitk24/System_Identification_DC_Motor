# Repository Guidelines

## Project State

This repo is a DC motor system-identification project for an Arduino Uno R4
Minima, L298N driver, 12 V geared DC motor, and quadrature encoder.

The top-level README and manual still describe the original Phase 0-1 manual
workflow. The current analysis state is later:

- Phase 1.1 static map is in `notebooks/01_static_map.ipynb`.
- Phase 2.1 step-up and step-down FOPDT analysis is in
  `notebooks/03_step_responses.ipynb`.
- Phase 2.2 LOOCV validation is in `notebooks/04_validation.ipynb`.
- The running thesis narrative and conclusions live in `thesis_notes/log.md`.

Treat `thesis_notes/log.md`, processed CSVs, and notebooks as the source of
truth for the latest modeling state.

## Agent Operating Rules

This repo uses a compact Karpathy-inspired agent policy: think before editing,
keep the solution simple, make surgical changes, and verify against a concrete
goal. Merge these rules with the project-specific constraints below; do not
replace the project constraints with generic agent behavior.

- Start from evidence. Read the exact firmware, notebook, CSV, or thesis note
  before changing it. If the task could mean firmware, analysis, documentation,
  or hardware operation, state the assumption or ask before editing.
- Keep changes minimal. Do not add speculative abstractions, new workflows,
  convenience features, or alternate data layouts unless the user asked for
  them. Prefer the smallest change that preserves the current analysis state.
- Make every changed line traceable to the request. Match existing style, leave
  unrelated cleanup alone, and do not rewrite old conclusions unless the
  relevant notebook or processed CSV has been inspected or re-run.
- Define success before running. For firmware, the check is normally `pio run`.
  For analysis, re-execute the relevant notebook and inspect generated
  processed outputs/figures. For documentation-only changes, check that
  `AGENTS.md`, `CLAUDE.md`, and `thesis_notes/log.md` do not contradict each
  other.
- Respect hardware boundaries. Upload firmware, monitor serial, or depend on
  live bench behavior only when the user says hardware is connected.

## Firmware

Active firmware is `src/main.cpp`. It is manual-mode firmware:

- serial baud: `230400`
- telemetry: `t_ms,pwm_cmd,dir,enc_count,rpm`
- commands: `f`, `r`, `s`, `z`, `?`, and numeric `0..255`
- PWM output: D9 at 20 kHz using Renesas `PwmOut`
- encoder sign is currently `ENCODER_SIGN = -1`

Archived firmware is in `firmware_archive/`:

- `manual_mode_v1.cpp` preserves the manual-mode baseline.
- `step_response_v1.cpp` is the automated 30-trial Phase 2.1 firmware that
  responds to `GO` and emits trial blocks for `scripts/split_log.py`.

Do not assume `scripts/capture_serial.py` works with the active firmware. It is
for the archived `step_response_v1` protocol.

## Commands

Build active firmware:

```bash
pio run
```

Upload and monitor, only when hardware is connected:

```bash
pio run -t upload
pio device monitor -b 230400
```

Set up Python analysis:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Execute a notebook:

```bash
./.venv/bin/jupyter nbconvert --to notebook --execute notebooks/04_validation.ipynb --inplace --ExecutePreprocessor.timeout=180
```

Jupyter may need permission to bind a local kernel socket in this environment.

## Data Contracts

Raw static sweep CSV schema:

```text
pwm_cmd,direction,vmean_v,rpm,notes
```

Rules:

- `pwm_cmd` is the typed magnitude and is always nonnegative.
- `direction` is `fwd` or `rev`.
- `rpm` keeps its natural sign.
- Do not add derived columns to raw CSVs.

Phase 2.1 step-response trial CSVs live in `data/raw/step_responses/` and use:

```text
t_ms,pwm_cmd,dir,enc_count,rpm
```

For these files, `pwm_cmd` is unsigned and `dir` carries sign:

```python
dir_sign = {"F": 1, "R": -1, "N": 0}
signed_pwm = pwm_cmd * dir_sign[dir]
```

Processed outputs live in `data/processed/`. Keep processed and generated
artifacts out of `data/raw/`.

There is currently no `data/raw/_sealed/` validation dataset. Do not create or
populate it casually. Phase 2.2 uses LOOCV on the 30 Phase 2.1 trials instead
of true held-out validation.

## Current Model Notes

The working cascade model is:

```text
PWM command -> static driver voltage block -> motor dynamic block -> RPM
```

Locked Phase 2.1/2.2 interpretation:

- Static block constants: `K_fwd = 26.94 rpm/V`, `K_rev = 24.52 rpm/V`.
- Deadzone: breakaway `154/144` for fwd/rev, dropout `114/112`.
- Above-deadzone delay is about 10 ms as encoder/serial latency, though
  curve-fit delay can shift to absorb model-shape error.
- Accel and decel need separate regions in Model C.
- PWM 160 is friction-corrupted, PWM 200 is the cleanest FOPDT point, and
  PWM 240 is an effective FOPDT with visible model-shape residuals.
- Phase 2.2 LOOCV found mean excess error of about `+1.06 rpm` for accel and
  `+0.10 rpm` for decel.

Before changing these conclusions, re-run or inspect the relevant notebook and
the corresponding processed CSV.

## Analysis Workflow

When adding notebook cells:

- Prefer explicit schema checks before fitting or plotting.
- Keep raw data immutable and write generated tables to `data/processed/`.
- Write figures to `figures/` with numbered filenames.
- Append bench-session or thesis-facing conclusions to `thesis_notes/log.md`.
- If a notebook depends on prior cells, make that dependency clear. For quick
  debugging cells, import `Path`, `glob`, `pandas`, or `numpy` locally if the
  user is likely to run the cell after a kernel restart.

## Git Hygiene

- Check `git status --short` before editing.
- Do not revert user changes.
- Keep commits phase-scoped and include generated notebook outputs, processed
  CSVs, figures, and thesis log entries when they are part of the same analysis
  result.
