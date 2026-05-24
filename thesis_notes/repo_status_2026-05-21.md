# Repository Status — DC Motor System Identification

**Generated:** 2026-05-21 · **Branch:** main · **Author tooling:** full read-through of notebooks, firmware, scripts, processed CSVs, figures, and thesis notes.

All numbers in this document are pulled **directly from `data/processed/*.csv`** (and from `data/raw/` for the static block, which has no processed CSV). Where prose in `log.md`/`AGENTS.md`/notebooks disagrees with the CSV ground truth, the CSV wins and the discrepancy is flagged in §5/§9.

---

## 1. Project overview

This thesis is an open-loop **system identification** of a DC-motor + L298N-driver rig (Arduino Uno R4 Minima, 12 V 60:1 geared motor, 600 PPR quadrature encoder → 2400 counts/rev). The identified model is a **cascade**: `PWM command → static driver-voltage block → motor dynamic block → RPM`, internally called **Model C**. The static block captures the L298N's direction-asymmetric voltage delivery plus a hysteretic deadzone; the motor dynamic block is a first-order-plus-dead-time (FOPDT) response that is approximately direction-symmetric but **operating-point dependent**, with **separate forward/reverse parameters and separate accel/decel regions**. Steady-state behaviour was mapped statically (Phase 1.1/1.2); transient behaviour was fitted as per-condition FOPDT from step responses (Phase 2.1 + gap-fill); the model was validated within its calibration grid by leave-one-out cross-validation (Phase 2.2 + gap-fill). The cascade decomposition is empirically supported because the directional asymmetry and the session-to-session drift both localize to the driver/static side, while the motor V→RPM gain stays stable and symmetric.

> Operational note: the static "driver-voltage" block is the *physical/conceptual* justification (Phase 1.1 voltage measurements). The **operational Model C simulator** (`simulate_model_C`, notebooks 04/05) works directly in PWM→RPM space — each condition carries a fitted FOPDT whose gain `K_ss` is in **rpm**, with the voltage block absorbed into `K_ss`. No voltage variable appears at simulation time.

---

## 2. Hardware setup

| Item | Value | Source |
|---|---|---|
| Board | Arduino Uno R4 Minima (`uno_r4_minima`) | `PIN_CONFIGURATION.md`, `platformio.ini` |
| Driver | L298N H-bridge, single channel (OUT1/OUT2, ENA) | `PIN_CONFIGURATION.md` |
| Motor | Orange Johnson 12 V, 60:1 gearbox, ~300 rpm | `datasheets/`, `plan.md` |
| Encoder | 600 PPR quadrature, 4× decoded → **2400 counts/rev** | `firmware_archive/step_response_v2.cpp:41` |
| Encoder pins | A=D2, B=D3 (CHANGE interrupts, `INPUT_PULLUP`; external 4.7 kΩ pull-ups also specified) | `…v2.cpp:33-34,260-268`; `PIN_CONFIGURATION.md` |
| Direction pins | IN1=D4, IN2=D5 (fwd: IN1 H/IN2 L) | `…v2.cpp:35-36,69-80` |
| PWM pin / freq | ENA=D9, **20 kHz** via Renesas `PwmOut` (`motorPwm.begin(20000.0f,…)`; core has no `analogWriteFrequency`) | `…v2.cpp:61,273`; `PIN_CONFIGURATION.md` |
| Encoder sign | `ENCODER_SIGN = -1` (fixed after Phase 0 scope check) | `…v2.cpp:40`; `log.md` 2026-05-06 |
| Serial baud | 230400 | `…v2.cpp:270` |
| Telemetry rate | 10 ms (`LOG_INTERVAL_US = 10000`) | `…v2.cpp:165` |
| PSU | 12.0 V, current limit 1.5 A | `log.md`; `data/metadata/2026-05-07_phase21_session.md` |
| L298N jumpers | ENA jumper **removed** (D9 drives PWM); 5V-EN removed when Arduino feeds logic 5V | `PIN_CONFIGURATION.md` |

Mechanical fixturing (motor/encoder mounts, coupling) is in `freecad_macros_motor_encoder/` (STEP/STL/FreeCAD macros); component datasheets in `datasheets/`. These are reference assets, not part of the analysis pipeline.

---

## 3. Experimental phases

### Phase 1.1 — Static map
- **Goal:** Map steady-state PWM→V_motor and V_motor→RPM, and quantify forward/reverse asymmetry.
- **Firmware/protocol:** Manual-mode firmware (`firmware_archive/manual_mode_v1.cpp`); operator stepped PWM 10→255 in both directions, recording DMM/scope mean motor voltage and serial RPM. One combined CSV with a `direction` column.
- **Notebook:** `notebooks/01_static_map.ipynb` (8 cells).
- **Key results (recomputed from `data/raw/static_sweep_20260506_run1.csv`, 52 rows = 26 fwd + 26 rev, PWM 10–255):**
  - Motor-block gain (through-origin LS on moving points, V→RPM): **K_fwd = 26.94 rpm/V**, **K_rev = 24.52 rpm/V** (24.5156). Exactly matches the locked values.
  - Staircase "breakaway" PWM = 130 both directions (stochastic; lower than true breakaway — see Phase 1.2).
  - Asymmetry lives in PWM→V (driver), not V→RPM (motor): V→RPM gains agree within ~9%.
