"""Controllers for closed-loop work.

PIController — discrete PI with anti-windup (conditional integration), output
               clamped to ±pwm_max, optional output slew limit.
CascadeController — inverse-static feedforward + PI with accel/decel gain
               switching. Same call signature as PIController.

The same logic (algorithmically identical, modulo floating-point) is to be
re-implemented in src_closedloop/main.cpp at Stage 1, so the simulator and
firmware compute matching control actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PIController:
    """Discrete PI with conditional anti-windup and output clamp.

    Kp, Ki in (pwm-counts) per (rpm) and (pwm-counts) per (rpm·s).
    dt_ms is the sample period.
    pwm_max clamps output to [-pwm_max, +pwm_max].
    slew_pwm_per_sample limits |Δoutput| per call (0 = disabled).
    """

    Kp: float
    Ki: float
    dt_ms: float = 10.0
    pwm_max: float = 255.0
    slew_pwm_per_sample: float = 0.0
    integrator: float = field(default=0.0, init=False)
    prev_output: float = field(default=0.0, init=False)

    def reset(self) -> None:
        self.integrator = 0.0
        self.prev_output = 0.0

    def __call__(self, t_ms: float, ref: float, meas: float) -> float:
        error = ref - meas
        # tentative integrator update
        new_integrator = self.integrator + error * (self.dt_ms * 1e-3)
        u_unsat = self.Kp * error + self.Ki * new_integrator
        # saturation check
        u_sat = max(-self.pwm_max, min(self.pwm_max, u_unsat))
        saturated = (u_unsat != u_sat)
        # conditional integration: only commit integrator update if not
        # actively walking further into saturation
        if saturated and (error * u_unsat > 0):
            pass  # do not commit
        else:
            self.integrator = new_integrator
        # optional output slew
        u_out = u_sat
        if self.slew_pwm_per_sample > 0:
            du_max = self.slew_pwm_per_sample
            u_out = max(self.prev_output - du_max,
                        min(self.prev_output + du_max, u_sat))
        self.prev_output = u_out
        return u_out


@dataclass
class CascadeController:
    """Cascade-aware controller: PI + inverse-static feedforward + region gains.

    ff_lookup(ref_rpm) -> pwm_signed must implement the session-fresh inverse
    steady-state map (with deadzone). Below the minimum-sustainable speed it
    should saturate to ±breakaway_pwm with sign(ref).

    gains_accel / gains_decel are (Kp, Ki) per direction.
    Region is selected from (ref - meas) and sign(ref):
      accelerating when sign(ref - meas) == sign(ref)  (speed magnitude growing)
      decelerating otherwise.
    Direction is selected from sign(ref).
    """

    ff_lookup: callable
    gains_accel_fwd: tuple
    gains_decel_fwd: tuple
    gains_accel_rev: tuple
    gains_decel_rev: tuple
    dt_ms: float = 10.0
    pwm_max: float = 255.0
    slew_pwm_per_sample: float = 0.0
    integrator: float = field(default=0.0, init=False)
    prev_output: float = field(default=0.0, init=False)

    def reset(self) -> None:
        self.integrator = 0.0
        self.prev_output = 0.0

    def _select_gains(self, ref: float, meas: float) -> tuple[float, float]:
        direction = "fwd" if ref >= 0 else "rev"
        # accel iff |ref| > |meas| with same sign(ref); else decel
        if ref == 0:
            accel = False
        else:
            sign_ref = 1.0 if ref > 0 else -1.0
            accel = (sign_ref * (ref - meas) > 0) and (sign_ref * meas >= 0)
        if direction == "fwd":
            return self.gains_accel_fwd if accel else self.gains_decel_fwd
        else:
            return self.gains_accel_rev if accel else self.gains_decel_rev

    def __call__(self, t_ms: float, ref: float, meas: float) -> float:
        Kp, Ki = self._select_gains(ref, meas)
        # feedforward from inverse static map (session-fresh)
        u_ff = self.ff_lookup(ref)
        error = ref - meas
        new_integrator = self.integrator + error * (self.dt_ms * 1e-3)
        u_pi = Kp * error + Ki * new_integrator
        u_unsat = u_ff + u_pi
        u_sat = max(-self.pwm_max, min(self.pwm_max, u_unsat))
        saturated = (u_unsat != u_sat)
        # anti-windup: don't integrate further into saturation
        if saturated and (error * (u_unsat - u_ff) > 0):
            pass
        else:
            self.integrator = new_integrator
        u_out = u_sat
        if self.slew_pwm_per_sample > 0:
            du_max = self.slew_pwm_per_sample
            u_out = max(self.prev_output - du_max,
                        min(self.prev_output + du_max, u_sat))
        self.prev_output = u_out
        return u_out
