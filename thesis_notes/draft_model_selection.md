# §4.6 — Model selection: the A/B/C ladder, quantified

> **Draft status:** first pass, 2026-05-25. Markdown; converts to LaTeX mechanically. Standalone
> section — slot into Chapter 4 as **§4.6** (renumbering the present cross-session note to §4.7 and
> the summary to §4.8), or use it to open Chapter 5 as a model-selection preamble before the
> generalisation tests. All numbers trace to `data/processed/phase21_model_ladder_summary.csv` and
> `notebooks/06_model_comparison.ipynb`; figures `20`–`21`. Comparison dataset: the Phase 2.1 grid
> (30 trials, single session).

Section 4.5 *defined* the candidate ladder and adopted Model C on structural grounds. This section
makes the choice quantitative: rather than dismiss the simpler models by argument, it **fits them
to the same data** and scores all three head-to-head, so that the superiority of the cascade — and
the separate contributions of its two ideas, the static block and the region-dependent dynamics —
can be read off directly, forward and reverse.

## The three models, fit on a common footing

All three predict an RPM trajectory from a PWM step and are simulated with the identical FOPDT
core used for validation (Chapter 5), so differences are due to model *structure*, not numerics.

- **Model A — naive global LTI.** No static block: a single proportional gain maps command to
  speed, `rpm = K_A·pwm`, followed by one global first-order-plus-dead-time. Fit over all thirty
  trials, `K_A = 0.785 rpm/PWM`, `τ = 207 ms`, `T_d = 20 ms`. This is the textbook model an
  engineer reaches for, and the straw man of Section 4.5.
- **Model B — static block + one global dynamic block.** The static block supplies the correct
  per-operating-point steady state (the deadzone and the direction-specific gain of Chapter 3),
  but a **single** global time constant governs every transition: `τ = 187 ms`, `T_d = 16 ms`.
- **Model C — the cascade.** The static block plus the **region- and operating-point-dependent**
  FOPDT of Tables 4.1–4.2 (unchanged).

The pairing is deliberate. **A → B isolates the value of the static block**; **B → C isolates the
value of region-dependent dynamics.**

## Results

Each trial is scored on its post-step window by RMSE and by the normalised fit
`FIT% = 100·(1 − ‖y − ŷ‖ / ‖y − ȳ‖)`, where `FIT% = 0` means "no better than predicting the mean."

| Region · direction | RMSE A | RMSE B | RMSE C | FIT% A | FIT% B | FIT% C |
|---|---:|---:|---:|---:|---:|---:|
| accel · fwd | 42.1 | 6.0 | **3.8** | −332 | 56.6 | **71.8** |
| accel · rev | 38.4 | 7.2 | **4.3** | −191 | 53.9 | **73.4** |
| decel · fwd | 28.3 | 6.7 | **4.3** | −13 | 76.4 | **85.2** |
| decel · rev | 24.4 | 8.3 | **3.8** | +11 | 73.3 | **88.7** |
| **overall (30)** | **34.7** | **6.96** | **4.07** | **−157** | **63.1** | **78.3** |

*Table 4.3 — Post-step RMSE (rpm) and FIT% by region and direction. Model C is best in every
group, forward and reverse. (Figure 21.)*

Three readings follow, and they hold in both directions.

**(1) Model A fails outright.** Its FIT% is *negative* in three of four groups — the naive model
predicts the step responses worse than a horizontal line through their mean. With no static block,
its single gain cannot represent the deadzone, so it overshoots heavily at low PWM (at PWM = 160 it
predicts ≈125 rpm against a measured ≈52). Figure 20 shows the symptom directly: A reaches the
wrong level and rises with the wrong shape. This is the empirical justification — not the
assumption — that a low-cost H-bridge drive cannot be treated as a single linear system.

**(2) The static block is the dominant improvement (A → B).** Restoring the deadzone and the
direction-specific steady-state map collapses overall RMSE from ≈35 to ≈7 rpm and lifts FIT% from
−157 to +63 %. The single largest gain in the whole study comes from *decomposing* the plant — the
central claim of the cascade, here measured.

**(3) Region-dependent dynamics are a real, smaller gain (B → C).** Model C lowers overall RMSE
further to ≈4 rpm and FIT% to ≈78 %. The improvement is modest on the full window — dominated by
the (shared) steady state — but it concentrates exactly where Section 4.3 predicts: in the
**transient**. Scored on a transient window (five time constants), Model C's error is ≈5.8 rpm
against Model B's ≈15.3 rpm. A single global τ is misspecified by ≈2× across the operating range
(the bathtub), and that misspecification surfaces precisely in the rise/decay, which is what
region scheduling repairs.

## Conclusion

On the Phase 2.1 grid, the candidate ladder resolves monotonically and identically across
direction and regime: **A ≪ B < C**. Model C — the cascade with a region- and
operating-point-dependent dynamic block — is the best-fit model **forward and reverse, accelerating
and decelerating**, with the static block accounting for the bulk of the improvement and the
region-dependent dynamics for the remainder, concentrated in the transient. This is in-sample
*structural* selection; the model's ability to predict *held-out* trials, and how far it transfers
across sessions, are the separate subjects of Chapter 5.

## Extension to the full operating envelope

Re-running the comparison across all **68 calibrated trials** — adding the gap-fill acceleration
points (PWM 180/220) and deceleration targets (240->100/180/220), with Models A and B re-fit
globally over the enlarged set and Model C using each condition's session-appropriate parameters —
confirms the conclusion and sharpens it.

| Subset | RMSE A | RMSE B | RMSE C | FIT% A | FIT% B | FIT% C |
|---|---:|---:|---:|---:|---:|---:|
| Phase 2.1 (n=30) | 34.8 | 7.1 | **4.1** | -157 | 62.8 | **78.3** |
| gap-fill (n=38) | 35.2 | 9.7 | **4.5** | -115 | 43.1 | **67.6** |
| overall (n=68) | 35.0 | 8.5 | **4.3** | -133 | 51.8 | **72.3** |

*Table 4.4 - Full-envelope ladder, overall and by session.*

Two further points follow. **(i) The ordering replicates independently in each session** (P2.1 and
gap-fill both give A << B < C), so it is not an artefact of a single bench day. **(ii) The added
mid-range points are exactly where Model B is worst:** its transient error peaks at PWM 180-220
(~18-31 rpm) - the bottom of the tau bathtub, where the true time constant is fastest (~95-108 ms)
and a single global tau (~211 ms) is most misspecified - while Model C holds ~3-5 rpm throughout
(Figure 22, `figures/22_model_ladder_fullgrid.png`). Broadening the grid therefore *strengthens*
the case for region-dependent dynamics rather than merely extending it. Caveat: the consolidated
grid mixes two sessions (as do Tables 4.1-4.2), so Models A and B carry a small extra cross-session
penalty that falls on all three models alike; the single-session Table 4.3 remains the clean
structural reference.

---

### Sources for this section
`data/processed/phase21_model_ladder_summary.csv`, `phase21_model_ladder_per_trial.csv` ·
`notebooks/06_model_comparison.ipynb` (fits, scoring, figures 20–21) ·
`models/model_A.json`, `model_B.json`, `model_C.json` (persisted parameters) ·
Tables 4.1–4.2 (Model C parameters) · `plan.md` §3.3, §3.6 (the A/B/C/D ladder and scoring plan).
