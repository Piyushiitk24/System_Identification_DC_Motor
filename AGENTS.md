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
- Phase 2 gap-fill, session-to-session drift analysis, and refined LOOCV
  comparison are in `notebooks/05_gap_fill.ipynb`.
- The running thesis narrative and conclusions live in `thesis_notes/log.md`.
- Thesis chapter drafts live in `thesis_notes/draft_ch*.md`; use
  `thesis_notes/repo_status_2026-05-21.md` as the cross-checked snapshot of
  reported thesis numbers before editing prose.

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

Active firmware is `src/main.cpp`. In this checkout it is the Phase 2 gap-fill
automated step-response firmware, equivalent to
`firmware_archive/step_response_v2.cpp`:

- serial baud: `230400`
- telemetry: `t_ms,pwm_cmd,dir,enc_count,rpm`
- commands: `GO`, `STOP`, and `?`
- PWM output: D9 at 20 kHz using Renesas `PwmOut`
- encoder sign is currently `ENCODER_SIGN = -1`
- trial sequence: 46 hands-off trials, about 7.3-7.5 min total:
  8 piggyback Phase 2.1 reruns, 20 new accel trials at PWM 180/220
  across fwd/rev with 5 runs each, and 18 new decel trials from 240 to
  100/180/220 across fwd/rev with 3 runs each

Archived firmware is in `firmware_archive/`:

- `manual_mode_v1.cpp` preserves the manual-mode baseline.
- `step_response_v1.cpp` is the automated 30-trial Phase 2.1 firmware that
  responds to `GO` and emits trial blocks for `scripts/split_log.py`.
- `step_response_v2.cpp` is the automated 46-trial Phase 2 gap-fill firmware
  now mirrored in `src/main.cpp`.

`scripts/capture_serial.py` is for GO-based automated firmware
(`step_response_v1` or `step_response_v2`) and sends `GO` after startup. Do
not use it against manual-mode firmware. `scripts/split_log.py` works for
both v1 and v2 trial-block logs; choose the correct output directory.

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
./.venv/bin/jupyter nbconvert --to notebook --execute notebooks/05_gap_fill.ipynb --inplace --ExecutePreprocessor.timeout=180
```

Jupyter may need permission to bind a local kernel socket in this environment.

Compile the thesis draft:

```bash
cd thesis
latexmk -pdf main.tex
```

Capture an automated GO-based step-response run, only when hardware is
connected and the matching automated firmware is flashed:

```bash
python scripts/capture_serial.py <port> data/raw/serial_logs/<session>.log
python scripts/split_log.py data/raw/serial_logs/<session>.log data/raw/step_responses_gapfill/
```

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

Step-response trial CSVs live in:

- `data/raw/step_responses/` for the original 30-trial Phase 2.1 session.
- `data/raw/step_responses_gapfill/` for the 46-trial Phase 2 gap-fill
  session.

Both directories use:

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

Current Phase 2 gap-fill processed outputs include:

- `phase2gapfill_fopdt_accel_per_trial.csv`
- `phase2gapfill_fopdt_accel_per_condition.csv`
- `phase2gapfill_stepdown_per_trial.csv`
- `phase2gapfill_stepdown_per_condition.csv`
- `phase2gapfill_loocv_accel.csv`
- `phase2gapfill_loocv_decel.csv`
- `phase2gapfill_loocv_summary_combined.csv`

There is currently no `data/raw/_sealed/` validation dataset. Do not create or
populate it casually. Phase 2.2 uses LOOCV on the 30 Phase 2.1 trials, and
the gap-fill analysis uses within-condition LOOCV on the new 180/220 accel
and 240-to-100/180/220 decel conditions.

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

Latest Phase 2 gap-fill interpretation:

- Within-session reproducibility is strong when the motor is warm. Gap-fill
  LOOCV excess is about `-0.05 rpm` for accel and `+0.45 rpm` for decel, with
  the main outlier being reverse `240->100` decel at about `+1.06 rpm`.
- Session-to-session drift after the two-week idle period is real and
  structured. Cold-start forward accel tau inflated roughly 30-40% during the
  first about 30 s, low-rpm decel through the deadzone is much slower than
  Phase 2.1 interpolation, and reverse high-PWM tau is persistently about 20%
  faster than Phase 2.1.
- The cascade structure remains supported. `K_ss` stays highly linear in PWM
  within each direction across PWM 160/180/200/220/240, while tau carries the
  operating-region and session-history effects.
- The old sharp "V-shape" tau description should be refined to a broad
  bathtub: accel tau is low across roughly PWM 180-220 and rises near PWM 160
  and PWM 240.
- Phase 3 should not treat Phase 2.1 parameters as ground truth for a later
  bench session. The Phase 3 protocol needs a fresh in-session calibration
  block before closed-loop trials, then should use that same-session
  calibration for simulator predictions.

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
- In notebook 03, `rms_decel` is the documented 1500 ms post-step window
  `[3000, 4500]` ms. For apples-to-apples LOOCV comparison against the decel
  fit window, use `rms_total`.

## Thesis Writing Layer

This repo also holds the M.Tech thesis. Keep thesis-facing prose traceable to
the data and status snapshot:

- Chapter drafts are `thesis_notes/draft_ch1_introduction.md` through
  `thesis_notes/draft_ch7_conclusion.md`. They are Markdown drafts intended to
  convert mechanically to LaTeX. Chapter 6 is a forward-looking closed-loop
  plan; Phase 3 has not been run.
- `thesis_notes/repo_status_2026-05-21.md` is the status-doc: a cross-checked
  snapshot of reported numbers pulled from `data/processed/*.csv` and the raw
  static/deadzone CSVs. For a thesis number, CSV wins over prose.
- The LaTeX working copy is in `thesis/`; the pristine IITK template copy is in
  `IITK Thesis Template (LaTeX Code File)/`. Thesis figures live in
  `thesis/Pictures/` and mirror the generated figures where needed.
- Before changing a reported conclusion, inspect or re-run the relevant
  notebook and processed CSV, then keep the chapter draft, status-doc,
  `AGENTS.md`, and `thesis_notes/log.md` consistent. Do not edit one of those
  artifacts in isolation when the underlying model meaning changes.

## Git Hygiene

- Check `git status --short` before editing.
- Do not revert user changes.
- Keep commits phase-scoped and include generated notebook outputs, processed
  CSVs, figures, and thesis log entries when they are part of the same analysis
  result.
