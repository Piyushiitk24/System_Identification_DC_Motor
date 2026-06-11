# Lab Log

Append one entry for every bench session. Keep raw observations here even if
they look unimportant at the time.

## 2026-05-04 - Phase 0 acceptance

- PSU setting: ___ V, current limit ___ A
- Board: Arduino Uno R4 Minima
- Firmware build: `pio run` passed: yes / no
- PWM frequency command: 20 kHz
- DMM: __________________

Single-point DMM check:

| Direction | PWM | DMM Vmean (V) | RPM from serial | Notes |
|---|---:|---:|---:|---|
| fwd | 150 |  |  |  |
| rev | 150 |  |  |  |

Decision:

- Ready for Day 2 sweep: yes / no
- Notes:

## 2026-05-06 - Phase 0 oscilloscope single-point check

- PSU voltage display: 12 V
- Motor supply current: 0.21-0.22 A
- Scope setup: CH1 on L298N OUT1 to common ground, CH2 on L298N OUT2 to common ground
- Math channel: CH1 - CH2, used as average motor voltage
- Firmware state during this run: pre-fix encoder sign, `ENCODER_SIGN = 1`

Single-point scope check:

| Command | PWM | CH1 Mean (V) | CH2 Mean (V) | MATH Mean (V) | RPM from serial | PSU current (A) | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| fwd | 150 | 7.66-7.77 | 5.37-5.76 | 1.74-2.10 | -57.75 to -59.00 | 0.22 | Motor voltage polarity positive, RPM sign negative |
| rev | 150 | 5.75-5.80 | 8.27-8.48 | -2.48 to -3.00 | 55.75 to 61.00 | 0.21 | Motor voltage polarity negative, RPM sign positive |

Diagnosis:

- Voltage polarity is consistent: forward command gives positive CH1-CH2 motor voltage, reverse command gives negative CH1-CH2 motor voltage.
- Encoder sign was reversed relative to the command convention.
- Firmware updated after this run: `ENCODER_SIGN` changed from `1` to `-1` in `src/main.cpp`.
- `pio run` passed after the firmware sign change.

Decision:

- Not ready for full static sweep until the PWM=150 gate is repeated after uploading the fixed firmware.

## 2026-05-06 - Phase 1.1 static sweep ingestion

- Raw data file added: `data/raw/static_sweep_20260506_run1.csv`
- Source file copied from: `/Users/piyush/Downloads/static_sweep_20260506_run1.csv`
- File format: single combined forward/reverse CSV with `direction` column
- Schema: `pwm_cmd,direction,vmean_v,rpm,notes`
- Row count: 52 total rows
- Direction counts: 26 `fwd`, 26 `rev`
- PWM range: 10 to 255 for both directions
- Measured fields retained in raw data: PWM command, direction, motor average voltage, steady RPM, and notes with CH1/CH2/math/current details
- Confirmed deadzone boundary used for first analysis notebook: +/-130 PWM

Work completed:

- Replaced generic static-map notebook with dataset-specific `notebooks/01_static_map.ipynb`.
- Notebook outputs four figures under `figures/`.
- Derived slopes and asymmetry ratios remain in notebook outputs, not in the raw CSV.

## 2026-05-07 - Phase 1.1 static-map interpretation

Headline finding from Plot 3:

- Static-block-only asymmetry hypothesis confirmed by Phase 1.1 sweep: V-to-RPM gain is symmetric within about 9% across direction.
- Forward motor gain: `K_fwd = 26.94 rpm/V`.
- Reverse motor gain magnitude: `K_rev = 24.52 rpm/V` (`K_rev` is negative when signed).
- The large directional asymmetry appears mainly in the PWM-to-voltage map, not in the voltage-to-RPM map.

Interpretation:

- Reverse produces about 7% more delivered motor voltage at high PWM and more than 2x the forward voltage at some low PWM points.
- Once delivered motor voltage is used as the input, forward and reverse RPM gains are close.
- This supports the cascade decomposition: the static driver block captures L298N voltage asymmetry, while the motor dynamic block is approximately direction-symmetric.
- Physical explanation: the DC motor is nearly electromagnetically symmetric, while the L298N output stages are not because different switch paths have different saturation drops.

Thesis note:

- This is a defensible result for using a cascaded structure: `PWM command -> driver/static voltage block -> motor dynamic block`.

## 2026-05-06 - Deadzone hysteresis

Phase 1.2 complete via manual ramp.

- Multiple manual ramp runs in both directions show breakaway PWM approximately 150: fwd 154, rev 144.
- Dropout PWM approximately 113: fwd 114, rev 112.
- Hysteresis band is about 32-40 PWM wide.
- Phase 1.1 staircase sweep showed breakaway at PWM=130 because the staircase steps deliver enough torque for kinetic motion above dropout but caught a stochastic breakaway.
- True breakaway is higher and stochastic.
- Model implication: deadzone block must include hysteresis.
- Phase 1.2 closed; data saved in `data/raw/deadzone_manual_run01.csv`.

## 2026-05-06 evening - Phase 2.1 complete; Phase 1.1 expanded to 3 runs

Phase 2.1 step-response data captured under `step_response_v1` firmware. 30 trials: 9 step-ups x 3 PWM levels (160, 200, 240) x 2 directions, plus 12 step-downs (240->0 and 240->160 x 2 directions x 3 runs). Ambient temp ___ deg C, PSU 12.0 V. Serial log at `data/raw/serial_logs/2026-05-06_phase21_session.log`, split CSVs at `data/raw/step_responses/`. Session metadata at `data/metadata/2026-05-07_phase21_session.md`. Firmware archived at `firmware_archive/step_response_v1.cpp`.