- **Figures:** `01_pwm_vs_vmean.png`, `02_pwm_vs_rpm.png`, `03_vmean_vs_rpm.png` (with K fits), `04_asymmetry_ratio.png`.

### Phase 1.2 — Deadzone hysteresis
- **Goal:** Find true breakaway (from rest) and dropout (to rest) PWM thresholds and quantify hysteresis.
- **Firmware/protocol:** Manual ramp passes (multiple, both directions); scope V_motor + serial RPM at threshold.
- **Notebook:** none (characterized manually; reported in `log.md`). Data: `data/raw/deadzone_manual_run01.csv` (4 rows).
- **Key results (from `deadzone_manual_run01.csv`):**
  - Breakaway (up): **fwd 154, rev 144** PWM (V_motor ≈ ±2.30 V, rpm ≈ ±55).
  - Dropout (down): **fwd 114, rev 112** PWM (V_motor ≈ −0.13 V, rpm 0).
  - Hysteresis band ≈ 32–40 PWM wide; deadzone block must be hysteretic.
- **Figures:** none.

### Phase 2.1 — Step-response FOPDT (accel + decel)
- **Goal:** Identify transient dynamics (K_ss, Td, τ) per operating point and test accel/decel + direction symmetry.
- **Firmware/protocol:** `firmware_archive/step_response_v1.cpp` (automated, **30 trials**, `GO`-triggered, block-delimited). 18 step-ups (PWM 160/200/240 × fwd/rev × 3) + 12 step-downs (240→0, 240→160 × fwd/rev × 3). Captured via `scripts/capture_serial.py`, split via `scripts/split_log.py` → `data/raw/step_responses/` (30 CSVs). Session metadata: `data/metadata/2026-05-07_phase21_session.md`.
- **Notebook:** `notebooks/03_step_responses.ipynb` (25 cells). Pipeline: implicit static cross-validation → heuristic 63.2% FOPDT → `scipy.curve_fit` promotion → step-down FOPDT → synthesis.
- **Key results:**
  - Implicit cross-val (`phase21_xval_static_consistency.csv`): PWM≥200 step SS agrees with sweep within thermal-drift bounds (fwd −5%, rev −1 to −2%); PWM=160 disagrees −11 to −25% (dropped — friction/deadzone regime).
  - Accel FOPDT (`phase21_fopdt_curvefit_per_condition.csv`) and decel FOPDT (`phase21_stepdown_curvefit_per_condition.csv`) — see §4 tables.
  - τ is **operating-point dependent** (PWM=200 ≈ 88 ms vs PWM=240 ≈ 148 ms): single-global-τ model rejected, region-dependent Model C accepted.
  - Dynamic block direction-symmetric within std; accel/decel asymmetry confirmed (decel τ > accel τ).
- **Figures:** `05`–`11` (single-trial fit, 6-condition heuristic grid, τ/Td-vs-PWM, curve_fit residual grid, step-down single + 4-grid, τ synthesis bar chart).

### Phase 2.2 — LOOCV validation
- **Goal:** Validate Model C within its calibration grid without held-out data.
- **Firmware/protocol:** none (analysis only). The originally-planned `data/raw/_sealed/` held-out set **never existed** (cell 5a inventory probe confirmed absent on disk and in `.gitignore`); pivoted to leave-one-out cross-validation over the 30 Phase 2.1 trials.
- **Notebook:** `notebooks/04_validation.ipynb` (15 cells). Builds `simulate_model_C` (single-transition; `override_params` for LOOCV); each trial predicted from the mean of the other 2 runs at its condition.
- **Key results (`phase21_loocv_summary.csv`, 10 conditions):** accel mean excess **+1.06 rpm** (std 0.80), decel **+0.10 rpm** (std 0.10) → decel ~10× more reproducible than accel; worst = accel fwd PWM=160 **+1.97 rpm**. See §4.
- **Figures:** `12_phase22_loocv_summary.png`, `13_phase22_loocv_grid.png` (30-panel appendix).

