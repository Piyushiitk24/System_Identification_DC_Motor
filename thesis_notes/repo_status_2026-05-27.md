# Repository Status — DC Motor System Identification (Phase 3 included)

**Generated:** 2026-05-27 · **Branch:** main · **Supersedes:** `repo_status_2026-05-21.md` (model-ladder snapshot, pre-Phase-3). · **Author tooling:** full read-through of notebooks, firmware, scripts, processed CSVs, figures, and thesis notes; numbers re-pulled from `data/processed/*.csv` and `data/raw/`.

This update preserves the previous status-doc's structure but folds in Phase 3 closed-loop results. The rule remains *CSV wins*: prose in `log.md`/`AGENTS.md`/notebooks loses to the processed CSV when they disagree, and the discrepancy is flagged. Numerical claims about Phases 1–2 are unchanged from the 2026-05-21 doc; refer there for the full Phase-1/2 cross-checks. This doc focuses on the Phase 3 delta and what it changes about the overall thesis state.

---

## 1. Project overview (Phase 3 update)

The thesis is now both an open-loop **system identification** of a DC-motor + L298N rig (Arduino Uno R4 Minima, 12 V geared motor, 600 PPR quadrature encoder) **and** a closed-loop validation of the structural choice the identification produced. The identified model is the cascade `PWM → static driver block → motor dynamic block → RPM` (Model C, Tables 4.1–4.2). Phase 3 (2026-05-27) tested whether Model C is a measurably better closed-loop controller than a single-LTI baseline (Model A) tuned from the same in-session data; the answer is mixed and specific (§4.5 below).

Operational note unchanged: the static "driver-voltage" block is the physical/conceptual justification. The operational Model C simulator (`motor_id/cascade_sim.py`, formerly the inline notebook simulators) works directly in PWM→RPM space with the voltage block absorbed into per-condition `K_ss`.

---

## 2. Hardware setup

Unchanged from `repo_status_2026-05-21.md` §2. Closed-loop firmware uses the same pins, encoder chain, PWM frequency, and serial baud as the open-loop firmware. Active open-loop firmware remains `src/main.cpp` (Phase 2 gap-fill sequencer); Phase 3 firmware is `src_closedloop/main.cpp`, built via `platformio_closedloop.ini` (a separate `.ini` so the open-loop default `pio run` is unchanged).

---

## 3. Experimental phases (Phase 3 added)

Phases 1.1, 1.2, 2.1, 2.2, and gap-fill: unchanged. See `repo_status_2026-05-21.md` §3 for those.

### Phase 3 — Closed-loop validation (2026-05-27, single session)

**Goal:** Test whether a cascade-aware controller (CASC: Model C + region PI + inverse-static FF) tracks references better than a single-LTI baseline (BASE: Model A IMC PI) on the same rig, tuned from the same in-session calibration.

**Firmware/protocol:** `src_closedloop/main.cpp` running on the Uno R4 Minima at the standard wiring. One 2026-05-27 session, ~75 min motor-on, ~2 h wall-clock. Driver: `scripts/bench_session.py`.

**Pre-registration:** committed to `data/processed/phase3_preregistration.json` (SHA-256 `da94c83d3b57bda80cf3a137740ed7441f41df2424da909098a2d63602707669`) before any closed-loop trial ran, persisted from `notebooks/07a_closed_loop_sim.ipynb` Cell G. Metrics, success criteria, statistical procedure all fixed before bench day.

**Stages:**

