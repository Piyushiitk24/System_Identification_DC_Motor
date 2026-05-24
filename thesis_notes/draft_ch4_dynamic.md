# Chapter 4 — Dynamic Characterization

> **Draft status:** first full pass, 2026-05-21. Markdown; converts to LaTeX mechanically. All parameter values trace to `data/processed/phase21_fopdt_curvefit_per_condition.csv`, `phase21_stepdown_curvefit_per_condition.csv`, `phase2gapfill_fopdt_accel_per_condition.csv`, `phase2gapfill_stepdown_per_condition.csv`, and status-doc §4.2–§4.3. Figures `05`–`11`, `16`–`18`. Covers Phase 2.1 step responses and the Phase 2 gap-fill conditions.

## 4.1 Objective

Chapter 3 fixed the steady-state map; this chapter identifies how the motor moves *between* operating points. The transient is modelled as a first-order-plus-dead-time (FOPDT) response, and the central questions are structural: is one global time constant enough, or does the dynamic behaviour depend on operating point, on direction, and on whether the motor is speeding up or slowing down? The answers define the working model — termed **Model C** — as a cascade in which a static block (Chapter 3) feeds a dynamic block whose parameters are indexed by direction and by acceleration/deceleration region.

## 4.2 Method

**Trials.** Step responses were collected with the automated sequencer firmware (Section 2.7), which removes operator timing variability. Acceleration ("step-up") trials drive the motor from rest to a target PWM; deceleration ("step-down") trials hold PWM = 240 to a settled speed and then step down to a target. The Phase 2.1 session covered PWM ∈ {160, 200, 240} accel (×3 runs) and 240→{0, 160} decel (×3 runs); the gap-fill session added PWM ∈ {180, 220} accel (×5 runs) and 240→{100, 180, 220} decel (×3 runs), plus eight piggyback re-runs of Phase 2.1 conditions (Section 4.6). The piggyback re-runs are not folded into Tables 4.1–4.2; they are reported separately as the cross-session drift signal and quantified in Chapter 5.

**Model.** Acceleration is fitted as a rise from rest,
$$\text{rpm}(t) = K_{ss}\,\bigl(1 - e^{-(t - t_0 - T_d)/\tau}\bigr),$$
and deceleration as a decay between two levels,
$$\text{rpm}(t) = y_\text{final} + (y_\text{init} - y_\text{final})\,e^{-(t - t_0 - T_d)/\tau},$$
with gain `K_ss` (or the level pair `y_init, y_final`), dead time `T_d`, and time constant `τ`.

**Fitting.** Each trial is fitted in two stages: a 63.2 %-rise heuristic provides robust initial estimates, then `scipy.optimize.curve_fit` refines them under physical bounds. The bounds enforce τ ∈ [10, 1000] ms and T_d ∈ [0, 200] ms; the gain is sign-constrained by direction with magnitude up to twice the heuristic estimate (and, for deceleration, the level pair bounded to ±400 rpm), while t_0 is fixed at the step-command index. The heuristic alone snaps `T_d` and `τ` to the 10 ms sample grid; the nonlinear fit yields continuous parameters and per-window residuals (rise, steady-state, total). All fits converged — 18/18 and 12/12 in Phase 2.1, 20/20 and 18/18 in gap-fill. Residual windows are recorded so that validation (Chapter 5) can compare like with like: the rise window for accel, and the post-2000 ms fit window for decel.

## 4.3 Acceleration dynamics

| Dir | PWM | K_ss (rpm) | T_d (ms) | τ (ms) ± std | rms_rise | n | Session |
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

*Table 4.1 — Acceleration FOPDT parameters, all ten operating points.*

Four findings follow.

