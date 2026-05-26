"""Closed-loop performance metrics and paired-comparison statistics.

Metrics: RMSE (full, windowed), settling time, overshoot, steady-state error,
RMS control effort. Stats: paired bootstrap CI of differences, Wilcoxon
signed-rank p-value, within-profile-standardised pooled paired-difference test.

All metrics operate on numpy arrays. The "trial" abstraction is left to the
caller — every function takes raw arrays + a sample-rate or sample-time grid.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
from scipy import stats


# ----------------------------------------------------------------------------
# Error metrics
# ----------------------------------------------------------------------------

def rmse(ref: Sequence[float], meas: Sequence[float],
         mask: Optional[Sequence[bool]] = None) -> float:
    ref = np.asarray(ref, dtype=float)
    meas = np.asarray(meas, dtype=float)
    diff = ref - meas
    if mask is not None:
        diff = diff[np.asarray(mask)]
    if diff.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(diff ** 2)))


def rmse_window(t_ms: Sequence[float], ref: Sequence[float],
                meas: Sequence[float], t_lo: float, t_hi: float) -> float:
    t_ms = np.asarray(t_ms, dtype=float)
    mask = (t_ms >= t_lo) & (t_ms < t_hi)
    return rmse(ref, meas, mask)


def rmse_deadzone(t_ms, ref, meas, deadzone_threshold: float = 80.0) -> float:
    """RMSE over samples where |ref| <= deadzone_threshold (default 80 rpm,
    just above the steady-state breakaway speed of ~55 rpm)."""
    ref = np.asarray(ref, dtype=float)
    mask = np.abs(ref) <= deadzone_threshold
    return rmse(ref, meas, mask)


def rmse_transient(t_ms: Sequence[float], ref: Sequence[float],
                   meas: Sequence[float], tau_ms: float = 200.0,
                   horizons: int = 5) -> float:
    """RMSE over `horizons * tau_ms` after each setpoint change."""
    t_ms = np.asarray(t_ms, dtype=float)
    ref = np.asarray(ref, dtype=float)
    meas = np.asarray(meas, dtype=float)
    diff = np.diff(ref)
    change_idx = np.where(np.abs(diff) > 1e-6)[0] + 1
    if change_idx.size == 0:
        return rmse(ref, meas)
    mask = np.zeros(len(t_ms), dtype=bool)
    horizon_ms = horizons * tau_ms
    for k in change_idx:
        t0 = t_ms[k]
        mask |= (t_ms >= t0) & (t_ms < t0 + horizon_ms)
    return rmse(ref, meas, mask)


# ----------------------------------------------------------------------------
# Time/step-shape metrics
# ----------------------------------------------------------------------------

def settling_time(t_ms: Sequence[float], meas: Sequence[float],
                  target: float, band: float = 5.0,
                  t_step_ms: float = 0.0,
                  hold_ms: float = 100.0) -> float:
    """Time (ms after t_step_ms) at which meas first enters and stays inside
    [target-band, target+band] for at least `hold_ms`. Returns NaN if never
    achieved within the window.
    """
    t_ms = np.asarray(t_ms, dtype=float)
    meas = np.asarray(meas, dtype=float)
    mask = t_ms >= t_step_ms
    t_w = t_ms[mask]
    y_w = meas[mask]
    in_band = np.abs(y_w - target) <= band
    if not np.any(in_band):
        return float("nan")
    # find earliest k such that in_band[k:k+hold_samples] all true
    dt_ms = float(np.median(np.diff(t_w))) if len(t_w) > 1 else 10.0
    hold_samples = max(int(round(hold_ms / dt_ms)), 1)
    for k in range(len(in_band) - hold_samples + 1):
        if np.all(in_band[k:k + hold_samples]):
            return float(t_w[k] - t_step_ms)
    return float("nan")


def overshoot(meas: Sequence[float], y_init: float, y_final: float) -> float:
    """Overshoot magnitude as a percentage of the step amplitude |y_final-y_init|.
    Sign of the step is respected; returns 0 if the trajectory never exceeds y_final.
    """
    meas = np.asarray(meas, dtype=float)
    step = y_final - y_init
    if step == 0:
        return 0.0
    if step > 0:
        peak = float(np.max(meas))
        excess = max(peak - y_final, 0.0)
    else:
        peak = float(np.min(meas))
        excess = max(y_final - peak, 0.0)
    return 100.0 * excess / abs(step)


def ss_error(t_ms: Sequence[float], ref: Sequence[float],
             meas: Sequence[float], window_ms: float = 500.0) -> float:
    """Mean (ref - meas) over the last `window_ms` of the trial."""
    t_ms = np.asarray(t_ms, dtype=float)
    ref = np.asarray(ref, dtype=float)
    meas = np.asarray(meas, dtype=float)
    t_end = t_ms[-1]
    mask = t_ms >= (t_end - window_ms)
    return float(np.mean(ref[mask] - meas[mask]))


def control_effort_rms(pwm: Sequence[float]) -> float:
    pwm = np.asarray(pwm, dtype=float)
    return float(np.sqrt(np.mean(pwm ** 2)))


# ----------------------------------------------------------------------------
# Paired statistics
# ----------------------------------------------------------------------------

def paired_bootstrap_ci(diffs: Sequence[float],
                         n_resamples: int = 1000,
                         alpha: float = 0.05,
                         random_state: Optional[int] = None) -> tuple[float, float, float]:
    """Paired bootstrap percentile CI of the mean of `diffs`.

    Returns (mean, lower, upper) with `1-alpha` coverage.
    """
    diffs = np.asarray(diffs, dtype=float)
    n = len(diffs)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(random_state)
    means = np.empty(n_resamples)
    for b in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[b] = float(np.mean(diffs[idx]))
    lo = float(np.quantile(means, alpha / 2))
    hi = float(np.quantile(means, 1 - alpha / 2))
    return float(np.mean(diffs)), lo, hi


def wilcoxon_signed_rank_p(diffs: Sequence[float],
                            alternative: str = "greater") -> float:
    """One-sided Wilcoxon signed-rank p-value (default: testing diffs > 0).

    Returns NaN if scipy raises (e.g. all zero differences).
    """
    diffs = np.asarray(diffs, dtype=float)
    diffs = diffs[~np.isnan(diffs)]
    if len(diffs) < 1 or np.all(diffs == 0):
        return float("nan")
    try:
        result = stats.wilcoxon(diffs, alternative=alternative,
                                 zero_method="wilcox")
        return float(result.pvalue)
    except Exception:
        return float("nan")


def standardised_pooled_diff_p(per_profile_diffs: dict,
                                random_state: Optional[int] = None) -> dict:
    """Pool paired differences across multiple profiles after within-profile
    standardisation, then test the pooled distribution > 0.

    per_profile_diffs: {profile_id: array of paired differences (BASE - CASC)}.

    Standardisation: subtract 0 (we test against H0=0), divide by within-profile
    median absolute deviation (MAD) to put all profiles on comparable scales.
    This stops the noisiest profile from dominating the pool.

    Returns dict with pooled mean, n, and Wilcoxon one-sided p (greater).
    """
    pooled = []
    for prof, diffs in per_profile_diffs.items():
        d = np.asarray(diffs, dtype=float)
        d = d[~np.isnan(d)]
        if len(d) == 0:
            continue
        mad = float(np.median(np.abs(d - np.median(d))))
        if mad <= 0:
            # constant differences across this profile; preserve their sign
            # without scaling explosion
            scale = 1.0
        else:
            scale = mad * 1.4826  # MAD -> sigma equivalent for normal
        pooled.append(d / scale)
    if not pooled:
        return {"pooled_mean": float("nan"), "n": 0, "p_greater": float("nan")}
    pooled_arr = np.concatenate(pooled)
    return {
        "pooled_mean": float(np.mean(pooled_arr)),
        "n": int(len(pooled_arr)),
        "p_greater": wilcoxon_signed_rank_p(pooled_arr, alternative="greater"),
    }
