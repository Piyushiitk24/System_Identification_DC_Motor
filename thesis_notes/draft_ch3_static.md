# Chapter 3 — Static Characterization

> **Draft status:** first full pass, 2026-05-21. Markdown; converts to LaTeX mechanically. Numbers trace to `data/raw/static_sweep_20260506_run1.csv`, `data/raw/deadzone_manual_run01.csv`, `data/raw/spot_check_max_pwm_2026-05-06_evening.csv`, status-doc §4.1, and figures `01`–`04`. Covers Phase 1.1 (static map) and Phase 1.2 (deadzone hysteresis).

## 3.1 Objective

This chapter identifies the **steady-state** behaviour of the rig: the mapping from PWM command to settled output speed, with the motor allowed to reach equilibrium at each operating point. The aim is not merely to tabulate that map but to **decompose** it into a driver stage (PWM → motor voltage) and a motor stage (motor voltage → speed), and to show that the plant's pronounced forward/reverse asymmetry lives almost entirely in the driver. That decomposition is the empirical foundation for the cascade model used in the rest of the thesis, and it tells us which block must carry the asymmetry and the deadzone, and which may be treated as direction-symmetric.

## 3.2 Method

Two manually operated procedures were used, both on the manual-mode firmware (Section 2.7).

**Static sweep (Phase 1.1).** PWM magnitude was stepped from 10 to 255 in each direction. At every point the motor was allowed to settle, and three quantities were recorded: the commanded PWM, the steady serial RPM, and the **mean motor voltage** `V_motor`. The latter was read as the time-average of the differential H-bridge output — feasible only because the 20 kHz carrier produces a stable average (Section 2.4) — using a DMM and an oscilloscope math channel (CH1 − CH2). Both directions were stored in one combined file with a `direction` column: 52 rows (26 forward, 26 reverse), PWM 10–255.

**Deadzone ramp (Phase 1.2).** Because a coarse staircase cannot resolve the breakaway threshold cleanly (Section 3.7), the deadzone was probed separately with multiple slow manual ramps in each direction, recording the PWM at which the shaft first moved from rest (**breakaway**) and the PWM at which a moving shaft stopped (**dropout**), together with the corresponding `V_motor`, RPM, and supply current.

Raw measurements were kept immutable; all gains and ratios reported below are computed in `notebooks/01_static_map.ipynb` and are recomputed here directly from the raw CSV.

## 3.3 The static input–output map

Figure `02` plots commanded PWM against settled RPM for both directions. Three features are immediate: (i) a wide central **deadzone** in which no PWM produces motion; (ii) an approximately linear region above breakaway extending to full scale; and (iii) a **direction asymmetry** in which reverse runs slightly faster than forward at equal PWM magnitude. Taken at face value this is the plant's static characteristic, but the PWM→RPM map alone conflates two physically distinct effects — driver voltage delivery and motor electromechanical gain — which the next two sections separate.

## 3.4 Driver block: PWM → motor voltage

Figure `01` plots PWM against `V_motor`. The L298N does not deliver the full supply: even at 100 % duty (PWM = 255), only **8.71 V** (forward) and **9.35 V** (reverse) of the 12.0 V supply reach the motor — a droop of roughly **27 %** and **22 %** respectively, attributable to the saturation voltage of the bipolar output transistors. More importantly, the two directions are **not** symmetric: reverse delivers more motor voltage than forward at every PWM, and the disparity grows sharply toward the low-PWM edge.

| PWM | V_motor fwd (V) | V_motor rev (V) | \|V_rev\|/V_fwd |
|---:|---:|---:|---:|
| 130 | 0.93 | −2.05 | **2.22** |
| 160 | 2.20 | −3.48 | 1.58 |
| 200 | 4.85 | −5.79 | 1.19 |
| 240 | 8.41 | −8.93 | 1.06 |
| 255 | 8.71 | −9.35 | 1.07 |

*Table 3.1 — Driver-block voltage delivery and forward/reverse ratio at representative PWM (from the static sweep).*

The voltage asymmetry is therefore ≈6 % at the top of the range but exceeds **2×** at the lowest moving point. Physically, the forward and reverse current paths traverse different transistor pairs in the H-bridge, whose saturation drops differ; the effect is largest where the delivered voltage is smallest.

## 3.5 Motor block: motor voltage → RPM

When speed is plotted against the *delivered* motor voltage rather than PWM (figure `03`), the picture simplifies dramatically. Above the deadzone the relationship is linear through the origin, `RPM = K · V_motor`, and a least-squares fit through the origin on the moving points gives

$$K_\text{fwd} = 26.94\ \text{rpm/V}, \qquad K_\text{rev} = 24.52\ \text{rpm/V}.$$

The reverse motor gain is only **9.0 % lower** than forward — i.e. the motor itself is close to direction-symmetric, consistent with a nearly electromagnetically symmetric DC machine. The small residual difference, with reverse slightly *lower*, partially offsets the higher reverse voltage of Section 3.4 when the two blocks are composed.

## 3.6 Attribution of the asymmetry

Composing the blocks resolves the apparent tension in the raw map. Reverse receives substantially more voltage per unit PWM (driver asymmetry, large), but converts it at a slightly lower gain (motor asymmetry, ≈9 %, opposite sign); the net forward/reverse speed difference is therefore much smaller than the voltage difference. This is exactly what figure `04` shows: the voltage ratio falls from 2.22 to ≈1.06 across the range, while the RPM ratio stays close to unity (≈1.35 at the low edge, ≈1.01–1.03 at high PWM).

| PWM | \|V_rev\|/V_fwd | \|RPM_rev\|/RPM_fwd |
|---:|---:|---:|
| 130 | 2.22 | 1.35 |
| 200 | 1.19 | 1.03 |
| 240 | 1.06 | 1.01 |