**(1) τ is operating-point dependent — a broad bathtub.** The time constant is smallest in the mid-range and rises at both ends: τ ≈ 81–110 ms across PWM 180–220, climbing to ≈145–152 ms at PWM = 240 and ≈192–200 ms at PWM = 160 (figures `07`, `16`). The bottom of the curve is flat across a ≈40-PWM window rather than a single sharp minimum — an earlier "V-shape" reading is refined here to a **bathtub**. A single global τ (call it "Model B") is therefore misspecified by roughly 2× across the range; a region-dependent dynamic block (Model C) is required. The rise at PWM = 160 is friction-dominated (the operating point sits just above breakaway); the rise at PWM = 240 reflects departure from first-order behaviour near full drive (back-EMF/saturation), evidenced by the residuals below.

**(2) The gain is linear and direction-clean.** `K_ss` rises smoothly and almost linearly with PWM within each direction, with very tight run-to-run spread (per-condition std ≤ 2 rpm across the five gap-fill runs). The static-block separability of Chapter 3 thus holds across all five calibrated PWMs — the dynamics change with operating point, but the steady gain does not misbehave.

**(3) The dynamic block is direction-symmetric to first order.** At every PWM, τ_fwd and τ_rev agree to within a small margin, with reverse running consistently a few percent faster. The largest gap is at PWM = 200 (fwd 95 ms vs rev 81 ms, ≈15 %), which exceeds the run-to-run scatter and is flagged as a genuine but minor effect — possible static/dynamic coupling or commutation asymmetry — that does not undermine the cascade. Crucially, the *large* directional asymmetry of Chapter 3 does **not** reappear in the dynamics, confirming that asymmetry lives in the static block.

**(4) T_d is an effective parameter, not physical latency.** The fitted dead time is ≈0 at PWM = 160 and inflates to 17–23 ms at PWM = 240 — the opposite of a fixed transport delay. This is the FOPDT model absorbing rise-shape error at the operating-point extremes; the genuine encoder/serial latency (≈10 ms, one sample) is what the heuristic recovers. `T_d` in Table 4.1 should therefore be read as a curve-fit nuisance parameter, and PWM = 200 — where the rise is cleanly first-order (rms ≈ 2.5 rpm) — taken as the canonical operating point. Fit quality degrades away from it: rms_rise climbs to ≈4.7 rpm (PWM 240 fwd) and ≈7.2 rpm (PWM 240 rev), with the residual grid (figure `08`) showing structured, not random, error there.

## 4.4 Deceleration dynamics

| Dir | 240→ | y_init | y_final | T_d (ms) | τ (ms) ± std | rms_decel | n | Session |
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

*Table 4.2 — Deceleration FOPDT parameters, all ten transitions from PWM = 240.*

**(1) Deceleration is slower than acceleration.** In the same operating range, decel τ exceeds every accel τ: 240→160 decays with τ ≈ 275 ms (fwd) / 306 ms (rev), against accel τ of 95–152 ms at PWM 200–240. Speeding up and slowing down are not the same process, which is the primary justification for splitting Model C into separate accel and decel regions.

**(2) Decel τ is non-monotone in the target.** It is *not* simply "slower for bigger steps." The slowest decays are to targets sitting on the deadzone edge — 240→100 and 240→180 (τ ≈ 321–366 ms) — where the shaft must coast through the high-friction low-speed region. A full coast to rest (240→0) is faster (172–190 ms), and a mild decel (240→220) is fastest (109–123 ms). The deadzone, characterized statically in Chapter 3, thus reshapes the *dynamics* of any transition that passes near it (figures `17`, `18`).

**(3) Regenerative braking is suppressed at non-zero targets.** Decel to 160 is slower than decel to 0 even though it is a smaller speed change. The likely cause is that at a non-zero PWM hold the L298N keeps chopping, preventing the regenerative braking that a pure coast (PWM = 0) allows — an artefact of the driver, again localising a behavioural quirk to the static/driver side.

