"""
Main Simulator
Orchestrates steam source, valve controller, and cascade endpoints.
Provides unified state interface for the UI.
"""
import time
from simulation.steam_source import SteamSource, SystemState
from simulation.valve_controller import ValveController
from simulation.endpoints import CascadeManager


class GeothermalSimulator:
    """Orchestrates all simulation components."""

    def __init__(self):
        self.steam_source    = SteamSource()
        self.valve_controller = ValveController()
        self.cascade_manager  = CascadeManager()

        self.last_update = time.time()
        self.is_running  = True

        # Legacy alias used by some UI references
        self.endpoint_manager = self.cascade_manager

    def update(self):
        """Advance simulation one time-step (called ~10 Hz)."""
        if not self.is_running:
            return

        current_time = time.time()
        dt = min(current_time - self.last_update, 0.5)
        self.last_update = current_time

        # 1. Update steam source
        self.steam_source.update(dt)

        pressure    = self.steam_source.pressure
        temperature = self.steam_source.temperature
        flow        = self.steam_source.flow

        # 2. Update cascade with current valve positions
        valve_positions = self.valve_controller.get_all_positions()
        self.cascade_manager.update(dt, valve_positions, temperature, flow)

        # 3. Pressure-based valve auto-control
        self.valve_controller.update(dt, pressure)

        # 4. Per-stage auto-tune adjustments
        if self.valve_controller.auto_control_enabled:
            for sid, status in self.cascade_manager.get_all_sensor_status().items():
                if status['needs_adjustment']:
                    self.valve_controller.apply_endpoint_adjustment(
                        sid, status['recommended_adjustment'])

    def get_state(self) -> dict:
        """Return unified state dict for UI consumption."""
        si      = self.steam_source.get_state_info()
        sensors = self.cascade_manager.get_all_sensor_status()
        geochem = self.cascade_manager.get_geochemistry()

        return {
            # Main steam
            'pressure':             si['pressure'],
            'temperature':          si['temperature'],
            'flow':                 si['flow'],
            'state':                si['state'],
            'disturbance_active':   si['disturbance_active'],
            # Valves
            'valve_positions':      self.valve_controller.get_all_positions(),
            'valve_auto_tune':      self.valve_controller.get_all_auto_tune_status(),
            'auto_control_enabled': self.valve_controller.auto_control_enabled,
            'last_control_action':  self.valve_controller.last_action,
            # Cascade stages (includes inlet_temp, outlet_temp, heat_duty_kw, efficiency, ...)
            'endpoint_sensors':     sensors,
            # System-wide derived data
            'geochemistry':         geochem,
            'total_heat_duty_kw':   self.cascade_manager.get_total_heat_duty_kw(),
        }

    def reset(self):
        self.steam_source.reset()
        self.valve_controller.reset_all_valves()
        self.is_running = True

    def emergency_shutdown(self):
        self.steam_source.trigger_emergency()
        self.valve_controller.emergency_close_all()

    def set_valve_position(self, valve_id: str, position: float):
        self.valve_controller.set_valve_position(valve_id, position)

    def toggle_auto_control(self, enabled: bool):
        self.valve_controller.auto_control_enabled = enabled

    def set_mode(self, mode: str) -> None:
        """Switch cascade physics mode: 'scada' (tight, ±1.5°C) or 'sequential' (loose, ±5°C)."""
        self.cascade_manager.set_mode(mode)