1. **Warm-up** (no logged trials): +200 PWM fwd 20 s → 0 5 s → −200 PWM rev 20 s → 0 10 s. ~55 s motor-on.
2. **CALIB** — 30 open-loop trials: accel PWM ∈ {160, 200, 240} × {fwd, rev} × 3 + decel 240 → {0, 160} × {fwd, rev} × 3. Splits to per-trial CSVs under `data/raw/closed_loop_2026-05-27/calib_trials/`.
3. **On-laptop refit** (motor idle): FOPDT per condition; Model A globally; IMC gains and FF table built; persisted to `models/calibration_2026-05-27.json` and `models/closed_loop_gains_2026-05-27.json`; uploaded to firmware. **Gains frozen.**
4. **Closed-loop trials** — n = 8 paired runs per (profile × {BASE, CASC}). 64 trials total. Pair order randomised within profile (seed = 20260527); controller order within pair randomised. Each trial captured to its own CSV under `data/raw/closed_loop_2026-05-27/closed_loop_trials/<profile>_pair<NN>_<CTRL>.csv`. Pair structure recorded in `trial_index.json`.
5. **DRIFT** — 6 end-of-session trials: fwd/rev PWM = 200 accel × 3 each.

**Notebooks:** `07a_closed_loop_sim.ipynb` (pre-registration + sim), `07b_closed_loop_results.ipynb` (bench analysis + pre-registered tests).

---

## 4. Final model state (Phase 3 additions)

### 4.1 Static block — unchanged

See `repo_status_2026-05-21.md` §4.1. Phase 3 used the within-session breakaway/dropout PWMs (computed dynamically from the inverse-static map of the session Model C) for the FF table.

### 4.2–4.3 Dynamic block (FOPDT tables) — unchanged

See `repo_status_2026-05-21.md` §4.2–§4.3 for the locked Phase 2.1 + gap-fill tables. Phase 3 used a *session-fresh* Model C fit from the 2026-05-27 calibration block, not the locked tables (which would have given an overdamped baseline — see §4.5).

### 4.4 Within-grid validation (LOOCV) — unchanged

See `repo_status_2026-05-21.md` §4.4.

### 4.5 Phase 3 closed-loop validation (new)

**Session calibration models (`models/calibration_2026-05-27.json`):**

| Quantity | Phase 2.1 locked | 2026-05-27 session | Δ |
|---|---:|---:|---:|
| Model A `K_A` (rpm/PWM) | 0.785 | 0.737 | −6.1 % |
| Model A `τ` (ms) | 207 | 155 | −25 % |
| Model A `T_d` (ms) | 19.8 | 6.6 | −67 % |

The session τ is sharply shorter than the locked value. Reusing the locked numbers would have designed a baseline controller with closed-loop bandwidth ~30 % too low — i.e., overdamped. This directly tests and confirms the §5.6 "recalibrate in situ" recommendation.

**Pre-registered paired RMSE result (`closed_loop_metrics_per_trial.csv`, n = 8 paired per profile):**

| Profile | median(BASE − CASC) rpm | mean (rpm) | 95 % bootstrap CI | Wilcoxon p (one-sided "greater") | Sim prediction |
|---|---:|---:|---:|---:|---:|
| P1 (staircase)        | **+2.82** | +2.83 | [+2.74, +2.93] | 0.004 | +2.20 |
| P2 (deadzone ramp)    | **−1.13** | −1.09 | [−1.20, −0.97] | 1.000 | +4.21 |
| P3 (reversal)         | **+5.15** | +5.22 | [+5.04, +5.40] | 0.004 | +9.15 |
| P4 (small-signal)     | **+1.00** | +1.03 | [+0.86, +1.22] | 0.004 | +0.92 |

Pooled (MAD-standardised) Wilcoxon over P1+P2+P3: pooled-mean 21.3, n = 24, p = 3 × 10⁻⁴.

**Pre-registered tests applied:**