**(4) The direction asymmetry reverses sign between regions.** In acceleration reverse is slightly *faster* (Section 4.3); in deceleration reverse is slightly *slower* (240→160: 306 vs 275 ms; 240→0: 190 vs 172 ms). Equal magnitude, opposite sign. This indicates partial coupling between the static and dynamic blocks — the cascade holds but is not perfectly clean, and this is carried as an explicit thesis caveat. Finally, the coast-to-rest cases (240→0, y_final ≈ 0) are Coulomb-friction-dominated and so only effectively first-order; their residuals (rms ≈ 8.7–9.8 rpm over the decel window) are the largest in the set but remain bounded.

## 4.5 Region structure: the definition of Model C

The findings compose into the working model. The plant is a cascade `PWM → static driver-voltage block (Chapter 3) → motor dynamic block → RPM`, in which the dynamic block is **not** a single LTI system but a family of FOPDT responses indexed by:

- **direction** (forward / reverse) — required by the static block, optional for the dynamics (small effect);
- **region** (acceleration / deceleration) — required, since decel τ ≈ 2× accel τ; and
- **operating point** — accel τ follows a bathtub in PWM; decel τ depends non-monotonically on the target through the deadzone.

This is Model C, the third rung of a candidate ladder fixed at the outset: **Model A**, a single global LTI model with no static block (`u_cmd → rpm`), used only as the straw-man baseline of Chapter 6; **Model B**, the static block followed by one global dynamic block (a single gain, τ, and delay); **Model C**, the static block with a region-dependent dynamic block (this chapter); and **Model D**, an optional friction-explicit refinement. Model B is rejected by the ≈2× spread in τ across operating points; Model C is adopted as the working model; the Coulomb/Stribeck Model D, motivated by the PWM = 160 and coast-to-rest residuals, is left to future work.

## 4.6 Cross-session note

Tables 4.1 and 4.2 combine two bench sessions two weeks apart: PWM 160/200/240 and targets 0/160 from Phase 2.1, and PWM 180/220 and targets 100/180/220 from the gap-fill session (`Session` column). The bathtub and target-dependence framings rely on combining both. Within either session, reproducibility is excellent (run-to-run τ std mostly ≤ a few ms). Between sessions there is structured drift — most visibly, the gap-fill reverse high-PWM τ runs ≈20 % below its Phase 2.1 value (≈114 vs 144 ms in the piggyback re-runs), and low-speed-target decel runs slower than Phase 2.1 interpolation would predict. The consolidated tables are therefore an honest two-session composite, and the magnitude and structure of the drift are quantified as a validation result in Chapter 5 rather than smoothed over here.

## 4.7 Summary

The motor's transient response is well captured, operating point by operating point, as FOPDT. The dynamics are operating-point dependent (accel τ a broad bathtub, 81–200 ms), region dependent (decel τ ≈ 2× accel, and non-monotone through the deadzone), and only weakly direction dependent — with the direction asymmetry switching sign between accel and decel, a small but real departure from a perfectly clean cascade. The fitted dead time is an effective parameter; PWM = 200 is the canonical clean FOPDT point, and the extremes are effective fits with bounded, structured residuals that motivate a future friction-explicit model. The twenty-condition parameter set of Tables 4.1–4.2 is the dynamic block of Model C; Chapter 5 tests how well it predicts held-out trials and how far it transfers across runs and sessions.

---

### Sources for this chapter
`data/processed/phase21_fopdt_curvefit_per_condition.csv`, `phase2gapfill_fopdt_accel_per_condition.csv` (Table 4.1) · `phase21_stepdown_curvefit_per_condition.csv`, `phase2gapfill_stepdown_per_condition.csv` (Table 4.2) · `notebooks/03_step_responses.ipynb`, `05_gap_fill.ipynb` (fits, figures 05–11, 16–18) · status-doc §4.2–§4.3, §5 · `thesis_notes/log.md` 2026-05-07 / 2026-05-22 (interpretation, accel/decel asymmetry, bathtub refinement).
