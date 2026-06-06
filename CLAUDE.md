# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read This First

`AGENTS.md` is the authoritative orientation document for assistants in this repo. Read it before making non-trivial changes — it covers project state, firmware variants, data contracts, and current locked modeling conclusions. The notes below complement it; they do not replace it.

The README and `manual.md` describe the original Phase 0-1 manual workflow and are no longer the latest state. The current state is Phase 2 gap-fill after Phase 2.2 LOOCV validation, a quantified A/B/C model-selection ladder added on 2026-05-25 in `notebooks/06_model_comparison.ipynb` (Phase 2.1 grid headline + full-envelope extension across both sessions; fitted A/B/C parameters persisted in `models/model_{A,B,C}.json`), and Phase 3 closed-loop validation completed on the 2026-05-27 bench (cascade-aware vs single-LTI baseline, pre-registered comparison, 64 paired trials; `notebooks/07a_closed_loop_sim.ipynb` froze the pre-registration, `notebooks/07b_closed_loop_results.ipynb` analyses the bench data). The source of truth for the latest modeling conclusions is `thesis_notes/log.md` plus the processed CSVs in `data/processed/` and the notebooks, especially `notebooks/05_gap_fill.ipynb`, `06_model_comparison.ipynb`, and `07b_closed_loop_results.ipynb`.

For thesis-facing work, the source of truth for prose is the chapter drafts in `thesis_notes/draft_ch*.md` (the standalone model-selection draft is `thesis_notes/draft_model_selection.md`, integrated as §4.6 of `thesis/Chapters/Chapter_4/Chapter4.tex`; Chapter 6 is the Phase 3 closed-loop *results* chapter, rewritten 2026-05-27), and the cross-checked snapshot of every reported number is `thesis_notes/repo_status_2026-05-27.md` (the "status-doc"; supersedes `repo_status_2026-05-21.md`). The LaTeX is built: `thesis/main.pdf` is 91 pages (last rebuild 2026-05-27, 0 undefined refs) and includes the rewritten Phase 3 Chapter 6 (Tables 6.1–6.2, Figures 6.1–6.3 = generated `figures/23`–`25`). Figure 6.3 is the P2 zero-crossing zoom that makes the FF-discontinuity mechanism visible. The pre-registration for Phase 3 is at `data/processed/phase3_preregistration.json` (SHA-256 `da94c83d...02707669`, locked 2026-05-26 before bench day); raw per-pair data at `data/processed/closed_loop_pair_differences.csv`. See *Thesis writing layer* below before editing either.

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
pio run                            # build default open-loop firmware (src/main.cpp)
pio run -t upload                  # upload (only when hardware is connected)
pio device monitor -b 230400       # serial monitor

# Phase 3 closed-loop firmware lives in src_closedloop/ and needs the -c flag
# so it does not collide with the default src_dir:
pio run -c platformio_closedloop.ini            # build closed-loop firmware
pio run -c platformio_closedloop.ini -t upload  # upload closed-loop firmware
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

- **Active (open-loop)**: `src/main.cpp` is the Phase 2 gap-fill automated firmware, mirrored by `firmware_archive/step_response_v2.cpp`. It responds to `GO`, `STOP`, and `?`, prints a ready banner, and emits trial blocks delimited by `=== START <name> ===` / `=== END ===`. The sequence has 46 hands-off trials: 8 piggyback Phase 2.1 reruns, 20 new accel trials at PWM 180/220 across fwd/rev with 5 runs each, and 18 new decel trials from 240 to 100/180/220 across fwd/rev with 3 runs each.
- **Phase 3 closed-loop**: `src_closedloop/main.cpp`, built with `platformio_closedloop.ini` (separate `.ini` so the default `pio run` still builds `src/main.cpp` unchanged). Reuses the open-loop trial runner for CALIB/WARMUP/DRIFT modes; adds a 10 ms closed-loop control step with BASE (Model A IMC PI) and CASC (Model C IMC PI + inverse-static FF + 4 region gain sets) controllers, four compiled-in reference profiles P1-P4, and STOP active-brake. Commands: `?`, `WARMUP`, `CALIB`, `DRIFT`, `BASE`, `CASC`, `LOAD P1|P2|P3|P4`, `GAINS_BASE <Kp> <Ki>`, `GAINS_CASC <8 floats>`, `FF_FWD <n> <rpm0> <pwm0> ...`, `FF_REV ...`, `GO`, `STOP`. Closed-loop trial telemetry header is `t_ms,profile,controller,ref_rpm,meas_rpm,pwm_cmd,dir,enc_count,integrator`. The Python orchestrators are `scripts/smoke_closed_loop.py` (one-shot smoke test, Stage 1) and `scripts/bench_session.py` (full Stage-2 bench session: warm-up, CALIB, on-laptop refit, gain freeze, 64 paired trials, drift check).
- **Archived manual**: `firmware_archive/manual_mode_v1.cpp` preserves the manual-mode baseline. The user sends single-character commands (`f`/`r`/`s`/`z`/`?`) and PWM magnitudes (`0..255`) over serial. It emits continuous `t_ms,pwm_cmd,dir,enc_count,rpm` telemetry. Do not use `scripts/capture_serial.py` with manual-mode firmware.
- **Archived Phase 2.1 automation**: `firmware_archive/step_response_v1.cpp` is the automated 30-trial Phase 2.1 firmware that responds to `GO` and emits the same trial-block format used by `scripts/split_log.py`.

