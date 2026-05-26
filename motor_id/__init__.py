"""Python package for DC-motor system-ID closed-loop work (Phase 3).

Module map:
  cascade_sim  — ModelC / ModelA plants, open-loop and closed-loop simulators.
  controllers  — PIController, CascadeController (PI + inverse-static FF + region gains).
  model_io     — load/save model JSONs, IMC tuning, gain safety caps, FF-table builder.
  metrics      — RMSE windows, settling time, overshoot, paired bootstrap, Wilcoxon.

Reusable from notebooks and (logic-mirrored) from firmware. Parameter artifacts
live in models/; this package holds the code.
"""

from .cascade_sim import (
    ModelC,
    ModelA,
    simulate_open_loop_single_transition,
    simulate_open_loop,
    simulate_closed_loop,
)
from .controllers import PIController, CascadeController
from .model_io import (
    load_model_C,
    load_model_A,
    compute_imc_gains,
    compute_baseline_gains,
    compute_cascade_gains,
    build_ff_table,
    safety_check_sim,
)
from .metrics import (
    rmse,
    rmse_window,
    settling_time,
    overshoot,
    ss_error,
    control_effort_rms,
    paired_bootstrap_ci,
    wilcoxon_signed_rank_p,
)
