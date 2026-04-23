"""
Valve Controller
Auto-control logic for 7 cascade valves based on system pressure.
Valve order matches the cascade chain.
"""
from typing import Dict
import random


class Valve:
    """Individual valve in the cascade."""

    def __init__(self, name: str, initial_position: float = 50.0):
        self.name             = name
        self.position         = max(0.0, min(100.0, initial_position))
        self.target_position  = self.position
        self.is_open          = self.position > 5
        self.auto_tune_enabled = True

    def set_position(self, position: float):
        self.position = max(0.0, min(100.0, position))
        self.is_open  = self.position > 5

    def set_target(self, target: float):
        self.target_position = max(0.0, min(100.0, target))

    def update(self, dt: float, speed: float = 10.0):
        """Smooth movement towards target position."""
        diff = self.target_position - self.position
        if abs(diff) > 0.5:
            self.position += speed * dt * (1 if diff > 0 else -1)
            if abs(self.target_position - self.position) < 1.0:
                self.position = self.target_position
            self.position = max(0.0, min(100.0, self.position))
            self.is_open  = self.position > 5


class ValveController:
    """Controls 7 cascade valves with pressure-based auto-control."""

    # Default positions: optimal valve openings from thermodynamic calculations
    # tea/food/hot_pool: 100% (need max flow for high heat demand)
    # cabin: 30% (small demand, low flow sufficient)
    # fish/greenhouse: 15% (minimal demand, small flow gives correct outlet temp)
    _DEFAULTS: Dict[str, float] = {
        'tea_dryer':         100.0,
        'food_dehydrator_1': 100.0,
        'cabin':              30.0,
        'hot_pool':          100.0,
        'fish_pond':          15.0,
        'green_house':        15.0,
    }

    def __init__(self):
        self.valves = {k: Valve(k, v) for k, v in self._DEFAULTS.items()}

        self.auto_control_enabled = True

        # Pressure thresholds (MPa) — scaled for 8.1 MPa nominal system
        self.pressure_critical_low  = 5.5
        self.pressure_warning_low   = 6.5
        self.pressure_normal_low    = 7.0
        self.pressure_normal_high   = 9.5
        self.pressure_warning_high  = 10.5
        self.pressure_critical_high = 12.0

        self.last_action     = None
        self.action_cooldown = 0.0

    # ------------------------------------------------------------------
    def update(self, dt: float, current_pressure: float):
        for valve in self.valves.values():
            valve.update(dt)

        if self.auto_control_enabled:
            self._apply_auto_control(current_pressure)

        if self.action_cooldown > 0:
            self.action_cooldown -= dt

    def _apply_auto_control(self, pressure: float):
        if self.action_cooldown > 0:
            return

        if pressure > self.pressure_critical_high:
            self._throttle_all(30)
            self.last_action = f"CRITICAL: Throttled all valves (P={pressure:.2f} bar)"
            self.action_cooldown = 2.0

        elif pressure < self.pressure_critical_low:
            self._open_all(20)
            self.last_action = f"CRITICAL: Opened all valves (P={pressure:.2f} bar)"
            self.action_cooldown = 2.0

        elif pressure > self.pressure_warning_high:
            self._throttle_most_open(15)
            self.last_action = f"WARNING: Throttled valve (P={pressure:.2f} bar)"
            self.action_cooldown = 3.0

        elif pressure < self.pressure_warning_low:
            self._open_most_closed(10)
            self.last_action = f"WARNING: Opened valve (P={pressure:.2f} bar)"
            self.action_cooldown = 3.0

    def _throttle_all(self, pct: float):
        for v in self.valves.values():
            v.set_target(max(10.0, v.position - pct))

    def _open_all(self, pct: float):
        for v in self.valves.values():
            v.set_target(min(100.0, v.position + pct))

    def _throttle_most_open(self, pct: float):
        candidates = [(k, v) for k, v in self.valves.items() if v.position > 30]
        if candidates:
            _, v = max(candidates, key=lambda x: x[1].position)
            v.set_target(max(20.0, v.position - pct))

    def _open_most_closed(self, pct: float):
        candidates = [(k, v) for k, v in self.valves.items() if v.position < 80]
        if candidates:
            _, v = min(candidates, key=lambda x: x[1].position)
            v.set_target(min(90.0, v.position + pct))

    # ------------------------------------------------------------------
    def set_valve_position(self, name: str, position: float):
        if name in self.valves:
            self.valves[name].set_target(position)

    def get_valve_position(self, name: str) -> float:
        return self.valves[name].position if name in self.valves else 0.0

    def get_all_positions(self) -> Dict[str, float]:
        return {n: v.position for n, v in self.valves.items()}

    def emergency_close_all(self):
        for v in self.valves.values():
            v.set_target(0.0)

    def reset_all_valves(self):
        for name, pos in self._DEFAULTS.items():
            self.valves[name].set_target(pos)

    def set_valve_auto_tune(self, name: str, enabled: bool):
        if name in self.valves:
            self.valves[name].auto_tune_enabled = enabled

    def get_valve_auto_tune(self, name: str) -> bool:
        return self.valves[name].auto_tune_enabled if name in self.valves else False

    def get_all_auto_tune_status(self) -> Dict[str, bool]:
        return {n: v.auto_tune_enabled for n, v in self.valves.items()}

    def apply_endpoint_adjustment(self, name: str, adjustment: float):
        if name in self.valves:
            v = self.valves[name]
            if v.auto_tune_enabled and self.auto_control_enabled:
                v.set_target(max(10.0, min(100.0, v.position + adjustment)))