*Table 3.2 — The asymmetry is large in voltage but small in speed: it originates in the driver, not the motor.*

**Conclusion.** The plant's directional asymmetry is driver-dominated. The motor (voltage → speed) block may be modelled as direction-symmetric to within ≈9 %, while a **direction-specific static driver block** must carry the voltage asymmetry. This is the empirical justification for the cascade decomposition `PWM → static driver-voltage block → motor dynamic block → RPM` developed in the following chapters.

## 3.7 Deadzone and hysteresis

The deadzone is not a single threshold but a **hysteresis band**: the PWM needed to start the shaft from rest (breakaway) is well above the PWM at which a moving shaft stops (dropout).

| Direction | Breakaway PWM | Dropout PWM | Band width | V_motor / RPM at breakaway |
|---|---:|---:|---:|---|
| Forward | 154 | 114 | 40 | ≈ +2.30 V / ≈ +55 rpm |
| Reverse | 144 | 112 | 32 | ≈ −2.30 V / ≈ −55 rpm |

*Table 3.3 — Deadzone thresholds (Phase 1.2). At dropout, V_motor ≈ −0.13 V and RPM = 0.*

The coarse staircase of the Phase 1.1 sweep first suggested breakaway near PWM = 130 in both directions, but this is misleading: the staircase steps deliver enough torque to keep an already-moving shaft turning above the dropout level, and the apparent 130 reflects a single stochastic breakaway rather than the typical one. The dedicated ramps show the true breakaway is higher (154 forward, 144 reverse) and is itself **stochastic** run-to-run, consistent with static-friction (stiction) onset. The wider forward band (40 vs 32 PWM) mirrors the larger forward breakaway.

The same hysteresis appears in *steady-state speed* near the deadzone edge: at PWM = 160 the settled speed depends on the approach direction, reaching ≈73.8 rpm (forward) and ≈85.7 rpm (reverse) when descending from a higher speed but only ≈52.1 and ≈69.6 rpm when rising from rest — a gap of ≈22 rpm (forward) and ≈16 rpm (reverse). These four steady-state values are the accel K_ss and decel y_final at PWM = 160 reported in Chapter 4 (Tables 4.1–4.2); it is noted here because it is a static-friction phenomenon and because it confirms that the static block must be **hysteretic**, not a single-valued curve. A Coulomb/Stribeck friction extension is the natural refinement (future work).

## 3.8 Reproducibility and thermal validity

The static map rests on a single sweep, validated by two independent checks rather than by full repeat sweeps. No `static_sweep_run02` or `_run03` were collected; the reproducibility argument rests on this single sweep, the two-point spot-check below, and the implicit cross-validation provided by the Phase 2.1 step-response steady-state endpoints. First, a two-point spot-check at PWM = ±255, repeated morning and evening of the same day, isolated where any drift occurs:

| Direction | ΔV_motor | ΔRPM | ΔPSU current |
|---|---:|---:|---:|
| Forward | −3.8 % | −0.6 % | −4.5 % |
| Reverse | +1.9 % | +0.8 % | −8.7 % |

*Table 3.4 — Morning→evening drift at full duty.*

The motor (voltage → speed) reproduces to within ≈1 %, while the driver-side motor voltage drifts a few percent and the supply current 5–9 %, consistent with **L298N junction thermal drift** after extended operation. Second, the steady-state speeds reached at the end of the Phase 2.1 step-up trials (Chapter 4) provide eighteen further implicit checks of the above-deadzone region; in the linear regime (PWM ≥ 200) they agree with the sweep within these thermal-drift bounds, and the residual forward-vs-reverse pattern of the disagreement matches the spot-check pattern.

Two points follow. The drift is itself **evidence for the cascade**: the instability is confined to the driver block, while the motor block is stable — the same separation found in the asymmetry analysis. And static-block parameters are strictly valid only at the session's thermal state; this caveat is carried forward to any later-session use and is one reason any future closed-loop work will require a fresh in-session calibration rather than reusing these numbers.

## 3.9 Static block model and summary

The identified static block of the cascade comprises three direction-specific elements:

1. a **hysteretic deadzone** — breakaway 154/144 PWM, dropout 114/112 PWM (fwd/rev);
2. a **driver voltage map** PWM → V_motor that is asymmetric (reverse higher, from ≈6 % at full scale to >2× near the edge) and droops ≈22–27 % below supply at full duty; and
3. a near-symmetric **motor gain** RPM = K · V_motor, with K_fwd = 26.94 and K_rev = 24.52 rpm/V (reverse 9 % lower).

The central result is structural: the large directional asymmetry and the only measurable session drift both localise to the driver, while the motor block is stable and near-symmetric. The plant is therefore well described as a direction-specific static driver block followed by a direction-symmetric motor block — the static half of the cascade. What this chapter does **not** capture is how the motor moves *between* operating points; that transient behaviour, and its dependence on operating point and on the direction of the transition, is the subject of Chapter 4.

---

### Sources for this chapter
`data/raw/static_sweep_20260506_run1.csv` (sweep, K fits, V/RPM ratios, full-duty droop) · `data/raw/deadzone_manual_run01.csv` (breakaway/dropout, V/RPM at threshold) · `data/raw/spot_check_max_pwm_2026-05-06_evening.csv` (thermal drift) · `notebooks/01_static_map.ipynb` (figures 01–04, gain computation) · status-doc §4.1 and §4.2 (SS hysteresis at PWM 160, cross-val) · `thesis_notes/log.md` 2026-05-06/07 (Phase 1.1/1.2 interpretation).