### Phase 2 gap-fill — bench re-run + new conditions + drift analysis
- **Goal:** Fill the PWM/target gaps (180/220 accel; 240→100/180/220 decel), bound session-to-session drift, and stress-test the Phase 2.2 accel/decel hypothesis with warm-motor n=5.
- **Firmware/protocol:** `firmware_archive/step_response_v2.cpp` (= `src/main.cpp`; **46 trials** = 8 piggyback P2.1 reruns + 20 new accel (180/220 × fwd/rev × 5) + 18 new decel (240→100/180/220 × fwd/rev × 3); ~7.3–7.5 min hands-off). ~2 weeks after the Phase 2.1 session. Ambient 27.3 °C → 28.8 °C. Raw: `data/raw/step_responses_gapfill/` (46 CSVs); log: `data/raw/serial_logs/2026-05-22_phase2_gapfill_session.log`.
- **Notebook:** `notebooks/05_gap_fill.ipynb` (9 cells).
- **Key results:**
  - New accel/decel FOPDT (`phase2gapfill_fopdt_accel_per_condition.csv`, `phase2gapfill_stepdown_per_condition.csv`) — §4.
  - Within-session reproducibility excellent: gap-fill accel LOOCV excess **−0.05 rpm**, decel **+0.45 rpm** (`phase2gapfill_loocv_summary_combined.csv`); worst = decel rev 240→100 **+1.06 rpm**.
  - Three structured session-drift effects (§5). Cascade structure further supported (K_ss linear in PWM within direction); τ landscape refined from sharp "V" to broad bathtub (flat ~95–110 ms across PWM 180–220).
- **Figures:** `14`–`19` (piggyback overlay, warm-up trend, accel τ-vs-PWM, decel τ-vs-target, decel trajectory overlays, P2.2-vs-gap-fill LOOCV).

---

## 4. Final model state

### 4.1 Static block

**Driver sub-block (PWM → V_motor):** empirical, direction-asymmetric map (figure `01`); reverse delivers ~7% more motor voltage at high PWM and >2× at some low-PWM points. No closed form — represented as the measured curve. In the operational simulator this is folded into the per-condition `K_ss` (rpm).

**Motor sub-block (V_motor → RPM), above deadzone, through origin:**
- RPM = K · V_motor, **K_fwd = 26.94 rpm/V**, **K_rev = 24.52 rpm/V** (K_rev negative when signed).

**Deadzone (hysteretic):**
- Breakaway PWM: **154 (fwd) / 144 (rev)**; Dropout PWM: **114 (fwd) / 112 (rev)**; band ≈ 32–40 PWM.
- Steady-state hysteresis at PWM=160 (from step-down vs step-up SS): ≈ **21 rpm fwd** (73.75 from above vs 52.4 from below), ≈ **16 rpm rev** (85.66 vs 69.75).

### 4.2 Dynamic block — FOPDT, all 10 accel operating points (5 PWM × 2 dir)

Accel FOPDT: `rpm(t) = K_ss · (1 − e^{−(t−Td)/τ})`. PWM 160/200/240 from `phase21_fopdt_curvefit_per_condition.csv` (n=3, Phase 2.1); PWM 180/220 from `phase2gapfill_fopdt_accel_per_condition.csv` (n=5, gap-fill).

| Dir | PWM | K_ss (rpm) | Td (ms) | τ (ms) ± std | rms_rise | n | Session |
|---|---:|---:|---:|---:|---:|---:|---|
| fwd | 160 | 52.08 | ~0 | 200.1 ± 22.0 | 2.61 | 3 | P2.1 |
| fwd | 180 | 89.55 | 2.33 | 102.9 ± 6.87 | 3.70 | 5 | gap-fill |
| fwd | 200 | 123.53 | 4.92 | 95.1 ± 4.64 | 2.48 | 3 | P2.1 |
| fwd | 220 | 175.4 | 6.43 | 108.4 ± 2.05 | 4.97 | 5 | gap-fill |
| fwd | 240 | 209.74 | 17.06 | 152.3 ± 2.74 | 4.69 | 3 | P2.1 |
| rev | 160 | −69.55 | ~0 | 191.7 ± 12.15 | 4.03 | 3 | P2.1 |
| rev | 180 | −93.97 | 1.25 | 93.08 ± 0.88 | 3.35 | 5 | gap-fill |
| rev | 200 | −131.35 | 5.63 | 81.24 ± 0.94 | 2.66 | 3 | P2.1 |
| rev | 220 | −180.0 | 7.47 | 102.6 ± 1.57 | 5.10 | 5 | gap-fill |
| rev | 240 | −222.56 | 23.49 | 144.4 ± 2.45 | 7.17 | 3 | P2.1 |

Notes: (1) Td here is an **effective curve_fit parameter** that absorbs non-first-order rise shape — it is *not* the ~10 ms physical encoder/serial latency (the 63.2% heuristic gives ~10 ms; curve_fit pins Td≈0 at PWM=160 and inflates it to 17–23 ms at PWM=240). (2) PWM=200 is the cleanest FOPDT; PWM=240 is effective FOPDT with visible rise-shape residuals; PWM=160 is friction-corrupted. (3) **180/220 were measured in a different session (warm motor, 2 weeks later)** — see drift caveats in §5.