Phase 1.1 run02 and run03 also collected with manual-mode firmware (archived at `firmware_archive/manual_mode_v1.cpp`). Same ambient conditions as morning's run01. Reproducibility data secured before next session, per concern about driver behaviour drift across days.

2026-05-06 evening — Phase 1.1 reproducibility validated via spot-check + Phase 2.1 implicit cross-validation.
Decision: full Phase 1.1 repeats deferred. Validation strategy adopted instead:

Phase 1.2 manual ramp (multiple passes) validates the deadzone region.
Phase 2.1 step-up steady-state values (last 1 s of each trial) will validate the above-deadzone region in 18 implicit data points; comparison to be done in notebooks/03_step_responses.ipynb.
Two-point spot-check at PWM=±255 collected this evening (data at data/raw/spot_check_max_pwm_2026-05-06_evening.csv).

Spot-check results (run01 → evening, at PWM=±255):
V_motor driftRPM driftPSU current driftForward−3.8%−0.6%−4.5%Reverse+1.9% (mag)+0.8% (mag)−8.7%
Interpretation: Motor (V→RPM block) is reproducible to <1% across the session. Driver (PWM→V block) drifts ~2–4% in V_motor and ~5–9% in PSU current — consistent with L298N junction thermal drift after extended operation. This drift pattern empirically supports the cascade decomposition: instability is isolated in the driver-side static block; the motor-side dynamic block is stable. The session-bounded data-collection methodology is justified. Static-block parameters fit from this dataset are valid only at this session's ambient/thermal condition; this caveat to be stated in the thesis.

## 2026-05-07 — Phase 2.1 implicit cross-validation (notebook 03 cells 1-6)

Compared steady-state RPM from step-up trials (mean of t in [4500, 5500] ms,
3 runs per condition) against run01 static sweep at PWM ∈ {160, 200, 240} ×
{fwd, rev}.

Results:
  PWM=160 fwd: -25.2%   PWM=160 rev: -11.1%   (below linear regime — see below)
  PWM=200 fwd:  -5.1%   PWM=200 rev:  -2.3%
  PWM=240 fwd:  -5.6%   PWM=240 rev:  -1.0%

Interpretation:
1. PWM=160 dropped from validation set. Linear fit K_fwd=26.94 already
   underpredicts sweep RPM at this PWM by 19% (predicts 59, sweep shows 70),
   so the through-origin linear static map does not apply this close to
   breakaway. Confirms static block nonlinearity in the deadzone region —
   already characterised in Phase 1.2.

2. PWM=200, 240 fwd disagreement (~5%) consistent with L298N thermal drift.
   Spot-check at PWM=255 fwd showed v_motor -3.8% morning→evening; with
   K_fwd=27 rpm/V, this projects to roughly 5% RPM drop on cumulatively
   warmed driver. Sweep was earlier in the session than the step trials.

3. PWM=200, 240 rev disagreement (~1-2%) within noise. Consistent with
   spot-check showing reverse is more thermally stable (+0.8% mag RPM drift).

Cross-val gate: passed with caveats. Linear regime (PWM ≥ 200) agrees within
thermal-drift bounds, with fwd-vs-rev asymmetry matching spot-check pattern.
Cascade decomposition further supported: the disagreement signature lives
exactly where thermal/nonlinear effects are predicted (static block), and
fwd-vs-rev asymmetry in the disagreement matches the asymmetry in v_motor
thermal response.

## 2026-05-07 — Phase 2.1 FOPDT heuristic fit (notebook 03 cells 7–13)

Fitted FOPDT (K_ss, Td, tau) to all 18 step-up trials using a 63.2% rise
heuristic. All fits succeeded.

Per-condition aggregates (mean ± std, n=3):

  fwd 160:  K = 52.4±3.1   Td = 20±17   tau = 167±23   [friction-dominated]
  fwd 200:  K =123.9±1.3   Td = 10±0    tau =  97±6
  fwd 240:  K =210.5±4.7   Td = 10±0    tau = 173±6
  rev 160:  K =-69.8±1.8   Td = 17±12   tau = 170±26   [friction-dominated]
  rev 200:  K=-131.8±0.7   Td = 10±0    tau =  90±0
  rev 240:  K=-222.7±2.5   Td = 10±0    tau = 170±10

Findings:

(1) τ is operating-point dependent. PWM=200 → PWM=240: τ rises from
    ~95 ms to ~170 ms (80% increase). Error bars non-overlapping.
    Model B (single global τ) is misspecified. Model C (region-dependent
    dynamics) is justified.

(2) Dynamic block is direction-symmetric. τ_fwd ≈ τ_rev within std at
    every PWM. This confirms the cascade decomposition: asymmetry lives
    in the static block, not the motor.

(3) Td above deadzone = 10 ms exactly (std=0 across 12 trials at
    PWM=200,240). Operating-point invariant, direction-invariant.
    Identified as encoder + serial sample latency.

(4) τ shows a V-shape with minimum at PWM=200. Slow at PWM=160 due to
    friction; slow at PWM=240 cause TBD — either non-first-order
    dynamics or back-EMF/saturation effects. Will be diagnosed by
    curve_fit residuals (next step).

Caveat: τ values from a 63.2% rise heuristic, which assumes first-order
response. Promotion to scipy.curve_fit with residual analysis is the
next step before declaring Model C parameters final.

## 2026-05-07 — Phase 2.1 FOPDT curve_fit promotion (notebook 03 cells 14–17)

