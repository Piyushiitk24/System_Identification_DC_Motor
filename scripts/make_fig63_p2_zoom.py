#!/usr/bin/env python3
"""Generate Figure 6.3 — P2 zero-crossing zoom (closed-loop bench, 2026-05-27).

Reconstructs the 3-panel P2 deadzone-crossing figure directly from the bench
trials, decomposing the cascade command into its inverse-static feedforward and
PI-residual parts. This is the tracked generator for `figures/25_p2_zero_crossing_zoom.png`
(the figure had previously been committed as a bare PNG with no source).

Sources of truth:
  - data/raw/closed_loop_2026-05-27/closed_loop_trials/P2_pair00_{BASE,CASC}.csv
        telemetry: t_ms,profile,controller,ref_rpm,meas_rpm,pwm_cmd,dir,enc_count,integrator
  - models/closed_loop_gains_2026-05-27.json   (session FF table, frozen on bench day)
  - motor_id.model_io.ff_lookup_from_table     (controller-matched FF lookup)

Decomposition (matches src_closedloop/main.cpp and motor_id.controllers.CascadeController):
  PWM(CASC total) = FF(ref) + PI residual   ->   PI residual = pwm_cmd_signed - FF(ref)
The FF saturates to the breakaway PWM for 0 < |ref| <= 50 rpm and is 0 only at
ref == 0, producing the slope discontinuity at the zero crossing.

No in-image figure banner (the LaTeX/slide caption carries "Fig 6.3"); colours
follow the deck's code: cascade = teal, baseline = grey, feedforward = amber.

Run:  ./.venv/bin/python scripts/make_fig63_p2_zoom.py
"""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from motor_id.model_io import ff_lookup_from_table  # noqa: E402

# --- colour code (matches the slide deck) -----------------------------------
TEAL = "#0F766E"   # cascade
GREY = "#475569"   # baseline
AMBER = "#B45309"  # feedforward (inverse static / driver block)
GREEN = "#4D7C0F"  # PI residual
SIGN = {"F": 1, "R": -1, "N": 0}
BREAKAWAY_RPM = 50.0          # FF-saturation band: |ref| <= 50 saturates to breakaway PWM
T0, T1 = 22.0, 33.0           # zoom window around the P2 zero crossing (ramps 0 @25s, neg @28s)

TRIALS = ROOT / "data/raw/closed_loop_2026-05-27/closed_loop_trials"
gains = json.loads((ROOT / "models/closed_loop_gains_2026-05-27.json").read_text())
ff = ff_lookup_from_table(gains["FF_table"])
bk_fwd = float(gains["FF_table"]["fwd"][0][1])   # 154
bk_rev = float(gains["FF_table"]["rev"][0][1])   # 144


def load(ctrl):
    d = pd.read_csv(TRIALS / f"P2_pair00_{ctrl}.csv")
    d["t"] = d.t_ms / 1000.0
    d["spwm"] = d.pwm_cmd * d.dir.map(SIGN)       # signed PWM command
    return d


base = load("BASE")
casc = load("CASC")
casc["ff"] = casc.ref_rpm.map(lambda r: ff(float(r)))   # FF component (signed)
casc["pi"] = casc.spwm - casc.ff                         # PI residual = total - FF


def win(d):
    return d[(d.t >= T0 - 0.5) & (d.t <= T1 + 0.5)]


b, c = win(base), win(casc)

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9, 7.2), sharex=True)

# panel 1 — speed
ax1.axhspan(-BREAKAWAY_RPM, BREAKAWAY_RPM, color="0.6", alpha=0.15, lw=0,
            label=f"|rpm| ≤ {BREAKAWAY_RPM:.0f} (FF-saturation band)")
ax1.axhline(0, color="0.7", lw=0.8)
ax1.plot(c.t, c.ref_rpm, "--", color="k", lw=1.3, label="reference")
ax1.plot(b.t, b.meas_rpm, color=GREY, lw=1.5, label="meas (BASE)")
ax1.plot(c.t, c.meas_rpm, color=TEAL, lw=1.5, label="meas (CASC)")
ax1.set_ylabel("RPM")
ax1.legend(loc="upper right", fontsize=8, ncol=2)
ax1.grid(alpha=0.25)

# panel 2 — baseline command (pure PI, no FF)
ax2.axhline(0, color="0.7", lw=0.8)
ax2.plot(b.t, b.spwm, color=GREY, lw=1.5, label="PWM (BASE, no FF)")
ax2.set_ylabel("PWM (BASE)")
ax2.legend(loc="upper right", fontsize=8)
ax2.grid(alpha=0.25)

# panel 3 — cascade command, decomposed
ax3.axhline(0, color="0.7", lw=0.8)
ax3.axhline(bk_fwd, color="0.5", ls=":", lw=1.0)
ax3.axhline(-bk_rev, color="0.5", ls=":", lw=1.0,
            label=f"breakaway PWM (+{bk_fwd:.0f}/−{bk_rev:.0f})")
ax3.plot(c.t, c.spwm, color=TEAL, lw=1.6, label="PWM (CASC total)")
ax3.plot(c.t, c.ff, color=AMBER, lw=1.4, label="FF component")
ax3.plot(c.t, c.pi, color=GREEN, lw=1.1, alpha=0.9, label="PI residual")
ax3.set_ylabel("PWM (CASC)")
ax3.set_xlabel("time [s]")
ax3.legend(loc="upper right", fontsize=8, ncol=2)
ax3.grid(alpha=0.25)

ax1.set_xlim(T0, T1)
fig.tight_layout()

out = ROOT / "figures" / "25_p2_zero_crossing_zoom.png"
fig.savefig(out, dpi=150)
fig.savefig(ROOT / "thesis" / "Pictures" / "25_p2_zero_crossing_zoom.png", dpi=150)

# --- numeric sanity (so the mechanism is verifiable without opening the PNG) ---
cz = c[(c.t >= 27.5) & (c.t <= 30.0)]
ff_pre = c[(c.t >= 26.0) & (c.t < 28.0)].ff.median()
ff_post = c[(c.t > 28.0) & (c.t <= 30.0)].ff.median()
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {out.name}  ({w}x{h})")
print(f"  CASC reverse overshoot at crossing: min meas = {cz.meas_rpm.min():.0f} rpm "
      f"(ref ~ {cz.ref_rpm.median():.0f})")
print(f"  FF jump across zero: {ff_pre:+.0f} -> {ff_post:+.0f} PWM  (the discontinuity)")
