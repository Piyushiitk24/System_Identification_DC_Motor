# Chapter 6 — Closed-Loop Validation

> **Draft status:** rewritten 2026-05-27 from results, replacing the previous "plan" draft. Markdown; converts to LaTeX mechanically. All numbers trace to `data/processed/closed_loop_metrics_per_trial.csv`, `closed_loop_summary.json`, `closed_loop_drift_check.csv`, `models/calibration_2026-05-27.json`, `models/closed_loop_gains_2026-05-27.json`, `data/processed/phase3_preregistration.json`, and figures `23`–`24`. Covers Phase 3 (closed-loop validation, 2026-05-27 session, 64 trials, n=8 paired per profile).

## 6.1 Objective

Chapters 3–5 produced and within-session-validated the cascade model (Model C). Chapter 6 tests whether that structural choice translates into measurably better *closed-loop* tracking on the real rig. The benchmark is **Model A** — the naive global LTI model the cascade was meant to replace — fit from the same in-session calibration data and used to design a matched baseline controller. The test is **pre-registered**: metrics, success criteria, and statistical procedure were committed (with a SHA-256 hash recorded) before any closed-loop trial was run, so the result that follows is honest in the strict sense.

## 6.2 Hypothesis (unchanged from pre-registration)

> A controller informed by the cascade model (direction-specific static block, region- and operating-point-dependent FOPDT dynamics) achieves lower reference-tracking error than a controller informed by a single global LTI model fitted to the same plant, with the largest advantage near the deadzone, at the operating-point extremes, and during direction reversals — the regimes where the single-LTI model is most misspecified.

The hypothesis is falsifiable in both directions: a null (no advantage) is publishable, and a *negative* result on a specific profile (cascade loses) is sharper still, because it constrains where the cascade structure is and is not the right design.

## 6.3 Method

**Controllers.** Both controllers are discrete PI with anti-windup, ±255 PWM clamp, and 30-counts-per-sample output slew limit; identical control-loop arithmetic in firmware ([src_closedloop/main.cpp](../src_closedloop/main.cpp)) and in the Python simulator ([motor_id/controllers.py](../motor_id/controllers.py)).

- **BASE** — one global PI gain set computed from Model A by IMC with closed-loop time-constant λ = 200 ms. No feedforward, no region or direction split.
- **CASC** — four PI gain sets (forward/reverse × accel/decel), each computed from Model C's parameters at the canonical PWM = 200 operating point by the *same* IMC routine. Inverse-static feedforward from a five-point lookup table (RPM ∈ {50, 80, 100, 150, 200} per direction, with the 50-rpm entry pinned at the breakaway PWM since the motor cannot sustain steady speeds below breakaway).

The same `compute_imc_gains(K, τ, T_d, λ)` function tunes both controllers; neither was hand-adjusted on the bench. Gains were frozen from the in-session calibration before any closed-loop trial began and persisted to [`models/closed_loop_gains_2026-05-27.json`](../models/closed_loop_gains_2026-05-27.json).

**Reference profiles.** Four profiles, defined as time-stamped breakpoint tables compiled into the firmware:

- **P1** — bidirectional staircase: 0 → ±80 → ±150 → ±200 → ±150 → ±80 → 0 in each direction, 3 s holds, 39 s total. Exercises the deadzone edge holds at 80 rpm in both polarities.
- **P2** — bidirectional ramp through deadzone: linear ramp 0 → +150 over 10 s, hold 5 s, ramp +150 → 0, hold 3 s, ramp 0 → −150, hold 5 s, ramp −150 → 0. 53 s total. Crosses zero slowly twice.
- **P3** — reversal: +100 hold 3 s → ramp to −100 over 4 s → hold −100 3 s. 10 s total. Tests cross-zero behaviour.
- **P4** — small-signal negative control: 150 → 160 → 150 → 160 rpm, 2 s holds. 8 s total. In the linear regime above the deadzone where neither model is misspecified.

**Bench protocol.** A single 2026-05-27 session, ≈2 h motor-on:

1. **Warm-up** (~55 s, no logged trials). Forward PWM = 200 for 20 s, off 5 s, reverse PWM = 200 for 20 s, off 10 s. Discharges the cold-start transient identified in §5.5.
2. **In-session calibration** — 30 open-loop trials: accel PWM ∈ {160, 200, 240} × {fwd, rev} × 3 + decel 240 → {0, 160} × {fwd, rev} × 3.
3. **On-laptop refit** — FOPDT fits per condition; Model A globally; IMC gains and FF table built and persisted; uploaded to firmware via the `GAINS_BASE`/`GAINS_CASC`/`FF_FWD`/`FF_REV` commands. **Gains frozen from this point.**
4. **Closed-loop trials** — n = 8 paired runs per (profile × controllers). 64 trials total. Pair order randomised within profile (seed = 20260527); within each pair the controller order (BASE-first or CASC-first) randomised. Every trial has an explicit pair ID for the paired analysis.
5. **Drift check** — fwd/rev PWM = 200 accel × 3 each at session end, to bound mid-session drift.

