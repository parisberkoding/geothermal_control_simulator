"""
PID Controller
Standard proportional-integral-derivative controller for
automatic valve position control in the geothermal direct-use system.
"""


class PIDController:
    """
    Generic PID controller.

    Usage
    -----
    pid = PIDController(kp=2.0, ki=0.3, kd=0.05,
                        setpoint=60.0, output_min=0.0, output_max=100.0)
    dt  = 0.1          # seconds
    valve_cmd = pid.update(measured_temp, dt)
    """

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.1,
        kd: float = 0.01,
        setpoint: float = 0.0,
        output_min: float = 0.0,
        output_max: float = 100.0,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_min = output_min
        self.output_max = output_max

        self._integral:          float = 0.0
        self._prev_error:        float = 0.0
        self._initialized:       bool  = False
        self._prev_measurement:  float = 0.0   # [ADDED] for derivative-on-measurement

    # ── public API ─────────────────────────────────────────────────────────────

    def update(self, measured_value: float, dt: float) -> float:
        """
        Compute the control output for one time step.

        Parameters
        ----------
        measured_value : current process variable reading
        dt             : elapsed time since last call (seconds)

        Returns
        -------
        float : clamped control output in [output_min, output_max]
        """
        dt = max(dt, 1e-6)    # guard against zero division

        error = self.setpoint - measured_value

        # Proportional
        p_term = self.kp * error

        # Integral
        self._integral += error * dt
        i_term = self.ki * self._integral

        # [MODIFIED] Derivative on measurement — avoids kick on setpoint change
        if self._initialized:
            d_term = -self.kd * (measured_value - self._prev_measurement) / dt
        else:
            d_term = 0.0
            self._initialized = True

        self._prev_error       = error
        self._prev_measurement = measured_value   # [ADDED]

        # Raw output
        output_raw = p_term + i_term + d_term

        # Saturate output
        output_sat = max(self.output_min, min(self.output_max, output_raw))

        # [ADDED] Anti-windup back-calculation: undo integral overshoot when saturated
        if abs(self.ki) > 1e-10:
            self._integral -= (output_raw - output_sat) / self.ki

        return output_sat

    def reset(self) -> None:
        """Reset integrator and derivative history."""
        self._integral         = 0.0
        self._prev_error       = 0.0
        self._prev_measurement = 0.0   # [ADDED]
        self._initialized      = False

    # ── properties ─────────────────────────────────────────────────────────────

    @property
    def error(self) -> float:
        return self._prev_error

    @property
    def integral(self) -> float:
        return self._integral

    def __repr__(self) -> str:
        return (
            f"PIDController(kp={self.kp}, ki={self.ki}, kd={self.kd}, "
            f"sp={self.setpoint:.2f}, err={self._prev_error:.2f})"
        )


# ── Multi-loop manager for all 7 cascade stages ────────────────────────────────

class CascadePIDManager:
    """
    Maintains one PID loop per cascade stage, keyed by stage ID.

    The setpoint for each stage is the target outlet temperature defined
    in the unit configuration.  The controller output drives the
    corresponding valve position (0-100%).
    """

    # Tuning presets per unit type (kp, ki, kd)
    _TUNING: dict = {
        'cabin':             (2.5, 0.20, 0.10),
        'hot_pool':          (2.0, 0.15, 0.08),
        'tea_dryer':         (3.0, 0.25, 0.12),
        'food_dehydrator_1': (2.8, 0.22, 0.10),
        'fish_pond':         (1.8, 0.12, 0.06),
        'food_dehydrator_2': (2.8, 0.22, 0.10),
        'green_house':       (1.5, 0.10, 0.05),
    }

    # Default outlet temperature setpoints  (°C)
    _SETPOINTS: dict = {
        'cabin':             32.0,   # [MODIFIED] 26-38°C range; 45°C exceeded unit limit
        'hot_pool':          30.0,   # [MODIFIED] 27-38°C range; achievable after cabin stage
        'tea_dryer':         96.0,   # 95-98°C
        'food_dehydrator_1': 54.0,   # 53-56°C
        'fish_pond':         27.0,   # 24-30°C
        'food_dehydrator_2': 54.0,   # 53-56°C
        'green_house':       23.0,   # 21-26°C
    }

    def __init__(self):
        self._controllers: dict[str, PIDController] = {}
        for sid, (kp, ki, kd) in self._TUNING.items():
            sp = self._SETPOINTS.get(sid, 50.0)
            self._controllers[sid] = PIDController(
                kp=kp, ki=ki, kd=kd,
                setpoint=sp,
                output_min=10.0,
                output_max=95.0,
            )

    def compute(self, sid: str, outlet_temp: float, dt: float) -> float:
        """Return new valve position (%) for a stage given its outlet temperature."""
        ctrl = self._controllers.get(sid)
        if ctrl is None:
            return 50.0
        return ctrl.update(outlet_temp, dt)

    def set_setpoint(self, sid: str, setpoint: float) -> None:
        ctrl = self._controllers.get(sid)
        if ctrl:
            ctrl.setpoint = setpoint

    def reset(self, sid: str | None = None) -> None:
        if sid:
            ctrl = self._controllers.get(sid)
            if ctrl:
                ctrl.reset()
        else:
            for c in self._controllers.values():
                c.reset()

    def get_controller(self, sid: str) -> PIDController | None:
        return self._controllers.get(sid)
