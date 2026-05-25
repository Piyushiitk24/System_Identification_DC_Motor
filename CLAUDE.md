# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read This First

`AGENTS.md` is the authoritative orientation document for assistants in this repo. Read it before making non-trivial changes — it covers project state, firmware variants, data contracts, and current locked modeling conclusions. The notes below complement it; they do not replace it.

The README and `manual.md` describe the original Phase 0-1 manual workflow and are no longer the latest state. The current state is Phase 2 gap-fill after Phase 2.2 LOOCV validation. The source of truth for the latest modeling conclusions is `thesis_notes/log.md` plus the processed CSVs in `data/processed/` and the notebooks, especially `notebooks/05_gap_fill.ipynb`.

For thesis-facing work, the source of truth for prose is the chapter drafts in `thesis_notes/draft_ch*.md`, and the cross-checked snapshot of every reported number is `thesis_notes/repo_status_2026-05-21.md` (the "status-doc"). See *Thesis writing layer* below before editing either.

## How To Use This With An IDE Agent

Open the IDE or agent from the repository root:

```bash
cd /Users/piyush/code/System_Identification_DC_Motor
```

Keep both root instruction files in scope:

- `AGENTS.md` is the shared project policy for Codex-style agents.
- `CLAUDE.md` is the Claude Code project memory and should stay consistent
  with `AGENTS.md`.

For Claude Code, keep this file at the repo root so it is loaded as project
context. For other IDE assistants, add both `AGENTS.md` and `CLAUDE.md` as
project rules or explicitly attach/read them at the start of a session. The
useful pattern is not copying a generic template; it is keeping a short
behavior policy next to exact project facts, commands, data contracts, and
current modeling conclusions.

## Agent Behavior Policy

Use this Karpathy-inspired operating loop for non-trivial tasks:

1. Think before editing. Read the relevant firmware, notebook, CSV, or thesis
   note first. State assumptions when the request is ambiguous, especially when
   it could affect live hardware, raw data, or locked modeling conclusions.
2. Prefer the simplest working change. Do not add unrequested features,
   alternate workflows, configurable layers, or new data schemas. This is a
   measured system-identification project, so extra cleverness usually creates
   traceability problems.
3. Keep diffs surgical. Every changed line should map to the user's request.
   Match the surrounding style, leave unrelated cleanup alone, and remove only
   dead code or artifacts introduced by the current change.
4. Verify against a concrete goal. Firmware changes normally need `pio run`.
   Notebook changes need the relevant `nbconvert` execution and inspection of
   generated outputs. Documentation changes need consistency across
   `AGENTS.md`, `CLAUDE.md`, and `thesis_notes/log.md` when conclusions are
   involved.

Stop and ask before uploading firmware, opening a serial monitor as part of a
bench run, inventing a held-out validation dataset, or changing locked model
numbers without inspecting the corresponding notebook and processed CSV.

## Common Commands

Firmware (PlatformIO, Arduino Uno R4 Minima):

```bash
pio run                            # build
pio run -t upload                  # upload (only when hardware is connected)
pio device monitor -b 230400       # serial monitor
```

Python analysis environment:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Run a notebook headlessly (re-execute and overwrite outputs in place):

```bash
./.venv/bin/jupyter nbconvert --to notebook --execute \
    notebooks/05_gap_fill.ipynb --inplace --ExecutePreprocessor.timeout=180
```

Capture and split a GO-based automated step-response run (only when hardware is connected and the matching automated firmware is flashed):

```bash
python scripts/capture_serial.py <port> \
    data/raw/serial_logs/<session>.log
python scripts/split_log.py \
    data/raw/serial_logs/<session>.log \
    data/raw/step_responses_gapfill/
```

Split a captured original Phase 2.1 step-response serial log:

```bash
python scripts/split_log.py \
    data/raw/serial_logs/<session>.log \
    data/raw/step_responses/
```

There is no test suite. There is no linter configured. "Build" means `pio run`; "validate analysis" means re-executing the relevant notebook and checking the generated processed CSVs/figures.

## Architecture

This is a hardware-in-the-loop system-identification project, not a software product. The pipeline is:

```
firmware on Arduino  →  serial CSV telemetry  →  raw CSV in data/raw/  →
notebook analysis  →  processed CSVs + figures + thesis log entries
```

Physical setup: Arduino Uno R4 Minima drives an L298N H-bridge driving a 12 V geared DC motor. A 600 PPR quadrature encoder (4× decoded → 2400 counts/rev) feeds back via D2/D3 interrupts. PWM speed command is on D9 at 20 kHz (set via the Renesas `PwmOut` API — the Uno R4 PlatformIO core does not expose `analogWriteFrequency`). Direction is set via D4/D5 to L298N IN1/IN2. See `PIN_CONFIGURATION.md` for the full wiring map and required L298N jumper state.

### Firmware variants

There are three firmware behaviours, and they are not interchangeable:

- **Active**: `src/main.cpp` is the Phase 2 gap-fill automated firmware, mirrored by `firmware_archive/step_response_v2.cpp`. It responds to `GO`, `STOP`, and `?`, prints a ready banner, and emits trial blocks delimited by `=== START <name> ===` / `=== END ===`. The sequence has 46 hands-off trials: 8 piggyback Phase 2.1 reruns, 20 new accel trials at PWM 180/220 across fwd/rev with 5 runs each, and 18 new decel trials from 240 to 100/180/220 across fwd/rev with 3 runs each.
- **Archived manual**: `firmware_archive/manual_mode_v1.cpp` preserves the manual-mode baseline. The user sends single-character commands (`f`/`r`/`s`/`z`/`?`) and PWM magnitudes (`0..255`) over serial. It emits continuous `t_ms,pwm_cmd,dir,enc_count,rpm` telemetry. Do not use `scripts/capture_serial.py` with manual-mode firmware.
- **Archived Phase 2.1 automation**: `firmware_archive/step_response_v1.cpp` is the automated 30-trial Phase 2.1 firmware that responds to `GO` and emits the same trial-block format used by `scripts/split_log.py`.