Promoted FOPDT fits from 63.2% heuristic to scipy.curve_fit on all 18
step-up trials. All fits succeeded. Per-condition aggregates:

  fwd 160:  K=  52.1   Td= 0.0     tau= 200.1±22.0   rms_rise= 2.61
  fwd 200:  K= 123.5   Td= 4.9±0.9 tau=  95.1± 4.6   rms_rise= 2.48
  fwd 240:  K= 209.7   Td=17.1±0.7 tau= 152.3± 2.7   rms_rise= 4.69
  rev 160:  K= -69.6   Td= 0.0     tau= 191.7±12.2   rms_rise= 4.03
  rev 200:  K=-131.4   Td= 5.6±0.3 tau=  81.2± 0.9   rms_rise= 2.66
  rev 240:  K=-222.6   Td=23.5±0.6 tau= 144.4± 2.5   rms_rise= 7.17

Findings:

(1) V-shape in τ confirmed by curve_fit. τ minimum at PWM=200 (~88 ms
    averaging fwd/rev), τ rises at both PWM=160 (~196 ms) and PWM=240
    (~148 ms). Consistent across heuristic and curve_fit methods.

(2) Td shows operating-point dependence in curve_fit (0 / 5 / 20 ms at
    PWM 160/200/240) — opposite to the heuristic's claim of constant
    10 ms. Interpretation: this is NOT physical encoder latency; it is
    the FOPDT model compensating for non-first-order rise shape at the
    PWM extremes. The "real" Td is the heuristic's first-non-zero-RPM
    value (~10 ms), which curve_fit shifts to absorb model-shape error.

(3) Residual structure confirms FOPDT is well-specified at PWM=200
    (random ±2–3 rpm scatter) and increasingly mis-specified at
    PWM=160 (friction-onset structure) and PWM=240 (smooth-onset
    structure during rise). RMS rise residual climbs from 2.5 rpm
    (PWM=200) to 7.2 rpm (rev PWM=240).

(4) Direction symmetry of dynamic block holds at PWM=160 and PWM=240
    within std. Small 14 ms gap at PWM=200 (fwd 95 vs rev 81) is
    statistically significant and worth a thesis caveat — possible
    static/dynamic block coupling or motor commutation asymmetry —
    but does not invalidate the cascade decomposition.

Model C accepted as the working model:
  - PWM=200 is the canonical linear-regime operating point
    (FOPDT clean, τ ≈ 88 ms, Td ≈ 5 ms)
  - PWM=240 parameters are effective FOPDT, not true LTI
    (motivates higher-order dynamic block extension)
  - PWM=160 parameters are friction-corrupted
    (motivates Stribeck/Coulomb extension in Model D)

Outstanding questions to address with step-down trials (12 reserved):
  - Does decel dynamics match accel dynamics? (Model B/C
    region structure depends on this)
  - Does breakaway-vs-dropout hysteresis show up dynamically?

## 2026-05-07 — Phase 2.1 step-down analysis + synthesis (notebook 03 cells 18–25)

Fitted FOPDT decay model to all 12 step-down trials using a fit window
restricted to t >= 2000 ms (exclude pre-step ramp). All fits succeeded.

Per-condition aggregates (n=3):

  fwd 240→0:   y_init=214.3   y_final= -0.7   Td=55.2±2.0   tau=172.2± 1.8
  fwd 240→160: y_init=215.7   y_final= 73.75  Td=14.1±5.2   tau=275.3± 8.8
  rev 240→0:   y_init=-229.1  y_final= -0.0   Td=62.9±3.9   tau=189.5± 3.9
  rev 240→160: y_init=-231.7  y_final=-85.66  Td=10.0±0.4   tau=306.4± 4.0

Findings:

(1) Decel τ > accel τ in the same operating range. fwd 240→160 decel
    τ=275 ms is larger than any accel τ in 200–240 PWM range (95–152).
    Accel/decel asymmetry justifies *_accel vs *_decel region split
    in Model C.

(2) Decel-to-160 (~290 ms) slower than decel-to-0 (~180 ms). Likely
    L298N PWM-chopping prevents regenerative braking at PWM=160 that
    pure coast (PWM=0) provides.

(3) Direction asymmetry pattern OPPOSITE in accel vs decel:
    - accel: rev faster (15% gap at PWM=200)
    - decel: rev slower (11% gap at 240→160)
    Symmetric magnitude, opposite direction. Indicates partial coupling
    between static and dynamic blocks; cascade decomposition holds
    but is not perfectly clean. Thesis caveat.

(4) SS hysteresis at PWM=160 confirmed in both directions:
    - fwd: 73.75 (from above) vs 52.4 (from below) → 40% gap
    - rev: -85.66 (from above) vs -69.75 (from below) → 23% gap
    Bigger gap in fwd matches bigger fwd breakaway (Phase 1.2).
    Stribeck/Coulomb extension (Model D) empirically motivated.

(5) y_final at 240→0 ≈ 0 in both directions (-0.69 fwd, -0.00 rev).
    Motor coasts cleanly to rest. FOPDT τ for coast (172/190 ms) is
    an effective parameter — model is technically misspecified
    (Coulomb-dominated friction is not first-order) but residuals
    remain well-bounded.

Phase 2.1 complete. Locked-in Model C parameter set:

  Static block:    K_fwd=26.94 rpm/V, K_rev=24.52 rpm/V (from 01)
  Deadzone:        breakaway 154/144, dropout 114/112 (Phase 1.2)
                   SS hysteresis at PWM=160: ~21 rpm fwd, ~16 rpm rev
  Td (above DZ):   ~10 ms (encoder/serial latency)
  Accel τ:         PWM=200: 95/81 ms (fwd/rev) — clean FOPDT
                   PWM=240: 152/144 ms — FOPDT misspecified, effective
                   PWM=160: 200/192 ms — friction-corrupted
  Decel τ:         240→160: 275/306 ms (fwd/rev)
                   240→0:   172/190 ms (fwd/rev)