If you need a different protocol, swap from the archived file intentionally and keep `src/main.cpp`, `AGENTS.md`, and this file aligned.

### Shared Python package (`motor_id/`)

The Phase 3 control and simulation logic is factored out of the notebooks into an importable package so the *same code* backs the simulation, the bench orchestrator, and the results analysis:

- `cascade_sim.py` — `ModelC`/`ModelA` plant classes and the open- and closed-loop simulators (`simulate_open_loop*`, `simulate_closed_loop`).
- `controllers.py` — `PIController` (BASE) and `CascadeController` (CASC: IMC PI + inverse-static FF + region gains). These mirror the C++ in `src_closedloop/main.cpp`.
- `calibration.py` — in-session FOPDT refit: fit accel/decel CALIB trials, build a session Model A/C, and persist (`build_session_model_{A,C}`, `save_session_models`).
- `model_io.py` — load `model_{A,C}.json`, compute IMC baseline/cascade gains, build the FF table, and serialise it to `FF_FWD/FF_REV` firmware commands (`build_ff_table`, `ff_table_to_firmware_commands`).
- `metrics.py` — the pre-registered statistics: RMSE variants (windowed, deadzone, transient), settling/overshoot/ss-error, control-effort RMS, and the paired-bootstrap CI / Wilcoxon / pooled tests used by notebook 07b.

The key consequence: because notebooks `07a`/`07b` and `scripts/bench_session.py` import the *identical* controller and simulator code, a sim-vs-bench divergence (e.g. the P2 sign reversal) cannot be a controller-code mismatch — it is attributable to plant physics the simulator omits. Do not fork this logic into a notebook cell; extend the package and re-import.

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
- Phase 3 needs a fresh in-session calibration block before closed-loop trials. Do not use Phase 2.1 parameters as ground truth for a later session. (Confirmed on the 2026-05-27 bench: session Model A had `K_A=0.737, τ=155 ms, T_d=6.6 ms` vs locked `0.785 / 207 / 19.8` — reusing the locked numbers would have produced a 30 %-overdamped baseline.)
- Phase 3 closed-loop result (2026-05-27, n=8 paired per profile): cascade wins on P1 staircase (+2.83 rpm), P3 reversal (+5.22 rpm), P4 small-signal (+1.03 rpm) with 95 % CIs cleanly excluding zero; cascade *loses* on P2 slow-ramp through deadzone (−1.09 rpm), CI also excludes zero. Pre-registered "wins universally" hypothesis FAILS; **proximate** mechanism is the inverse-static FF saturation at breakaway PWM producing a slope discontinuity that hurts slow ramps (visible directly in Fig 6.3 / `figures/25_p2_zero_crossing_zoom.png` — FF jumps from 0 to ±breakaway-PWM as ref enters/leaves the deadzone band, producing a ~55 rpm reverse overshoot on P2). But the FF discontinuity alone does not explain the sim/reality sign reversal (sim predicted CASC wins P2 by +4.21 rpm using the same FF code); the missing factor is real low-speed friction physics absent from the simulator's plant — closing the gap therefore needs both a smoother FF (controller) and a richer low-speed plant model (Model D). Raw per-pair data in `data/processed/closed_loop_pair_differences.csv`. Caveat: the BASE-vs-CASC comparison cannot formally isolate FF contribution from region-gain-scheduling contribution; an ablation controller would be needed. Next concrete refinement: smoothed-FF cascade variant (re-run P2 with a smooth FF taper through deadzone).
- Model selection is now quantified (notebook 06, locked 2026-05-25): the A/B/C ladder confirms Model C wins every direction × region group. Phase 2.1 grid headline (30 trials) is overall post-step RMSE A 34.7 / B 6.96 / C 4.07 rpm (FIT% −157 / +63 / +78); the full-envelope extension (68 trials, adding gap-fill 180/220 accel and 240→100/180/220 decel) replicates A ≪ B < C independently in each session and shows Model B's transient error peaks at PWM 180–220 — the τ bathtub bottom where a single global τ is most wrong. Fitted A/B/C params are in `models/model_{A,B,C}.json`; full numerical detail is in `AGENTS.md` § *Current Model Notes*.