**Metrics (pre-registered).** Per trial: `rmse_full` (post-warm-up window), `rmse_deadzone` (samples where |ref| ≤ 80 rpm), `rmse_transient` (5 τ after each setpoint change), settling time, overshoot, steady-state error, RMS PWM. The headline metric is `rmse_full`. Headline statistic is the per-pair difference `RMSE(BASE) − RMSE(CASC)`.

**Pre-registered success criteria.** *Primary*: `median(BASE − CASC) > 0` on each of P1, P2, P3 **AND** pooled within-profile-MAD-standardised paired-difference one-sided Wilcoxon `p < 0.10` on the {P1, P2, P3} pool. *Strong*: Primary holds **AND** 95 % paired-bootstrap CI of (BASE − CASC) excludes zero on ≥ 2 of P1, P2, P3. **Fairness gate**: cascade RMS PWM ≤ 1.5 × baseline RMS PWM on every profile (a controller cannot "win by hammering harder").

## 6.4 Calibration block: this session's Model A and Model C

The 30 open-loop calibration trials at session start gave 18/18 accel fits and 12/12 decel fits OK. The on-laptop refit yielded:

- **Model A (this session):** K_A = 0.737 rpm/PWM, τ = 155 ms, T_d = 6.6 ms.
- **Model C (this session):** six accel conditions (PWM 160/200/240 × fwd/rev) and four decel conditions (240 → 0/160 × fwd/rev) with parameter values close to but not identical to the locked Phase 2.1 numbers of Tables 4.1–4.2.

The session Model A's τ (155 ms) is about 25 % below the locked Phase 2.1 value (207 ms) and Td (6.6 ms) is about a third of it (20 ms). This is exactly the kind of cross-session drift §5.6 warned about, and it directly validated the in-session-calibration protocol: a closed-loop session that had reused the locked Phase 2.1 Model A would have designed a 30 %-overdamped baseline controller. The session-fresh fit gave both controllers parameters that actually describe today's motor.

## 6.5 Closed-loop results

The paired RMSE results, with 95 % bootstrap CI and one-sided Wilcoxon p-value, are in Table 6.1 (Figure `23`).

| Profile | n | median(BASE − CASC) (rpm) | mean (rpm) | 95 % CI | p (greater) | Sim prediction |
|---|---:|---:|---:|---:|---:|---:|
| **P1** (staircase) | 8 | **+2.82** | +2.83 | [+2.74, +2.93] | 0.004 | +2.20 |
| **P2** (deadzone ramp) | 8 | **−1.13** | −1.09 | [−1.20, −0.97] | 1.000 | +4.21 |
| **P3** (reversal) | 8 | **+5.15** | +5.22 | [+5.04, +5.40] | 0.004 | +9.15 |
| **P4** (small-signal) | 8 | **+1.00** | +1.03 | [+0.86, +1.22] | 0.004 | +0.92 |

*Table 6.1 — Pre-registered paired RMSE difference per profile. Positive = cascade wins. The "Sim prediction" column is the simulated `BASE − CASC` from `notebooks/07a_closed_loop_sim.ipynb`, run before bench day with Model C as truth plant.*

**Three findings sit on the table, in tension with each other.**

**(1) Cascade wins decisively on step-change profiles.** P1 (+2.83 rpm), P3 (+5.22 rpm), and P4 (+1.03 rpm) all show statistically clear cascade advantages with CIs cleanly excluding zero (p ≈ 0.004 each, the minimum achievable at n = 8 by signed-rank). P3 — the reversal — is the largest single effect, exactly as the hypothesis predicted: the regime in which the baseline single-LTI model is most misspecified is also the regime in which the cascade wins by the largest margin. Per-pair run-to-run noise is small (sd of differences 0.14–0.29 rpm), so the effects are stable across the eight repetitions. The raw per-pair table — `rmse_base, rmse_casc, difference, rms_pwm_base, rms_pwm_casc` for every pair on every profile — is published at `data/processed/closed_loop_pair_differences.csv` for direct inspection.