### 4.3 Dynamic block — FOPDT, all 10 decel operating points (5 targets × 2 dir)

Decel FOPDT: `rpm(t) = y_final + (y_init − y_final)·e^{−(t−Td)/τ}` from 240 PWM hold. Targets 0/160 from `phase21_stepdown_curvefit_per_condition.csv` (n=3, Phase 2.1); targets 100/180/220 from `phase2gapfill_stepdown_per_condition.csv` (n=3, gap-fill).

| Dir | 240→ | y_init | y_final | Td (ms) | τ (ms) ± std | rms_decel | n | Session |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| fwd | 0 | 214.3 | −0.69 | 55.19 | 172.2 ± 1.77 | 8.67 | 3 | P2.1 |
| fwd | 100 | 220.5 | 1.09 | 25.51 | 366.2 ± 1.62 | 4.74 | 3 | gap-fill |
| fwd | 160 | 215.7 | 73.75 | 14.06 | 275.3 ± 8.77 | 4.39 | 3 | P2.1 |
| fwd | 180 | 219.9 | 94.18 | 0.33 | 356.6 ± 3.55 | 4.28 | 3 | gap-fill |
| fwd | 220 | 219.4 | 175.9 | 8.92 | 122.9 ± 16.14 | 5.43 | 3 | gap-fill |
| rev | 0 | −229.1 | ~0 | 62.93 | 189.5 ± 3.87 | 9.78 | 3 | P2.1 |
| rev | 100 | −229.9 | −0.61 | 25.27 | 349.0 ± 20.43 | 5.58 | 3 | gap-fill |
| rev | 160 | −231.7 | −85.66 | 9.95 | 306.4 ± 3.99 | 2.82 | 3 | P2.1 |
| rev | 180 | −229.8 | −96.23 | 5.94 | 321.3 ± 19.13 | 4.33 | 3 | gap-fill |
| rev | 220 | −230.2 | −181.8 | 11.43 | 109.2 ± 5.13 | 5.49 | 3 | gap-fill |

Structure: decel τ is **not monotone in target** — coast-through-deadzone targets (100, 180) have the largest τ (≈ 350–366 ms), full coast (→0) is faster (172/190 ms), and mild decel (→220) is fastest (109–123 ms). The 240→100 and 240→180 (gap-fill) τ run ~2× the value Phase 2.1 interpolation would predict (low-rpm decel drift, §5). `Td` is again an effective parameter.

### 4.4 Validation residuals (LOOCV, combined)

Source: `phase2gapfill_loocv_summary_combined.csv` (20 rows; the Phase 2.2 subset is identical to `phase21_loocv_summary.csv`). `excess = LOOCV mean RMSE − in-sample fit floor`.

| Phase | Type | Dir | Condition | n | LOOCV RMSE | floor | excess |
|---|---|---|---|---:|---:|---:|---:|
| P2.2 | accel | fwd | PWM=160 | 3 | 4.589 | 2.615 | **+1.974** |
| P2.2 | accel | fwd | PWM=200 | 3 | 3.299 | 2.478 | +0.822 |
| P2.2 | accel | fwd | PWM=240 | 3 | 6.440 | 4.689 | +1.751 |
| P2.2 | accel | rev | PWM=160 | 3 | 5.161 | 4.029 | +1.132 |
| P2.2 | accel | rev | PWM=200 | 3 | 2.363 | 2.658 | −0.295 |
| P2.2 | accel | rev | PWM=240 | 3 | 8.125 | 7.173 | +0.952 |
| P2.2 | decel | fwd | 240→0 | 3 | 5.171 | 5.160 | +0.012 |
| P2.2 | decel | fwd | 240→160 | 3 | 4.463 | 4.316 | +0.147 |
| P2.2 | decel | rev | 240→0 | 3 | 5.412 | 5.389 | +0.023 |
| P2.2 | decel | rev | 240→160 | 3 | 2.961 | 2.735 | +0.226 |
| gap-fill | accel | fwd | PWM=180 | 5 | 3.977 | 3.695 | +0.282 |
| gap-fill | accel | fwd | PWM=220 | 5 | 4.752 | 4.966 | −0.214 |
| gap-fill | accel | rev | PWM=180 | 5 | 3.436 | 3.345 | +0.091 |
| gap-fill | accel | rev | PWM=220 | 5 | 4.725 | 5.099 | −0.374 |
| gap-fill | decel | fwd | 240→100 | 3 | 4.250 | 4.076 | +0.173 |
| gap-fill | decel | fwd | 240→180 | 3 | 4.575 | 4.478 | +0.097 |
| gap-fill | decel | fwd | 240→220 | 3 | 6.286 | 5.685 | +0.601 |
| gap-fill | decel | rev | 240→100 | 3 | 5.290 | 4.230 | **+1.060** |
| gap-fill | decel | rev | 240→180 | 3 | 5.014 | 4.502 | +0.512 |
| gap-fill | decel | rev | 240→220 | 3 | 6.151 | 5.887 | +0.264 |