Outstanding gaps for future work:
  - Step-ups from PWM<150 (below breakaway) — breakaway dynamics
  - Step-downs to PWM other than {0, 160} — decel τ as function of
    target PWM
  - Step-ups to PWM=255 — extend top of operating range

## 2026-05-07 — Phase 2.2 LOOCV validation

**Notebook**: `notebooks/04_validation.ipynb` (cells 1–6f)

### Context

Original handover specified held-out validation against `data/raw/_sealed/`. Inventory probe (cell 5a) revealed the sealed directory does not exist on disk; `.gitignore` contains no entry for it either. **No truly held-out data exists.** Pivoted to leave-one-out cross-validation (LOOCV) on the 30 Phase 2.1 calibration trials.

### Methodology

For each of the 30 trials, predict the held-out trial using the **mean of per-trial fit parameters from the other 2 runs at the same condition**.

- Per-trial params from `phase21_fopdt_curvefit_per_trial.csv` (18 accel) and `phase21_stepdown_curvefit_per_trial.csv` (12 decel).
- `simulate_model_C` extended with optional `override_params` argument (cell 6b) to inject LOOCV-mean parameters per trial.
- Sanity-checked: with `override_params` equal to the per-condition lookup, output is bit-for-bit identical (`max_diff = 0.0e+00`).
- Residual windows aligned with curve_fit's optimization to enable apples-to-apples comparison:
  - **Accel**: rise window `[STEP, STEP + 5τ]` → compared to per-trial `rms_rise`
  - **Decel**: fit window `[2000, end]` → compared to per-trial `rms_total`