- **Primary:** required `median > 0` on each of P1, P2, P3 AND pooled MAD-standardised Wilcoxon p < 0.10. **FAIL** — P2's median is −1.13.
- **Strong:** required Primary plus 95 % CI excludes zero on ≥ 2 of P1/P2/P3. **FAIL** — Primary fails. (Note: CIs *do* exclude zero on P1 and P3, so the "≥ 2 of 3" sub-condition is met; it is Primary's median-sign condition that breaks the conjunction.)
- **Fairness gate** (cascade RMS PWM ≤ 1.5 × baseline RMS PWM, on every profile): **PASS**. Effort ratios:

  | Profile | BASE RMS PWM | CASC RMS PWM | ratio |
  |---|---:|---:|---:|
  | P1 | 172.98 | 171.41 | 0.991 |
  | P2 | 168.24 | 168.68 | 1.003 |
  | P3 | 165.58 | 171.68 | 1.037 |
  | P4 | 209.47 | 211.41 | 1.009 |

  Cascade is not winning anywhere by hammering harder.

**Headline interpretation.** Cascade wins decisively on P1, P3, P4; cascade loses on P2. The pre-registered "wins universally" hypothesis is therefore falsified, in a specific way. Mechanism (§4.6 of `draft_ch6_closedloop.md`): the inverse-static FF saturates at the breakaway PWM for |ref| ≤ 50 rpm (since the motor cannot sustain steady motion at lower speeds), giving the FF curve a slope discontinuity at the breakaway-RPM edge. On *step* references this is helpful — the FF jumps to the right neighbourhood immediately. On *slow ramps through zero* the discontinuity is a small piecewise-constant injection that breaks the smoothness the baseline PI integrator would produce. The cascade is therefore the right closed-loop structure for stepwise tracking; the wrong structure, without modification, for slow ramps through the deadzone.

**Sim-vs-reality.** P1 (+2.20 → +2.83), P3 (+9.15 → +5.22), P4 (+0.92 → +1.03) are all sim-direction consistent with reality, with magnitudes within 2× of prediction. P2 (+4.21 → −1.09) is a sign reversal — the simulation, which used the FF lookup as its plant's static block too, did not capture the FF-discontinuity penalty that emerged in real hardware. This is the most informative sim-reality gap of the study and the most specific lead for future controller refinement.

### 4.6 Within-session drift (`closed_loop_drift_check.csv`)

| Direction | PWM | ΔK_ss (start → end) | Δτ (start → end) | n_start | n_end |
|---|---:|---:|---:|---:|---:|
| fwd | 200 | +6.7 % | −5.2 % | 3 | 3 |
| rev | 200 | +3.7 % | −2.5 % | 3 | 3 |

Consistent with L298N junction warming (saturation drop falls, more motor voltage at the same PWM). Forward drift larger than reverse, matching the §3.8 asymmetry pattern. Small enough not to affect within-pair pairing (pair members run within seconds of each other) but enough to recommend in-session calibration for any future closed-loop work.

---

## 5. Limitations and known issues (Phase 3 additions)

In addition to the Phase-1/2 limitations in `repo_status_2026-05-21.md` §5:

- **Single closed-loop session.** All 64 paired Phase 3 trials are from one bench day. Cross-session reproducibility of the *closed-loop* result (separate from open-loop drift) is not measured.
- **No external disturbance.** Reference profiles are deterministic; no load disturbance, no brake. Cascade's advantage on step profiles is therefore a *tracking* advantage; load-disturbance rejection isn't tested. Since the FF is `f(ref)` only, a disturbance test would also serve as a pure PI-tuning fairness check.
- **PI only, no D term.** RPM quantisation (2.5 rpm) makes a D term noisy without an LP filter; both controllers are PI to keep the BASE-vs-CASC comparison purely about model structure.
- **FF resolution.** The FF table has 5 RPM points per direction. Denser sampling near the deadzone edge would refine FF curvature but per §4.5 the P2 issue is structural (slope discontinuity), unlikely to be flipped by resolution alone.

---

## 6. What's NOT been done (Phase 3 update)

- **Smoothed-FF cascade variant.** The natural follow-up: replace the breakaway-saturated FF with a smooth taper through the deadzone, re-run P2 (and others). Most direct test of the §4.5 mechanism.
- **Cross-session closed-loop reproducibility.** Phase 3 used n = 1 session; n ≥ 2 sessions would bound the session-to-session variance of the per-profile BASE − CASC.
- **Disturbance-rejection trials.** Phase 3 tested tracking only.
- **Friction-explicit Model D.** Mentioned in Phase-2 future work; would also smooth the static block through the deadzone, possibly addressing P2 via a different route.
- All Phase-1/2 "not done" items from `repo_status_2026-05-21.md` §6 remain open.

---

## 7. Files inventory (Phase 3 additions)

**Code (new):**

- `motor_id/__init__.py`, `motor_id/cascade_sim.py`, `motor_id/controllers.py`, `motor_id/model_io.py`, `motor_id/metrics.py`, `motor_id/calibration.py` — Python package for the closed-loop work.
- `src_closedloop/main.cpp` — Phase 3 firmware.
- `platformio_closedloop.ini` — separate PIO env.
- `scripts/smoke_closed_loop.py` — Stage-1 smoke driver.
- `scripts/bench_session.py` — full Stage-2 bench orchestrator.

**Notebooks:**

- `notebooks/07a_closed_loop_sim.ipynb` — pre-registration freeze, sim-only A-vs-C.
- `notebooks/07b_closed_loop_results.ipynb` — bench analysis, pre-registered tests.

**Models (new):**

- `models/calibration_2026-05-27.json` — session-fresh Model A and Model C fits.
- `models/closed_loop_gains_2026-05-27.json` — frozen IMC gains and FF table.

**Raw data:**

- `data/raw/closed_loop_2026-05-27/calib_trials/` — 30 calibration CSVs.
- `data/raw/closed_loop_2026-05-27/closed_loop_trials/` — 64 closed-loop CSVs (named `<profile>_pair<NN>_<CTRL>.csv`).
- `data/raw/closed_loop_2026-05-27/drift_trials/` — 6 drift-check CSVs.
- `data/raw/closed_loop_2026-05-27/trial_index.json` — pair structure metadata.
- `data/raw/serial_logs/2026-05-27_phase3_session.log` — full session serial log.

**Processed:**

- `data/processed/closed_loop_metrics_per_trial.csv` — 64 rows, all pre-registered metrics.
- `data/processed/closed_loop_summary.json` — pre-registered test outcomes, headline numbers.
- `data/processed/closed_loop_drift_check.csv` — start-vs-end PWM=200 accel drift.
- `data/processed/phase3_preregistration.json` — committed pre-registration (SHA-256 above).
- `data/processed/closed_loop_sim_metrics.csv` — sim predictions (pre-bench-day).

**Figures:**

- `figures/23_closed_loop_paired_diff.png` — per-profile paired RMSE diff with 95 % CIs (= thesis Fig 6.1).
- `figures/24_closed_loop_trajectories.png` — representative trajectories per profile per controller (= thesis Fig 6.2).
- `figures/nb07a_profiles.png`, `figures/nb07a_trajectories.png` — sim-only outputs.

---

## 8. Thesis-writing readiness check

- **Ch6 (Closed-Loop Validation):** rewritten from "plan" to **results** in `draft_ch6_closedloop.md` and `thesis/Chapters/Chapter_6/Chapter6.tex`. Now includes Table 6.1 (paired RMSE), Table 6.2 (drift), Figures 6.1–6.2.
- **Ch1 (Introduction):** updated. Outline and Contributions reflect Phase 3 outcomes (not "deferred").
- **Ch7 (Conclusion):** updated. Adds a Phase 3 finding paragraph; rewrites Future Work to lead with the smoothed-FF variant; Closing reflects the mixed result.
- **Ch2–Ch5:** unchanged.
- **Status-doc (this file):** complete; supersedes `repo_status_2026-05-21.md`.
- **`log.md`:** Phase 3 entry appended (2026-05-27).
- **`AGENTS.md`, `CLAUDE.md`:** project-state sections updated to point at Phase 3 artifacts and conclusions.
- **`thesis/main.pdf`:** **rebuild pending.** Will include Chapter 6 in its rewritten form once `latexmk -pdf main.tex` is rerun.

---

## 9. Inconsistencies, orphans, and ambiguities found

No new ones introduced by Phase 3. The §9 of `repo_status_2026-05-21.md` items are unchanged. Phase 3 specifically *tested* one open question from that section ("Phase 3 needs in-session recalibration") and **confirmed it** (§4.5 above): the session τ is 25 % lower than the locked value, exactly the kind of drift that would have invalidated a stale-calibration baseline controller.