**Group means:** P2.2 accel +1.06 / decel +0.10; gap-fill accel −0.05 / decel +0.45. Reading: cold-start accel stochasticity (P2.2, motor from rest) inflates accel excess; with a warm motor and n=5 (gap-fill) accel excess collapses to ≈0. Decel always begins after 3 s at PWM=240 (warm), so decel excess is low and consistent across both phases. Expected steady-operation closed-loop tracking floor ≈ 3–5 rpm RMSE.

---

## 5. Limitations and known issues

**Session-to-session drift (three distinct effects, gap-fill vs Phase 2.1, ~2 weeks idle):**
1. **Cold-start accel τ inflation (transient, ~first 30 s):** piggyback trial #1 fwd 200 run1 τ = 131 ms vs P2.1 mean 95 ms (~30–40% high), recovers as motor warms (`phase2gapfill_fopdt_accel_per_trial.csv` ordering; figure `15`).
2. **Persistent low-rpm decel slowdown:** coast-through-deadzone decel (240→100, 240→180) τ ≈ 350–366 ms, ~2× Phase 2.1's interpolated expectation (figure `18`). Candidate: lubricant settling during idle.
3. **Persistent reverse high-PWM τ deflation (~20%):** gap-fill rev 240 τ ≈ 114 ms (piggyback) vs P2.1 144 ms; stable across all rev high-PWM trials, *not* warm-up. Mechanism unexplained (out of scope).

**Cold-start stochasticity:** the Phase 2.2 accel/decel reproducibility asymmetry (+1.06 vs +0.10) was driven by cold-start friction breakaway + unknown rotor pole alignment from rest, not a steady-state property — confirmed by gap-fill's collapse to −0.05. Implication: Phase 2.1 parameters must **not** be used as ground truth for a later bench session; Phase 3 needs fresh in-session calibration.

**Noisy reverse 240→100 decel:** the worst gap-fill condition. `phase2gapfill_stepdown_per_condition.csv` shows rev 240→100 with τ_std = 20.4 ms, Td_std = 8.0 ms, y_init_std = 3.9 rpm (per-trial τ_self spans 331–371 ms; y_init spans −225 to −232). LOOCV excess +1.06 rpm. Attributed to stick-slip / short PWM-ON freewheel pulses interacting stochastically with brush contact through the deadzone in reverse. (The fwd 240→220 condition is also relatively noisy: τ_std = 16.1 ms, excess +0.60.)

**Thermal/driver caveats:** static-block parameters are valid only at the session's thermal state — L298N V_motor drifts ~2–4% and PSU current ~5–9% over a session (spot-check at PWM=255: fwd V −3.8%, rev V +1.9%); motor V→RPM block reproducible to <1%. Ambient T was **not logged** for the Phase 2.1 session.

**FOPDT misspecification (bounded):** PWM=160 (friction onset) and PWM=240 (smooth onset) accel, and all coast decel (Coulomb friction is not first-order), are *effective* FOPDT — residuals are structured but bounded (rms_rise up to ~7 rpm at rev-240). Motivates a Stribeck/Coulomb extension ("Model D") and a higher-order dynamic block, neither built.

**Td is not physical in the fitted tables:** curve_fit Td absorbs rise-shape error (Td≈0 at PWM=160, 17–63 ms for high-PWM/decel); the ~10 ms encoder/serial latency only appears in the heuristic fit.

---

## 6. What's NOT been done

**Phase 3 — closed-loop validation (NOT started).** This is the thesis's culminating claim (cascade Model C beats a naive global-LTI model in closed loop, per `plan.md`) and nothing for it exists yet. Needs:
- **Simulator v2:** `simulate_model_C` currently raises `NotImplementedError` for >1 transition (single-step only). A multi-event/feedback-capable version is required, and it should be extracted from the notebooks into a reusable module (today it lives only inside nb04/nb05; `models/` holds no code).
- **Closed-loop firmware:** a PID (or similar) controller variant — does not exist (current `src/main.cpp` is the open-loop 46-trial sequencer).
- **Bench protocol + data:** a fresh session that runs an in-session calibration block (re-run the 30 Phase 2.1 conditions) *then* closed-loop trials (setpoint steps, ramp tracking), using same-session calibration for simulator predictions. No closed-loop data exists.
- **Baseline:** a naive global-LTI model to beat (single τ, single K) — not yet defined/fit as a comparison artifact.

**Other future work flagged in `log.md`:**
- Step-ups from PWM < 150 (below breakaway) — breakaway dynamics never measured.
- Dynamic step-ups to PWM=255 — only a 2-point static spot-check exists, no transient.
- Decel from start PWMs other than 240.
- Mechanism for the reverse high-PWM τ deflation (needs instrumented idle-vs-immediate session pairs + thermistor; declared out of scope).
- Ambient-T logging for future sessions; "Model D" friction extension and higher-order dynamics for PWM=240.

