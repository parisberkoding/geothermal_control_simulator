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

        self._integral:    float = 0.0
        self._prev_error:  float = 0.0
        self._initialized: bool  = False

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

        # Integral with anti-windup clamping
        self._integral += error * dt
        max_i = (self.output_max - self.output_min) / max(abs(self.ki), 1e-10)
        self._integral = max(-max_i, min(max_i, self._integral))
        i_term = self.ki * self._integral

        # Derivative (skip on first call to avoid derivative kick)
        if self._initialized:
            d_term = self.kd * (error - self._prev_error) / dt
        else:
            d_term = 0.0
            self._initialized = True

        self._prev_error = error

        output = p_term + i_term + d_term
        return max(self.output_min, min(self.output_max, output))

    def reset(self) -> None:
        """Reset integrator and derivative history."""
        self._integral    = 0.0
        self._prev_error  = 0.0
        self._initialized = False

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
        'cabin':             32.0,
        'hot_pool':          40.0,
        'tea_dryer':         60.0,
        'food_dehydrator_1': 50.0,
        'fish_pond':         29.0,
        'food_dehydrator_2': 50.0,
        'green_house':       27.0,
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