### Notebook conventions

Notebooks are numbered by phase: `01_static_map.ipynb` (Phase 1.1), `03_step_responses.ipynb` (Phase 2.1 FOPDT), `04_validation.ipynb` (Phase 2.2 LOOCV), `05_gap_fill.ipynb` (Phase 2 gap-fill, session drift, refined LOOCV), `06_model_comparison.ipynb` (in-sample A/B/C structural ladder on the Phase 2.1 grid plus a full-envelope extension that adds the gap-fill conditions), `07a_closed_loop_sim.ipynb` (Phase 3 simulation + frozen pre-registration), and `07b_closed_loop_results.ipynb` (Phase 3 bench results, pre-registered tests). Notebook 06's structural comparison is distinct from notebooks 04/05's LOOCV, which is the *generalisation* test, and from notebook 07b's closed-loop comparison, which is the *control-performance* test — keep all three questions separate when interpreting their numbers. When adding cells, do explicit schema checks before fitting or plotting, and keep cells runnable after a kernel restart (re-import `Path`, `glob`, `pandas`, `numpy` locally in debugging cells the user is likely to rerun in isolation).

In notebook 03, `rms_decel` is the documented 1500 ms post-step window `[3000, 4500]` ms. For apples-to-apples LOOCV comparison against the decel fit window, use `rms_total`.

When an analysis result lands, the corresponding commit should bundle the notebook, the new processed CSV, the figures, and the `thesis_notes/log.md` entry that interprets them.

### Thesis writing layer

The repo also holds the M.Tech thesis. There are three pieces, and they have different roles:

- **Chapter drafts** (`thesis_notes/draft_ch1_introduction.md` … `draft_ch7_conclusion.md`): the working prose, written in Markdown that "converts to LaTeX mechanically." Numbering is Intro = Ch1, body = Ch2–6, Conclusion = Ch7. Ch6 is the Phase 3 closed-loop **results** chapter (rewritten 2026-05-27 from the previous "plan" draft). Each draft's header block lists exactly which CSVs, figures, and status-doc sections its numbers trace to; preserve that traceability when editing.
- **Status-doc** (`thesis_notes/repo_status_2026-05-27.md`, supersedes `repo_status_2026-05-21.md`): a snapshot that pulls every reported number directly from `data/processed/*.csv` (and `data/raw/` for the static block). Its rule is *CSV wins* — where `log.md`, `AGENTS.md`, or a notebook disagrees with the CSV, the CSV is ground truth and the discrepancy is flagged. Use this to check a number before quoting it in the thesis.
- **LaTeX build** (`thesis/`): the IITK template (working copy; pristine original is in `IITK Thesis Template (LaTeX Code File)/`). Compile `thesis/main.tex` with `latexmk -pdf` (run from inside `thesis/`). The preamble is trimmed for a local BasicTeX (2025basic) install — the note in `main.tex` lists the packages removed and to restore for a full TeX Live / Overleaf build. Figures live in `thesis/Pictures/` (mirrors `figures/`). The current build (`thesis/main.pdf`, 91 pages, last rebuilt 2026-06-02, 0 undefined refs) reflects Chapters 1–7 with §4.6 *Model selection: the A/B/C ladder, quantified* (Tables 4.3–4.4, Figures 4.6–4.8 = `figures/20`–`22`) and the Phase 3 Chapter 6 results (Tables 6.1–6.2, Figures 6.1–6.3 = `figures/23`–`25`). Copy newly-generated figures from `figures/` to `thesis/Pictures/` before rebuilding when the LaTeX references them by bare name (`\graphicspath{{Pictures/}}` is set in `main.tex`).