---

## 7. Files inventory

**Notebooks** (`notebooks/`):
- `01_static_map.ipynb` — Phase 1.1 static map; K_fwd/K_rev fits, asymmetry (figs 01–04).
- `03_step_responses.ipynb` — Phase 2.1 accel+decel FOPDT (heuristic→curve_fit), implicit static cross-val, synthesis (figs 05–11). *(No `02` notebook — Phase 1.2 was manual.)*
- `04_validation.ipynb` — Phase 2.2 LOOCV; builds `simulate_model_C` (figs 12–13).
- `05_gap_fill.ipynb` — Phase 2 gap-fill fits, drift analysis, combined LOOCV (figs 14–19).

**Firmware** (`firmware_archive/` + `src/`):
- `src/main.cpp` — **active**; byte-identical to `step_response_v2.cpp` (automated 46-trial gap-fill sequencer, `GO`/`STOP`/`?`).
- `firmware_archive/manual_mode_v1.cpp` — manual-mode baseline (single-char commands; used for Phase 1.1/1.2 sweeps).
- `firmware_archive/step_response_v1.cpp` — automated 30-trial Phase 2.1 sequencer.
- `firmware_archive/step_response_v2.cpp` — automated 46-trial gap-fill sequencer (mirror of `src/main.cpp`).
- `src/main.cpp.bak` — **leftover**; byte-identical to `manual_mode_v1.cpp` (redundant).

**Scripts** (`scripts/`):
- `capture_serial.py` — opens 230400-baud serial, sends `GO`, logs until `SEQUENCE COMPLETE` / 30 s silence (GO-based firmware only).
- `split_log.py` — splits a `=== START/END ===` serial log into per-trial CSVs (works for v1 and v2 logs).

**Processed CSVs** (`data/processed/`):

| File | Rows | Description | Consumed by |
|---|---:|---|---|
| `phase21_fopdt_per_trial.csv` | 18 | Accel **heuristic** (63.2%) per-trial — *superseded* | (none) |
| `phase21_fopdt_per_condition.csv` | 6 | Accel heuristic per-condition — *superseded* | (none) |
| `phase21_fopdt_curvefit_per_trial.csv` | 18 | Accel curve_fit per-trial (locked) | nb04, nb05 |
| `phase21_fopdt_curvefit_per_condition.csv` | 6 | Accel curve_fit per-condition (locked) | nb04, nb05 |
| `phase21_stepdown_curvefit_per_trial.csv` | 12 | Decel curve_fit per-trial | nb04, nb05 |
| `phase21_stepdown_curvefit_per_condition.csv` | 4 | Decel curve_fit per-condition | nb04, nb05 |
| `phase21_xval_static_consistency.csv` | 6 | Step-SS vs sweep disagreement — **orphan** (no notebook writes/reads it) | (none) |
| `phase21_loocv_accel.csv` | 18 | P2.2 accel LOOCV per-trial | terminal |
| `phase21_loocv_decel.csv` | 12 | P2.2 decel LOOCV per-trial | terminal |
| `phase21_loocv_summary.csv` | 10 | P2.2 LOOCV per-condition summary | nb05 |
| `phase2gapfill_fopdt_accel_per_trial.csv` | 20 | Gap-fill accel (180/220) per-trial | terminal |
| `phase2gapfill_fopdt_accel_per_condition.csv` | 4 | Gap-fill accel per-condition | terminal |
| `phase2gapfill_stepdown_per_trial.csv` | 18 | Gap-fill decel (100/180/220) per-trial | terminal |
| `phase2gapfill_stepdown_per_condition.csv` | 6 | Gap-fill decel per-condition | terminal |
| `phase2gapfill_loocv_accel.csv` | 20 | Gap-fill accel LOOCV per-trial | terminal |
| `phase2gapfill_loocv_decel.csv` | 18 | Gap-fill decel LOOCV per-trial | terminal |
| `phase2gapfill_loocv_summary_combined.csv` | 20 | P2.2 (10) + gap-fill (10) LOOCV summary | terminal |