**(2) Cascade *loses* on the slow ramp profile.** P2 shows a per-pair median difference of −1.13 rpm — the cascade controller tracks the bidirectional ramp through the deadzone *worse* than the baseline. The CI [−1.20, −0.97] cleanly excludes zero on the wrong side; the one-sided p-value for "cascade better" is essentially 1.0. The simulation predicted the *opposite* sign (+4.21 rpm) on this profile, so this is not just an "advantage smaller than expected" — it is a sign reversal, and a genuine counter-example to the universal version of the hypothesis. The mechanism is interpreted in §6.6.

**(3) The negative control did not behave as a negative control.** P4 was designed as a small-signal test in the linear regime (RPM steps of 10, far above the deadzone) where neither model is misspecified and no cascade advantage was expected. In fact, the cascade wins by ≈1 rpm with a CI excluding zero. The effect is small in absolute terms but real. The interpretation is that the inverse-static feedforward is providing a benefit *even where the model assumes none*, by getting the steady-state PWM nearly right and letting the PI loop spend its action on the small residual rather than on coarse seeking.

**Pre-registered tests, applied.** *Primary*: condition 1 (median > 0 on each of P1, P2, P3) **fails** because P2's median is negative. Condition 2 (pooled MAD-standardised Wilcoxon p < 0.10) passes overwhelmingly (p = 3 × 10⁻⁴ on n = 24 pooled paired differences). Therefore primary **fails**. *Strong*: requires primary plus ≥ 2 of P1/P2/P3 with CIs excluding zero — we have CIs excluding zero on P1 and P3 (2 of 3), but primary failing means strong also **fails**. *Fairness gate*: cascade RMS PWM is 0.99–1.04 × baseline across all four profiles — **PASS**. The cascade is not winning anywhere by hammering harder.

The pre-registered binary "did cascade win" answer is therefore **no, not universally** — and the reason is concentrated entirely in profile P2.

## 6.6 Interpretation: where the cascade structure helps, and where it hurts

The pattern of wins and losses is consistent, internally, and informative. The cascade controller differs from the baseline in two ways: (i) it has a per-direction inverse-static feedforward that supplies the steady-state PWM corresponding to the current reference, and (ii) it switches between accel and decel PI gain sets according to whether the speed magnitude is growing or shrinking. The feedforward is the structurally larger of the two changes — it accounts for almost all of the FF-table magnitude at steady state — and is also the most plausible source of the P2 anomaly.

**Why cascade wins on P1, P3, P4.** Each of these profiles asks the controller to *step* the reference. A step demands instant action: an integrator-only PI builds output slowly, while a feedforward jumps the PWM to the right neighbourhood immediately. Even on a small step (P4), this is worth ≈ 1 rpm in tracking, because settling time, not steady-state offset, dominates the RMSE on a short profile. On P3 (large reversal), the same effect compounds with the change of direction: the cascade's FF flips sign with the reference and is already producing the right-magnitude PWM in the new direction when the encoder has not yet seen the reversal, while the baseline must wait for accumulated integrator error to drive its output through zero. The advantage at the reversal is structural, not numerical, and matches the predicted shape.

**Why cascade *loses* on P2.** The bidirectional ramp visits every speed between −150 and +150 rpm slowly (at 15 rpm/s). When the reference passes through magnitudes below the steady-state breakaway speed (≈ 55 rpm), the cascade's FF table — which is constructed to saturate at the breakaway PWM for these unreachable steady speeds — produces a step-like PWM kick on either side of zero. Concretely, as `ref` rises from 0 toward +50 rpm, `ff_lookup(ref)` jumps from 0 to the breakaway PWM (≈ 168 PWM in this session); as `ref` continues toward 80 rpm, FF interpolates smoothly. On a ramp, that jump is a small but real injection of step-like control action at each zero crossing, plus a discontinuity in the *slope* of the FF curve at the breakaway-RPM edge of the table. The baseline controller, having no FF, accumulates integrator error gradually as the ramp passes through deadzone speeds and produces a smoothly increasing PWM — a control signal that happens to match the *slow* reference better than the cascade's piecewise-constant FF.

The proximate controller-side mechanism is therefore the FF discontinuity at the breakaway edge. However, the FF discontinuity by itself is not the full explanation: the pre-bench-day simulation (§6.3; same FF logic, Model C as truth plant) predicted CASC would *win* P2 by ≈ +4.2 rpm, opposite to the bench result of −1.1 rpm. Since the controller code is identical between simulation and bench, the sign reversal must arise from physics the simulator does not model. The simulator's plant has a clean binary deadzone — `static_rpm` returns 0 for |PWM| below breakaway and an FOPDT response above — with no low-speed friction dynamics, no stick–slip, no coasting through the unreachable region. On a slow ramp through the deadzone the real motor exhibits stiction onset, brush-pattern-dependent breakaway timing, and coasting decay below the deadzone edge; the FF discontinuity *interacting with* these unmodelled dynamics is what produces the P2 penalty. The clean discontinuity in simulation is absorbed by the FOPDT damping; in reality it excites a low-speed nonlinear regime the model is silent on.