If you need a different protocol, swap from the archived file intentionally and keep `src/main.cpp`, `AGENTS.md`, and this file aligned.

### Data contracts (raw CSVs)

These contracts matter because notebooks fail or silently mis-fit if they are violated:

- **Static sweep** (`data/raw/static_sweep_*.csv`): `pwm_cmd,direction,vmean_v,rpm,notes`. `pwm_cmd` is the *typed magnitude* and is always nonnegative; `direction` is `fwd` or `rev`; `rpm` carries its natural sign from telemetry.
- **Step responses** (`data/raw/step_responses/*.csv`): `t_ms,pwm_cmd,dir,enc_count,rpm`. Here `pwm_cmd` is unsigned and `dir` carries sign, with `dir_sign = {"F": 1, "R": -1, "N": 0}`.
- **Gap-fill step responses** (`data/raw/step_responses_gapfill/*.csv`): same schema and sign convention as Phase 2.1 step-response CSVs.

Raw data is immutable. Do not add derived columns to raw CSVs. All computed outputs go in `data/processed/`. Figures go in `figures/` with numbered filenames.

There is intentionally no `data/raw/_sealed/` held-out validation dataset. Phase 2.2 uses LOOCV across the existing 30 Phase 2.1 trials, and the gap-fill analysis uses within-condition LOOCV on the new 180/220 accel and 240-to-100/180/220 decel conditions. Do not invent a sealed dataset.

### Working model

The locked cascade is `PWM command → static driver-voltage block → motor dynamic block → RPM` with separate fwd/rev parameters and separate accel/decel regions. Specific locked numbers (static gains, deadzone breakaway/dropout, FOPDT picks, LOOCV residuals) are documented in `AGENTS.md` § *Current Model Notes*. Before changing any of those conclusions, re-run or inspect the corresponding notebook and processed CSV — do not edit the documented numbers in isolation.

Latest Phase 2 gap-fill conclusions:

- Within-session reproducibility is strong after warm-up: gap-fill LOOCV excess is about `-0.05 rpm` for accel and `+0.45 rpm` for decel, with reverse `240->100` decel as the main outlier at about `+1.06 rpm`.
- Session-to-session drift is real after the two-week idle: cold-start forward accel tau inflated roughly 30-40% for the first about 30 s, low-rpm decel through the deadzone is much slower than Phase 2.1 interpolation, and reverse high-PWM tau is persistently about 20% faster than Phase 2.1.
- The tau landscape is now a broad bathtub, not a sharp V: accel tau is low across roughly PWM 180-220 and rises near PWM 160 and PWM 240.
- Phase 3 needs a fresh in-session calibration block before closed-loop trials. Do not use Phase 2.1 parameters as ground truth for a later session.

### Notebook conventions

Notebooks are numbered by phase: `01_static_map.ipynb` (Phase 1.1), `03_step_responses.ipynb` (Phase 2.1 FOPDT), `04_validation.ipynb` (Phase 2.2 LOOCV), and `05_gap_fill.ipynb` (Phase 2 gap-fill, session drift, refined LOOCV). When adding cells, do explicit schema checks before fitting or plotting, and keep cells runnable after a kernel restart (re-import `Path`, `glob`, `pandas`, `numpy` locally in debugging cells the user is likely to rerun in isolation).

In notebook 03, `rms_decel` is the documented 1500 ms post-step window `[3000, 4500]` ms. For apples-to-apples LOOCV comparison against the decel fit window, use `rms_total`.

When an analysis result lands, the corresponding commit should bundle the notebook, the new processed CSV, the figures, and the `thesis_notes/log.md` entry that interprets them.

### Thesis writing layer

The repo also holds the M.Tech thesis. There are three pieces, and they have different roles:

- **Chapter drafts** (`thesis_notes/draft_ch1_introduction.md` … `draft_ch7_conclusion.md`): the working prose, written in Markdown that "converts to LaTeX mechanically." Numbering is Intro = Ch1, body = Ch2–6, Conclusion = Ch7 (Ch6 closed-loop is forward-looking — Phase 3 is not yet run). Each draft's header block lists exactly which CSVs, figures, and status-doc sections its numbers trace to; preserve that traceability when editing.
- **Status-doc** (`thesis_notes/repo_status_2026-05-21.md`): a snapshot that pulls every reported number directly from `data/processed/*.csv` (and `data/raw/` for the static block). Its rule is *CSV wins* — where `log.md`, `AGENTS.md`, or a notebook disagrees with the CSV, the CSV is ground truth and the discrepancy is flagged. Use this to check a number before quoting it in the thesis.
- **LaTeX build** (`thesis/`): the IITK template (working copy; pristine original is in `IITK Thesis Template (LaTeX Code File)/`). Compile `thesis/main.tex` with `latexmk`. The preamble is trimmed for a local BasicTeX (2025basic) install — the note in `main.tex` lists the packages removed and to restore for a full TeX Live / Overleaf build. Figures live in `thesis/Pictures/` (mirrors `figures/`).

A reported thesis number should be consistent across the draft, the status-doc, and the processed CSV it came from. If you change a modeling conclusion, the locked numbers in `AGENTS.md`, the chapter draft, and the status-doc all need to move together — do not edit one in isolation.