**Figures** (`figures/`):
1. `01_pwm_vs_vmean.png` — PWM vs V_motor, fwd/rev, deadzone line.
2. `02_pwm_vs_rpm.png` — PWM vs steady RPM, fwd/rev.
3. `03_vmean_vs_rpm.png` — V_motor vs RPM with K_fwd/K_rev through-origin fits.
4. `04_asymmetry_ratio.png` — |rev|/fwd voltage and RPM ratios vs PWM.
5. `05_fopdt_fwd_200_run01.png` — single-trial heuristic FOPDT (fwd 200 run01).
6. `06_fopdt_6condition_grid.png` — heuristic FOPDT, 6 accel conditions (run01).
7. `07_tau_td_vs_pwm.png` — heuristic τ and Td vs PWM, fwd/rev ±std.
8. `08_fopdt_curvefit_residuals.png` — curve_fit FOPDT + residual subpanels, 6 accel.
9. `09_stepdown_fwd_240_to_160_run01.png` — single step-down fit + residual.
10. `10_stepdown_4condition_grid.png` — curve_fit step-down, 4 decel conditions + residuals.
11. `11_phase21_tau_synthesis.png` — τ bar chart across all P2.1 accel+decel.
12. `12_phase22_loocv_summary.png` — LOOCV RMSE vs in-sample floor, 10 conditions.
13. `13_phase22_loocv_grid.png` — 30-panel measured-vs-predicted appendix grid.
14. `14_phase2gapfill_piggyback_overlay.png` — piggyback (2 runs) vs P2.1 run01, 4 conditions.
15. `15_phase2gapfill_warmup_trend.png` — piggyback τ and |K_ss| vs trial order.
16. `16_phase2gapfill_accel_tau_vs_pwm.png` — accel τ & |K_ss| vs PWM (P2.1+gap-fill+piggyback).
17. `17_phase2gapfill_decel_tau_vs_target.png` — decel τ & |y_final| vs target PWM.
18. `18_phase2gapfill_decel_overlays.png` — decel trajectory overlays, P2.1 vs gap-fill (2×3).
19. `19_loocv_phase22_vs_gapfill.png` — side-by-side LOOCV bars, P2.2 vs gap-fill.

**Raw data** (`data/raw/`): `static_sweep_20260506_run1.csv` (Phase 1.1, 52 rows); `deadzone_manual_run01.csv` (Phase 1.2, 4 rows); `spot_check_max_pwm_2026-05-06_evening.csv` (2 rows); `session_log.csv` (gap-fill ambient T); `step_responses/` (30 Phase 2.1 trial CSVs); `step_responses_gapfill/` (46 gap-fill trial CSVs); `serial_logs/` (2 raw session logs). Supporting: `datasheets/`, `freecad_macros_motor_encoder/`, `data/templates/`, `data/metadata/`.

---

## 8. Thesis-writing readiness check

**Phase → chapter mapping (decided 2026-05-21):** Phase 0 (encoder-sign / scope verification) → **Hardware** chapter as a commissioning note · Phase 1.1 (static map) + Phase 1.2 (deadzone hysteresis) → **Static characterization** · Phase 2.1 + Phase 2.2 + gap-fill → **Dynamic characterization** + **Validation** together.

| Chapter | Status | Blocker / caveat |
|---|---|---|
| **Hardware** | **Ready** | Fully documented (`PIN_CONFIGURATION.md`, firmware, datasheets, FreeCAD). Only nit: `CLAUDE.md` mis-describes the active firmware (§9). |
| **Static characterization** | **Ready (with caveat)** | K_fwd/K_rev, deadzone hysteresis, asymmetry all locked and CSV-verified. Caveat: rests on a **single** static sweep run (`run1`); `log.md` claims run02/run03 were collected but they are **absent from the repo** — reproducibility is instead argued via the 2-point spot-check + Phase 2.1 implicit cross-val. **Decided (2026-05-21):** commit to *single sweep + 2-point spot-check (PWM ±255) + Phase 2.1 implicit cross-validation* as the reproducibility argument — two independent verifications; run02/run03 not required. |
| **Dynamic characterization** | **Ready (with caveat)** | 10 accel + 10 decel FOPDT conditions, all fits succeeded, figures done. Caveat: parameters span **two sessions** (P2.1 + gap-fill, 2 weeks apart); the consolidated tables mix sessions — document the drift (§5) and note which rows came from which session (done in §4 tables). |
| **Validation** | **Ready (with caveat)** | LOOCV methodology + results complete for both phases. Caveat: LOOCV only — **no held-out dataset** and **no separate-session held-out test**; validity is within-grid (no extrapolation test). The `_sealed/` set never existed. |
| **Closed-loop** | **Not started** | Blocked on all of: multi-transition simulator v2, closed-loop (PID) firmware, a fresh bench session with in-session calibration, and a naive-LTI baseline to compare against. No closed-loop data exists. This is the main remaining thesis deliverable. |

---

## 9. Inconsistencies, orphans, and ambiguities found