This is therefore not a bug in the cascade design alone but a coupled limitation: the static block of Model C is *inherently* discontinuous at the deadzone edge (the deadzone is a real physical phenomenon, no PWM below breakaway produces steady motion), and any FF derived from inverting that static block will inherit a discontinuity in its slope at the breakaway-RPM. A controller that uses such an FF will get a benefit on *step* references that need to cross the deadzone quickly, and — when paired with the real motor's low-speed friction nonlinearities — a penalty on *ramp* references whose smoothness is broken by the FF jump. Closing this gap therefore requires both a smoother FF (controller side) *and* a richer low-speed plant model that captures stick–slip and coast (model side); the latter is the friction-explicit Model D listed in §6.9.

Figure `25` makes the mechanism visible directly. The two zero crossings of P2 (around t ≈ 25 s and t ≈ 28 s in pair 00) appear as instantaneous jumps in the FF component of the CASC PWM signal: the FF lookup steps from ≈ +154 to 0 as the reference enters the deadzone band |ref| ≤ 50 rpm at t ≈ 25 s, and from 0 to ≈ −155 as the reference re-emerges into reverse motion at t ≈ 28 s. The PI residual does not have time to oppose the second jump within one or two samples, and the total CASC PWM overshoots in the reverse direction, driving the motor to ≈ −55 rpm before the closed loop pulls it back to the reference. The BASE PWM is smooth and monotone over the same interval and produces a near-perfect tracking of the slow ramp. The CASC penalty on P2 is therefore traceable to a specific, identifiable event in the control signal, not a diffuse tuning effect.

**Why P4 went positive.** The same FF mechanism that helps with steps helps with small steps. P4's 10-rpm steps are in the linear region, well above the deadzone, where the FF is smooth and well-conditioned; the FF gets the steady-state PWM essentially right (within a couple of PWM counts), and the PI only has to handle the transient. The 1-rpm advantage is the absolute value of "settling-time benefit on a clean step" with no deadzone effects in play. It is consistent with — and forms an empirical floor for — the cascade-FF benefit on a step regardless of where in the operating range.

**A specific, falsifiable claim follows.** The cascade structure as designed is the *right* controller for closed-loop tracking when the reference is a sequence of stepwise setpoints (with or without deadzone crossings) or a reversal. It is the *wrong* controller — without modification — for slow ramps through the deadzone, where the FF discontinuity at the breakaway edge becomes a liability. A future refinement of the cascade controller for ramp-heavy references would smooth the FF table through the deadzone (for example by tapering linearly from 0 to breakaway PWM over the unreachable-RPM region, accepting a transient deadzone-overshoot in exchange for ramp continuity).

## 6.7 Within-session drift

The end-of-session drift check (six trials, fwd/rev PWM = 200 accel × 3 each) gave:

| Direction | PWM | ΔK_ss vs start | Δτ vs start | n_start | n_end |
|---|---:|---:|---:|---:|---:|
| fwd | 200 | +6.7 % | −5.2 % | 3 | 3 |
| rev | 200 | +3.7 % | −2.5 % | 3 | 3 |

*Table 6.2 — Drift over the ~2 h closed-loop session.*

K_ss rises ≈ 4–7 % and τ falls ≈ 3–5 % over the session, with forward drift larger than reverse. The direction of the drift (higher steady speed and faster transient for the same PWM at session end) is consistent with a reduction in effective drive loss or low-speed friction as the rig warms, mirroring the morning-vs-evening spot-check of §3.8 where motor voltage was measured and showed the same pattern. However, Phase 3 itself did not log motor voltage or L298N temperature, so the drift cannot be uniquely localised to the driver in this session — the same observation is consistent with rotor/bearing/lubricant warming. The drift is small enough that the closed-loop comparison itself — which runs each pair within seconds of each other — is unaffected, but it is large enough that *between*-session reuse of parameters would still be suspect, confirming once more §5.6's recalibrate-in-situ requirement.

## 6.8 Limitations

Three caveats bound this closed-loop result.

(i) **One session.** All 64 paired trials are from a single 2026-05-27 bench. Cross-session reproducibility of the *closed-loop* result (separate from the open-loop drift) is not measured.