A reported thesis number should be consistent across the draft, the status-doc, and the processed CSV it came from. If you change a modeling conclusion, the locked numbers in `AGENTS.md`, the chapter draft, and the status-doc all need to move together — do not edit one in isolation.

## Presentation deck and figure conventions (added 2026-06-02)

### Supervisor review deck (`slides/`)

A self-contained PowerPoint review deck is at `slides/cascade_review.pptx`, generated by `slides/Build.js` (Node + `pptxgenjs`). It is an 18-slide BLUF, assertion-titled deck built to *convince supervisors the work is ready to write up*; the narrative spine is "asymmetry and the only measurable session-drift both localise to the cheap L298N driver while the motor block is clean → that one-block localisation is what earns the cascade." Slide notes (`SAY:`) carry the spoken script; backup slides map anticipated questions to where each is already answered.

- Build: `cd slides && npm install && node Build.js` (writes the `.pptx` beside the script). `slides/node_modules/` is git-ignored; `package.json`/`package-lock.json` are tracked.
- Figures are embedded from `figures/` via an aspect-preserving `addFig()` helper (never stretched; very wide figures get full-width bands). The figure's pixel size is hard-coded in each `addFig(..., pxW, pxH)` call — **update it whenever the underlying figure's dimensions change**, or the fit math drifts.
- Fonts: Trebuchet MS (headings, a macOS system font) + Calibri/Consolas (body/mono, Microsoft Office fonts). PowerPoint has them; on this Mac they were copied from `/Applications/Microsoft PowerPoint.app/.../DFonts/` into `~/Library/Fonts/` so LibreOffice/Preview/Keynote render faithfully too.
- Render-check without PowerPoint: `/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to pdf --outdir /tmp/r slides/cascade_review.pptx`, then `pdftoppm -png -r 96` (poppler, `brew install poppler`) and inspect the pages. Verify embeds/aspect by unzipping the `.pptx` and checking each `<p:pic>`'s `<a:ext>` ratio against the source PNG.

### Figure-number convention

The figure *number* lives only in the caption (LaTeX `\caption{}` and the slide caption) — never baked into the image. The matplotlib generators must **not** add a `fig.suptitle("Figure N …")` banner; that produced double-numbering in both the thesis and the deck. Removed 2026-06-02 from `notebooks/06_model_comparison.ipynb` (figs 20/21/22). Thesis figure numbers for the deck's figures: `04`=Fig 3.4, `19`=Fig 5.2, `20/21/22`=Figs 4.6/4.7/4.8, `24`=Fig 6.2, `25`=Fig 6.3.

### `figures/25` (Fig 6.3) now has a generator

`figures/25_p2_zero_crossing_zoom.png` was previously a bare committed PNG with no source. It is now generated by `scripts/make_fig63_p2_zoom.py` from the bench trials (`data/raw/closed_loop_2026-05-27/closed_loop_trials/P2_pair00_{BASE,CASC}.csv`) + the session FF table (`models/closed_loop_gains_2026-05-27.json`) + `motor_id.model_io.ff_lookup_from_table`, decomposing the cascade command into FF + PI-residual. The figure makes the §6.6 mechanism visible: the FF jumps 0 → ±breakaway PWM at the deadzone edge, injecting a ~50 rpm reverse overshoot on the P2 slow ramp. Run: `./.venv/bin/python scripts/make_fig63_p2_zoom.py`.

### Figure colour code

Driver/problem = amber `#B45309`, motor/clean = teal `#0F766E` (established on the deck's cascade diagram). `figures/04_asymmetry_ratio.png` (notebook 01) was recoloured to this code (voltage-ratio amber = driver, RPM-ratio teal = motor); `scripts/make_fig63_p2_zoom.py` uses cascade = teal, baseline = grey, FF = amber.

### Regenerating figures safely

Re-running `notebooks/01` and `06` is deterministic — only the targeted figure PNGs change, and `models/model_{A,B,C}.json` plus the `data/processed/*ladder*` CSVs come back byte-identical. **Always confirm with `git status --short models/ data/processed/` after a notebook re-run; the locked numbers must not move.** After regenerating any figure, mirror it to `thesis/Pictures/` and rebuild the deck (`node Build.js`) and the thesis (`latexmk -pdf -g main.tex`).