**Documentation vs reality:**
1. **`CLAUDE.md` mis-describes the active firmware.** It says `src/main.cpp` is *manual-mode* (commands `f`/`r`/`s`/`z`/`?`). In fact `src/main.cpp` is **byte-identical to `step_response_v2.cpp`** (the automated 46-trial `GO`-based gap-fill sequencer). `AGENTS.md` is correct; `CLAUDE.md` §"Firmware variants" is stale.
2. **No `thesis_notes/handover_*.md` file exists.** Only `log.md` and `work_done.md` are present. "Handovers" are referenced *inside* `log.md` ("Original handover specified…", "Previous handover (2026-05-07)…") but exist only as references. `work_done.md` is an 18-line Phase 0/1.1 stub, not a handover. (The handovers were likely chat-session artifacts never committed.)
3. **`firmware/` directory does not exist.** The gap-fill `log.md` entry lists "Files added: `firmware/step_response_v2.cpp`", but firmware lives in `firmware_archive/` (+ `src/main.cpp`). Same loose path appears in your task description.
4. **Combined-LOOCV row count is mis-stated everywhere.** `AGENTS.md`, `log.md`, and the print in `notebooks/05_gap_fill.ipynb` cell 9 all say "10 P2.2 + 6 gap-fill" (=16). The actual `phase2gapfill_loocv_summary_combined.csv` has **20 rows = 10 P2.2 + 10 gap-fill** (4 accel + 6 decel). The "6 gap-fill" undercount omits the 4 accel gap-fill conditions (PWM 180/220 × fwd/rev).
5. **Phase 1.1 run02/run03 raw CSVs are missing.** `log.md` (2026-05-06 evening) says they "also collected", but only `static_sweep_20260506_run1.csv` is in `data/raw/`. **Resolved (2026-05-21):** run02/run03 are not required — the thesis commits to single sweep + spot-check + implicit cross-val (§8); the `log.md` "also collected" line should be corrected or dropped.

**Orphan / superseded / leftover files:**
6. **`phase21_xval_static_consistency.csv` — orphan.** Its content matches nb03's implicit cross-validation (cells 4–5), but **no current notebook writes or reads it**, and nothing references it (the save step is absent from nb03). Provenance unclear / save cell removed.
7. **`phase21_fopdt_per_trial.csv` + `phase21_fopdt_per_condition.csv` — superseded.** These are the 63.2% heuristic fits, replaced by the `_curvefit_` versions and **not consumed by nb04/nb05**. Not part of the live model. **Decided (2026-05-21): keep** as a thesis-appendix audit trail of the heuristic→curve_fit promotion.
8. **`src/main.cpp.bak` — redundant.** Byte-identical to `firmware_archive/manual_mode_v1.cpp`; the manual-mode firmware is already archived.
9. **`session_log.csv` — corrected 2026-05-21.** The erroneous `,,40 deg celsius` row (mistakenly entered as ambient temperature) has been **removed**. Remaining ambient: 27.3 °C (before) / 28.8 °C (after), matching `log.md`. Timestamps remain empty (not load-bearing).
10. **Stale Phase 0-1 docs.** `README.md` and `manual.md` describe the original manual workflow (`CLAUDE.md` already flags this). `figures/README.md`, `models/README.md`, `data/processed/README.md` are generic boilerplate that doesn't describe current contents. `models/` holds **no artifacts** — identified parameters live only in `data/processed/` + notebooks.

**Consistency checks that PASSED (CSV vs prose):** K_fwd/K_rev (26.94/24.52), deadzone 154/144 & 114/112, all Phase 2.1/gap-fill FOPDT per-condition numbers, LOOCV group means (+1.06/+0.10 accel/decel P2.2; −0.05/+0.45 gap-fill; worst fwd-160 +1.97, worst gap-fill rev 240→100 +1.06), and the `src/main.cpp ≡ step_response_v2.cpp` claim — all reconcile exactly.

### Resolved decisions (2026-05-21)

- **Phase numbering:** Phase 0 → Hardware (commissioning note); Phase 1.1 + 1.2 → Static characterization; Phase 2.1 + 2.2 + gap-fill → Dynamic + Validation. (See §8 mapping.)
- **Static reproducibility:** commit to single sweep + 2-point spot-check + Phase 2.1 implicit cross-validation; run02/run03 not required.
- **`session_log.csv` "40 deg celsius":** confirmed erroneous (mistaken ambient entry) — removed from the raw file (see §9.9).
- **Cross-session §4 tables:** keep P2.1 and gap-fill side-by-side with the `Session` column + drift caveats — the honest representation for the open-loop thesis. A single-session re-fit waits for the Phase 3 bench session.
- **Orphan/superseded files:** keep `phase21_fopdt_per_*.csv` (heuristic) as thesis-appendix audit trail. `phase21_xval_static_consistency.csv` and `src/main.cpp.bak` left in place (not deleted) — flagged for optional later cleanup.

### Still open (off-repo / your call)

- The "Consistency checks that PASSED" note above and the §3/§4 numbers are final. The only doc-hygiene follow-ups, if you want them, are correcting the stale claims at their source: `CLAUDE.md` firmware section (§9.1), the `log.md`/`AGENTS.md` "6 gap-fill" / "firmware/" lines (§9.3–9.4), and the `log.md` "run02/run03 also collected" line (§9.5). I did not edit those source docs — say the word and I will.