(ii) **No external disturbance.** The reference profiles are deterministic; no load disturbance, no brake. The cascade advantage on P1/P3 is therefore a *tracking* advantage; load-disturbance rejection is not tested. Given that the FF is purely a function of `ref`, a load-disturbance test would isolate the PI portion of each controller and the cascade's FF would not contribute, so this is a meaningful gap.

(iii) **PI only, no D term.** Both controllers are PI; RPM is quantised at 2.5 rpm by the encoder/finite-difference chain (§2.5), making a derivative term noisy. A D term with a low-pass filter is a natural refinement but was excluded from this study to keep BASE-vs-CASC comparison purely about model structure, not controller order.

(iv) **No ablation of FF vs. region-scheduled gains.** The BASE-vs-CASC comparison tests the complete model-informed controller package, not the separate contribution of each element. In particular, CASC differs from BASE both by inverse-static feedforward and by region- and direction-scheduled PI gains. The present data are consistent with the FF dominating the closed-loop benefit on P1/P3/P4 (the FF supplies the step-change PWM jump, the PI residual is small in steady state, and the P2 failure is traceable directly to an FF event in Figure `25`), but the data cannot formally isolate the two contributions. An ablation controller — static FF only, with a single global PI gain set — would be needed to attribute the closed-loop benefit between the two structural changes.

A fifth, milder, caveat: the FF table has five RPM points per direction. Denser sampling near the deadzone edge (e.g. RPM ∈ {30, 50, 60, 70, 80} on top of the present table) would refine the FF curvature in the very region where P2 lost — but per §6.6 the issue is structural rather than resolution-limited, so this is unlikely to flip the P2 sign on its own.

## 6.9 Future work

Beyond the closed-loop study, the open-loop identification leaves several threads, in rough priority order:

- **Smoothed-FF cascade variant.** Replace the breakaway-saturated FF with a smooth taper through the deadzone, then re-run P2. If P2 flips to a cascade win, the §6.6 mechanism is confirmed and a clean cascade-wins-everywhere result follows.
- **Disturbance-rejection trials.** Add a small load step (e.g. via a brake or a mechanical detent) during a steady-state hold; compare BASE and CASC settle-back. The cascade's FF should *not* help here — the comparison becomes a pure PI tuning fairness check.
- **Friction-explicit dynamic block ("Model D").** A Coulomb/Stribeck extension is motivated by the structured residuals at PWM = 160 and in coast-to-rest decel (§4.3–§4.4); it would also smooth the static block through the deadzone, possibly addressing the P2 result by a different route.
- **Higher-order dynamics near full drive.** The PWM = 240 rise departs from first order (§4.3); a second-order or back-EMF-aware model would reduce the largest accel residuals.
- **Cross-session closed-loop reproducibility.** Repeat the bench day on a second session and quantify session-to-session variance of the per-profile differences.
- **Instrumentation.** Routine ambient-temperature and L298N-temperature logging, plus a session-end calibration to bound drift better than two endpoints can.

## 6.10 Summary

The cascade model is *not* a uniformly better closed-loop controller than a single-LTI baseline on this rig: it wins by 1–5 rpm on stepwise profiles (staircase, reversal, small-signal) and loses by ≈ 1 rpm on a slow bidirectional ramp through the deadzone. The pre-registered "wins universally" hypothesis is therefore falsified, in a specific and informative way. The mechanism — the inverse-static feedforward's discontinuity at the breakaway edge of the deadzone — is identifiable and addressable, and points at a concrete refinement (smoothed-FF cascade variant) that would be the natural next bench-day target. As it stands, the cascade structure earned its complexity for stepwise reference tracking on this hardware; for ramp-through-deadzone tracking, the simpler controller is the better default until the FF is fixed.

---

### Sources for this chapter

`data/processed/closed_loop_metrics_per_trial.csv` (per-trial metrics, n=64) · `data/processed/closed_loop_summary.json` (pre-registered tests, headline numbers) · `data/processed/closed_loop_drift_check.csv` (start-vs-end drift) · `models/calibration_2026-05-27.json` (in-session refit of Models A and C) · `models/closed_loop_gains_2026-05-27.json` (frozen PI gains and FF table) · `data/processed/phase3_preregistration.json` (committed pre-registration, SHA-256 in `thesis_notes/log.md`) · `notebooks/07a_closed_loop_sim.ipynb` (sim predictions, pre-registration freeze) · `notebooks/07b_closed_loop_results.ipynb` (per-trial metrics, paired tests, figures) · figures `23` (paired differences with CIs), `24` (representative trajectories) · `src_closedloop/main.cpp`, `motor_id/{cascade_sim,controllers,model_io,metrics,calibration}.py` (controller & analysis implementations).