- **Note on `rms_decel`**: per-trial decel CSV has both `rms_decel` and `rms_total`. Diagnostic (cell 6d-followup) confirmed `rms_total = residual on [2000, end]` exactly; `rms_decel` uses an undocumented window (~150 samples post-step, doesn't match natural τ multiples). Adopted `rms_total` as the comparison floor since it's principled (matches curve_fit's actual fit window). `rms_decel` definition is recoverable from notebook 03 if ever needed.

### Schema notes (future self)

- Trial CSV: `pwm_cmd` is **unsigned**; `dir` is string `{'F','R','N'}`. Construct signed PWM via `pwm_cmd * dir_sign` with `dir_sign = {'F':1,'R':-1,'N':0}`.
- Per-trial fit table uses `Td_ms`, `tau_ms`; per-condition table uses `Td_mean`, `tau_mean`. Map at lookup.

### Headline results

- **Accel mean LOOCV excess: +1.06 rpm** (std 0.80, n=6 conditions)
- **Decel mean LOOCV excess: +0.10 rpm** (std 0.10, n=4 conditions)
- **Decel is ~10× more reproducible than accel.**
- Worst condition: `accel fwd PWM=160`, excess +1.97 rpm (run01 friction-onset outlier)
- All 30 trial-level RMSE values consistent with per-trial fit residuals on the apples-to-apples comparison.

### New finding: accel/decel reproducibility asymmetry

Decel parameters transfer between runs within a condition far more cleanly than accel parameters. **Physical hypothesis**: by the time decel begins, the motor has been running at PWM=240 SS for 3000 ms — thermally settled, friction stable, pole position randomized over many revolutions. Accel from rest catches the motor cold with stochastic friction breakaway and unknown rotor pole alignment. This effect was invisible in Phase 2.1's per-condition fits (which average across runs) but is exposed cleanly by LOOCV.

This is a thesis observation worth foregrounding in the validation chapter alongside the existing accel-vs-decel τ asymmetry from Phase 2.1.

### Anomalies

- **`rev PWM=200 run3`**: LOOCV `rmse_rise = 2.28` *below* per-trial `rms_rise = 3.24`. Cause: run3 has anomalously noisy steady-state (`rms_ss_self = 5.03` vs sibling runs ~2.4). Curve_fit on run3 alone was pulled toward chasing that noise, inflating its rise residual; LOOCV uses params from cleaner runs 1+2, giving a smoother prediction that doesn't chase run3's SS noise. **This is LOOCV robustness, not a simulator bug.** No action required.

### Files generated

- `data/processed/phase21_loocv_accel.csv` — 18-row accel per-trial results (LOOCV params, self params, 3 RMSE windows, floors)
- `data/processed/phase21_loocv_decel.csv` — 12-row decel per-trial results (LOOCV params, self params, 4 RMSE windows: fit_window/post/transient/ss, floors)
- `data/processed/phase21_loocv_summary.csv` — 10-row per-condition summary
- `figures/12_phase22_loocv_summary.png` — bar chart: LOOCV vs in-sample floor across all conditions, accel/decel split
- `figures/13_phase22_loocv_grid.png` — 30-panel overlay grid for thesis appendix

### Limitations

- LOOCV stays within the calibration grid: PWM ∈ {160, 200, 240}, decel transitions ∈ {240→0, 240→160}. **Does not test extrapolation.**
- No data from a separate bench session → does not test session-to-session generalization (thermal state, ambient T, motor age).
- `data/raw/_sealed/` is empty (never populated; was an aspiration in the original handover, not a real artifact).

### Open questions for thesis discussion

- Why does fwd PWM=160 have a wider per-trial spread than rev PWM=160? (Asymmetric friction breakaway? Encoder direction-dependent quantization?)
- The accel/decel reproducibility asymmetry — thermal stabilization is the most likely cause, but ambient-T was not logged for the Phase 2.1 session. Future bench sessions should record ambient T.

### Next steps

- **Phase 3 (closed-loop validation)** — requires (a) extending `simulate_model_C` to multi-event trajectories (currently raises `NotImplementedError` for >1 transition), (b) closed-loop bench data (PID step responses, ramp-tracking, or similar). Bench session needed.
- **Optional gap-fill (open-loop)** — uncalibrated PWMs (180, 220) and decel targets other than {0, 160} to characterize interpolation within the calibration convex hull. Useful but not blocking the thesis.

### Status

**Phase 2.2: COMPLETE.** Validation methodology demonstrated, results saved, summary and appendix figures rendered. Cascade Model C is validated within its calibration grid via LOOCV with quantified excess (+1.06 rpm accel, +0.10 rpm decel). Ready to move to Phase 3 in next bench session.

## 2026-05-22 — Phase 2 gap-fill bench session + analysis

### Session
- Firmware: `step_response_v2.cpp` (variant of v1 with 46-trial array; logic identical).
- 46 trials in ~7.5 min hands-off: 8 piggyback + 20 new accel + 18 new decel.
- Ambient T: 27.3°C start → 28.8°C end (AC on).
- Gap since previous bench session: ~2 weeks (last bench 2026-05-06).

### Files added
- `firmware/step_response_v2.cpp`
- `data/raw/step_responses_gapfill/*.csv` (46 trials)
- `data/raw/serial_logs/2026-05-22_phase2_gapfill_session.log`
- `data/raw/session_log.csv`
- `data/processed/phase2gapfill_fopdt_accel_{per_trial, per_condition}.csv`
- `data/processed/phase2gapfill_stepdown_{per_trial, per_condition}.csv`
- `data/processed/phase2gapfill_loocv_{accel, decel}.csv`
- `data/processed/phase2gapfill_loocv_summary_combined.csv` (10 P2.2 + 6 gap-fill)
- `figures/14_phase2gapfill_piggyback_overlay.png` through `figures/19_loocv_phase22_vs_gapfill.png`
- `notebooks/05_gap_fill.ipynb` (9 cells: setup, piggyback, P2.1 outlier audit, new accel, new decel, decel overlays, LOOCV new conditions, combined summary)

### Findings (thesis-relevant)

**1. Within-session reproducibility is excellent.**
Warm-motor LOOCV excess ≤ 0.5 rpm for almost all conditions. Only outlier: decel rev 240→100 (+1.06 rpm excess, attributable to stick-slip through deadzone in reverse direction — short PWM-ON pulses during freewheel interact stochastically with brush contact pattern).

**2. Session-to-session drift after 2-week idle is real and structured.**
- *Cold-start accel:* fwd τ inflated 30–40% for first ~30 s of operation (e.g. piggyback trial 1, fwd 200 run1: τ=131 vs Phase 2.1 mean 95). Recovers as motor warms. Direct support for the Phase 2.2 thermal hypothesis.
- *Persistent low-rpm decel:* τ at coast-through-deadzone targets (240→100, 240→180) is ~2x Phase 2.1's interpolated expectation, visually confirmed in trajectory overlays (`figures/18`). Friction at low rpm has shifted; lubricant settling during idle is the candidate mechanism.
- *Persistent rev high-PWM τ deflation (~20%):* gap-fill rev 240 τ ≈ 114 ms vs Phase 2.1 144 ms. Not warm-up — stable across all rev high-PWM trials. Mechanism unclear.

**3. Cascade structure further validated.**
K_ss highly linear in PWM within direction (per-condition std ≤ 2 rpm across 5 runs). Static block separability holds across all 5 calibrated PWMs (160, 180, 200, 220, 240).

**4. τ landscape refined.**
Broad bathtub minimum at PWM 180–220 (τ ≈ 95–110 ms), sharp rise at edges (PWM=160: 192–200 ms; PWM=240: 144–152 ms). Earlier "V-shape" framing was too sharp; the bottom is flat across a 40-PWM-wide window.

**5. Phase 2.2 hypothesis refined, not contradicted.**
Phase 2.2's accel/decel asymmetry (+1.06 vs +0.10) was driven by cold-start stochasticity, NOT a steady-state property. With warm motor and n=5, gap-fill accel excess collapses to −0.05 rpm. Decel inherently sees a warm motor (decel begins after 3 s at PWM=240), so its low excess is consistent across both phases.

### Documentation correction
Previous handover (2026-05-07) claimed `rms_decel` window was undocumented. Verified in nb03: the window IS documented as `decel_mask = (t >= STEP_DOWN_START_MS) & (t <= STEP_DOWN_START_MS + 1500)`, i.e. t ∈ [3000, 4500] ms (150 samples, 1500 ms post-step). Not load-bearing; Phase 2.2 correctly used `rms_total` as the apples-to-apples floor against LOOCV `rmse_fit_window`.

### Implications for Phase 3
- Phase 2.1 calibration parameters MUST NOT be used as ground truth for Phase 3 trials (session drift too large for decel).
- Phase 3 bench protocol must include a fresh in-session calibration block at the session start. Re-run the original 30 Phase 2.1 conditions, then proceed to closed-loop trials in the same session, then use that fresh calibration for Phase 3 simulator predictions.
- Expected closed-loop tracking accuracy in steady operation: ~3–5 rpm RMSE (matches within-session reproducibility floor).
- Cold-start may see transiently worse tracking for first ~30 s.
- Reverse-direction stops through deadzone will have elevated stochasticity.

### Open question (future work, not blocking thesis)
Reverse-direction τ deflation at high PWM (~20% faster than Phase 2.1, stable across all gap-fill rev high-PWM trials) is not explained by warm-up. Falsifying any specific mechanism (lubricant migration, brush wear pattern reset, bearing seating) would require controlled idle-vs-immediate session pairs with thermistor instrumentation. Out of scope.

Paste the entry into thesis_notes/log.md, commit, and confirm done.

## 2026-05-25 — Model selection: A/B/C ladder quantified (analysis only, no bench)

### Motivation
The thesis defined the candidate ladder (Model A naive LTI, B static+global τ, C cascade) but
only *argued* B/C superiority verbatim — A and B were never fit and scored as competitors
(status-doc §6; `models/` was empty). This closes that gap with an explicit, quantified
head-to-head, which is the "compare transfer functions and pick the winner" deliverable from
`plan.md` §3.3/§3.6.

### Method
Notebook `notebooks/06_model_comparison.ipynb`. Phase 2.1 grid only (30 trials, single session —
no cross-session confound). All three models simulated in PWM→RPM space with the same FOPDT core
used in nb04/nb05; scored in-sample on the post-step window (RMSE + FIT% = 1−‖e‖/‖y−ȳ‖), split by
direction and accel/decel. A transient window (5·τ_C, identical for all models) isolates the
B-vs-C dynamic gain.
- **Model A:** single proportional gain `K_A = 0.785 rpm/PWM` (LS through origin over 42 SS
  points), single global `τ=207 ms, Td=20 ms`. No static block.
- **Model B:** Model C's per-condition steady states + single global `τ=187 ms, Td=16 ms`.
- **Model C:** locked per-condition FOPDT (Tables 4.1–4.2), unchanged.

### Results (overall, 30 trials)
| Model | RMSE (rpm) | FIT% | transient RMSE |
|---|---:|---:|---:|
| A (naive LTI) | 34.7 | −157 | 34.0 |
| B (static + global τ) | 6.96 | 63.1 | 15.3 |
| C (cascade) | **4.07** | **78.3** | **5.83** |

Per group (RMSE A / B / C): accel-fwd 42.1/6.0/3.8, accel-rev 38.4/7.2/4.3, decel-fwd
28.3/6.7/4.3, decel-rev 24.4/8.3/3.8. **C wins every direction × region group.**

### Findings (thesis-relevant)
1. **Model A fails outright** — negative FIT% in 3 of 4 groups (worse than predicting the mean).
   With no static block its single gain overshoots badly at low PWM (deadzone unmodelled). The
   straw man is now quantified, not asserted.
2. **The static block is the dominant gain (A→B):** RMSE 34.7 → 6.96 rpm. This is the measured
   payoff of the Chapter 3 cascade decomposition.
3. **Region-dependent τ is a real but smaller gain (B→C):** RMSE 6.96 → 4.07 rpm, and the gain is
   concentrated in the transient window (C 5.8 vs B 15.3 rpm) — exactly where the τ bathtub
   predicts a single global τ must fail.
4. C's post-step RMSE sits +0.25 rpm above the locked per-trial `rms_total` floor → the
   comparison reproduces the locked Model C fits (no regression of Chapter 4 numbers).

### Artifacts
- Notebook: `notebooks/06_model_comparison.ipynb`
- Processed: `data/processed/phase21_model_ladder_per_trial.csv`, `phase21_model_ladder_summary.csv`
- Figures: `figures/20_model_ladder_overlay.png` (A/B/C over real traces, 2×2),
  `figures/21_model_ladder_scoreboard.png` (RMSE + FIT% bars by group)
- Models: `models/model_A.json`, `model_B.json`, `model_C.json` (populates the empty `models/`)
- Draft section: `thesis_notes/draft_model_selection.md` (slot into Ch4 as §4.6 or open Ch5)

### Scope / caveats
In-sample structural model selection on a single session. Generalisation is the separate LOOCV
result (Ch5); cross-session drift is §5.6. Covers the calibrated grid (PWM 160–240); extending the
ladder to gap-fill PWM 180/220 is straightforward future work. Model A uses a through-origin gain
(an affine variant would still lack the deadzone and remain the straw man).

### Extension (same day) — full operating envelope (P2.1 + gap-fill)

Extended the ladder to all 68 calibrated trials: added gap-fill accel PWM 180/220 (n=5 each) and
decel 240→100/180/220 (n=3 each); 38 accel + 30 decel. Models A and B re-fit globally over the
full grid; Model C uses session-appropriate per-condition params (gap-fill conditions from the
gap-fill fit tables). Full-grid fits: K_A=0.783 rpm/PWM, A τ=196/Td=10, B τ=211/Td=2.

Overall (68): A 35.0 / B 8.5 / C 4.3 rpm RMSE; FIT% −133 / 52 / 72. **By session the ordering
A≪B<C replicates independently** — P2.1 34.8/7.1/4.1, gap-fill 35.2/9.7/4.5. The added mid-range
points are where B is worst: accel transient RMSE vs PWM is 160→4.5, 180→18.3, 200→28.8, 220→30.5,
240→15.8 for B vs 4.2/3.6/2.6/4.7/6.8 for C — B's single global τ (211 ms) fails hardest at the
bathtub bottom (180–220, true τ≈95–108 ms), so broadening the grid *strengthens* B→C. B's global τ
also rose (187→211 ms) once the slow deadzone-edge decels (τ 350–366 ms) entered the global fit.

Artifacts: notebook cells appended to `notebooks/06_model_comparison.ipynb`;
`data/processed/phase2_full_model_ladder_per_trial.csv`, `phase2_full_model_ladder_summary.csv`;
`figures/22_model_ladder_fullgrid.png` (transient RMSE vs operating point, log scale).
Thesis: §4.6 extended with Table 4.4 (overall + by-session) and Figure 22 (=Fig 4.8); `main.pdf`
rebuilt to 79 pages, clean (no errors/undefined refs). Caveat: full grid mixes two sessions (as do
Tables 4.1–4.2); the cross-session penalty falls on all three models, so the single-session Table
4.3 stays the clean structural reference.




## 2026-05-27 — Phase 3 bench day (closed-loop validation)

### Pre-registration freeze (2026-05-26)
Pre-registered hypothesis, metrics, success criteria, and statistical procedure committed in
`notebooks/07a_closed_loop_sim.ipynb` Cell G and persisted to
`data/processed/phase3_preregistration.json` (SHA-256
`da94c83d3b57bda80cf3a137740ed7441f41df2424da909098a2d63602707669`).
Pre-bench sim (Model C as ground-truth plant) predicted BASE−CASC RMSE of +2.20, +4.21, +9.15,
+0.92 rpm on P1/P2/P3/P4 respectively.

### Stage 0 → Stage 1 → Stage 2 (single working day, 2026-05-27)

Stage 0 (software, no bench): built `motor_id/{cascade_sim,controllers,model_io,metrics,
calibration}.py`. Cascade simulator regression-tested against the locked notebook 04/05
single-transition simulator: max |err| 2.8e-14 rpm across all six Phase 2.1 accel conditions (gate
1e-6, passed by 8 orders of magnitude).

Stage 1 (firmware smoke): built `src_closedloop/main.cpp` + `platformio_closedloop.ini`. Smoke
test on P3 reversal with placeholder gains: BASE 19.85 rpm RMSE, CASC 13.84 rpm RMSE, 10.0 ms loop
period locked, telemetry parses through `split_log.py` unchanged. CASC steady-state PWM ±187 at
±100 rpm matches the FF table lookup, confirming firmware FF parser. `src/main.cpp` untouched
throughout.

Stage 2 (bench): one 2026-05-27 session, ~75 min motor-on. 55 s warm-up; 30-trial CALIB (18/18
accel fits OK, 12/12 decel fits OK); on-laptop refit gave session Model A `K_A=0.737 rpm/PWM,
τ=155 ms, T_d=6.6 ms` — meaningfully different from locked Phase 2.1 (`0.785 / 207 / 19.8`),
confirming §5.6's "calibrate in situ" recommendation has teeth. Frozen IMC gains uploaded;
64 paired closed-loop trials (P1×8 + P2×8 + P3×8 + P4×8) × {BASE, CASC} with explicit pair IDs,
seed 20260527; 6 drift-check trials at end.

### Pre-registered tests, applied (n=8 paired per profile)

| Profile | median(BASE−CASC) | 95 % CI | Wilcoxon p (greater) | Sim pred. |
|---|---:|---:|---:|---:|
| P1 (staircase)        | +2.82 rpm | [+2.74, +2.93] | 0.004 | +2.20 |
| P2 (deadzone ramp)    | −1.13 rpm | [−1.20, −0.97] | 1.000 | +4.21 |
| P3 (reversal)         | +5.15 rpm | [+5.04, +5.40] | 0.004 | +9.15 |
| P4 (small-signal)     | +1.00 rpm | [+0.86, +1.22] | 0.004 | +0.92 |

Pooled MAD-standardised paired-difference Wilcoxon over P1+P2+P3: p = 3 × 10⁻⁴ (n = 24 pooled).

**Primary criterion: FAIL** — median(BASE−CASC)>0 required on each of P1, P2, P3, but P2 is
strongly negative. **Strong criterion: FAIL** — primary required, and primary fails. **Fairness
gate (cascade RMS PWM ≤ 1.5× baseline): PASS** — ratios 0.99–1.04 across all four profiles.

### Headline interpretation

Cascade clearly wins on P1, P3, P4 (each CI cleanly excludes zero) and clearly loses on P2 (CI
excludes zero on the wrong side). P3 (reversal) shows the largest single advantage at +5.22 rpm
mean, exactly as the hypothesis predicted for the regime where the single-LTI baseline is most
misspecified. The P2 sign reversal vs sim (+4.21 → −1.09) is a real counter-example to the
universal cascade hypothesis.

Mechanism (interpreted in §6.6): the inverse-static FF table saturates at the breakaway PWM for
|ref| ≤ 50 rpm (since the motor cannot sustain steady speeds below breakaway), producing a
slope discontinuity at the breakaway-RPM edge. On a slow ramp this discontinuity is a small
step-like PWM kick at each zero crossing, breaking the smoothness the baseline PI integrator
would produce by accumulating gradually. P4's small but real positive result (≈1 rpm with CI
excluding zero) shows the FF gives a general settling-time benefit on step references even in
the linear regime, not just the deadzone/extremes/reversal benefit the hypothesis named.

The pre-registered binary "did cascade win" answer is **no, not universally** — the loss is
concentrated entirely in P2. The thesis bottom line is therefore sharper than a clean universal
win: cascade is the right closed-loop structure for stepwise tracking; the *wrong* structure,
without modification, for slow ramps through the deadzone. The one-change refinement is a
smoothed FF table through the deadzone region.

### Drift check (start vs end of session, ~2 h apart)

| Direction | ΔK_ss | Δτ |
|---|---:|---:|
| fwd 200 | +6.7 % | −5.2 % |
| rev 200 | +3.7 % | −2.5 % |

L298N junction warming: driver saturation drop falls slightly so the same PWM gives a few % more
RPM and a few % faster transient. Forward drift larger than reverse, as in §3.8. Negligible at
within-pair timescales (pair members run within seconds of each other); confirms the
recalibrate-in-situ rule for any future session.

### Artifacts

Code: `motor_id/{cascade_sim,controllers,model_io,metrics,calibration}.py`,
`src_closedloop/main.cpp`, `platformio_closedloop.ini`, `scripts/{smoke_closed_loop.py,
bench_session.py}`. Notebooks: `07a_closed_loop_sim.ipynb` (sim + pre-registration freeze),
`07b_closed_loop_results.ipynb` (bench analysis + pre-registered tests).

Models: `models/calibration_2026-05-27.json` (session-fresh A and C), `models/closed_loop_
gains_2026-05-27.json` (frozen IMC gains + FF table).

Data: `data/raw/closed_loop_2026-05-27/{calib_trials,closed_loop_trials,drift_trials}/`
(30 + 64 + 6 CSVs), `data/raw/closed_loop_2026-05-27/trial_index.json`,
`data/raw/serial_logs/2026-05-27_phase3_session.log`. Processed:
`data/processed/{closed_loop_metrics_per_trial.csv, closed_loop_summary.json,
closed_loop_drift_check.csv}`.

Figures: `figures/23_closed_loop_paired_diff.png` (per-profile RMSE diff with 95 % bootstrap CI),
`figures/24_closed_loop_trajectories.png` (representative trajectories per profile per
controller).

Thesis: chapter drafts `draft_ch6_closedloop.md` rewritten from "plan" to results; `draft_ch1` and
`draft_ch7` updated to drop deferred-framing and to include Phase 3 findings. LaTeX
`thesis/Chapters/Chapter_{1,6,7}` mirrored. `main.pdf` rebuild pending.

## 2026-06-10 - Thesis LaTeX standalone-final polish (no bench)

Editing pass on `thesis/` LaTeX only (no data, no model, no figure changes). Goal: turn the
draft-rooted report into a self-contained final document.

- **Em dashes removed everywhere in rendered prose.** All `---` replaced by comma / colon /
  parentheses across `main.tex` (abstract) and `Chapters/Chapter_1..7`. En-dash `--` numeric
  ranges (e.g. `1--5` rpm) left intact. Verified: `pdftotext main.pdf | grep -c '—'` = 0.
  Remaining `---` in the tree are only LaTeX comment dividers (`% ---`) and TikZ-figure comments,
  which do not render.
- **Repo/code identifiers stripped from prose.** Every `\texttt{}`/`\mathtt{}` carrying a filename,
  CSV/notebook/`.cpp`/`.py` path, serial-command name (`GO`, `GAINS_BASE`, `FF_FWD`, ...), telemetry
  column header (`t_ms,pwm_cmd,dir,enc_count,rpm`), or API/function/struct name
  (`analogWriteFrequency()`, `PwmOut`, `pulse_perc()`, `ENCODER_SIGN`, `compute_imc_gains`,
  `ff_lookup`, `static_rpm`) was reworded into plain description. The no-op `\chaptersources{...}`
  provenance footers were deleted from all seven chapters.
- **Informal phrasing reworded:** "piggyback (trials/re-runs)"→"cross-session re-run(s)"
  (figure *labels* `fig:piggyback` and the figure *filenames* kept — invisible in the PDF);
  "hands-off"→"without operator intervention"; "straw-man baseline"→"deliberately simple baseline".
  Visible "status-doc §x" pointers removed from two Ch5 captions.
- **Build:** `cd thesis && latexmk -pdf main.tex` → exit 0, **0 undefined refs/cites, 90 pages**
  (was 91; one page of reflow). No locked numbers, tables, or figures touched.
- **Not done:** the `thesis_notes/draft_ch*.md` markdown working drafts were *not* re-polished, so
  the `.tex` is now ahead of them on em-dash/standalone prose style. Two invariants documented in
  `CLAUDE.md` and `AGENTS.md`: no em dashes, no code identifiers in thesis prose.
- **Figure-baked draft words fixed (same day).** Several thesis figures had draft jargon rendered
  *into the image* (titles/legends), not just the caption. Fixed at the generator level in
  `notebooks/05_gap_fill.ipynb` (display strings only, no variable names or logic touched):
  fig 14 legend "piggy run N" → "re-run N", subplot titles "τ_p21/τ_pig" → "τ_P2.1/τ_rerun";
  fig 15 titles "Piggyback τ/|K_ss| vs trial-order" → "Cross-session re-run … vs trial order";
  fig 16 legend "… piggyback (n=2)" → "… re-run (n=2)" and title "+ piggyback" → "+ re-runs";
  fig 18 "P21" → "Phase 2.1" in legends and overlay titles. Notebook re-executed in place; figs
  14/15/16/18 regenerated and mirrored to `thesis/Pictures/`. The re-run's float-noise-only CSV
  rewrites (`phase2gapfill_*.csv`, differing at ~1e-9, invisible at thesis precision) were
  `git checkout`-restored to keep locked numbers byte-stable, and the unintended fig-17 re-render
  was restored too. Net change: 4 figure PNGs (×2 = `figures/` + `thesis/Pictures/`) and the
  notebook. The figure *filenames* (e.g. `14_…_piggyback_overlay.png`) were kept — they are
  invisible in the PDF; only the in-image text was the issue. Thesis rebuilt: 90 pp, 0 undefined.
