"""
Cascade Endpoints Simulation
Models 7 direct-use applications in a serial geothermal cascade.
Temperature decreases stage by stage along the chain.

Cascade order (highest T → lowest T):
  Cabin Warmer → Kolam Rendam → Pengering Teh → Food Dehydrator 1
  → Fish Pond → Food Dehydrator 2 → Green House → Discharge
"""
import random
import math

# Cascade definition: (id, display_name, base_demand_kg/h, target_T_in, target_T_out)
CASCADE_STAGES = [
    ('cabin',              'Cabin Warmer',      400, 162, 130),
    ('hot_pool',           'Kolam Rendam',       800, 130,  75),
    ('tea_dryer',          'Pengering Teh',      500,  75,  60),
    ('food_dehydrator_1',  'Food Dehydrator 1',  600,  60,  48),
    ('fish_pond',          'Fish Pond',          374,  48,  36),
    ('food_dehydrator_2',  'Food Dehydrator 2',  450,  36,  28),
    ('green_house',        'Green House',        300,  28,  24),
]


class SensorStatus:
    NORMAL        = "Normal"
    WARNING_LOW   = "Need Steam"
    WARNING_HIGH  = "Excess Steam"
    CRITICAL_LOW  = "Critical - Low Steam"
    CRITICAL_HIGH = "Critical - High Steam"


class CascadeStage:
    """Single stage in the geothermal cascade heat-use chain."""

    WATER_CP = 4.186  # kJ / (kg·°C)

    def __init__(self, stage_id: str, name: str, base_demand: float,
                 target_t_in: float, target_t_out: float):
        self.stage_id     = stage_id
        self.name         = name
        self.base_demand  = base_demand
        self.target_t_in  = target_t_in
        self.target_t_out = target_t_out
        self.tolerance    = 0.15

        # Runtime state
        self.current_demand  = float(base_demand)
        self.current_supply  = 0.0
        self.inlet_temp      = float(target_t_in)
        self.outlet_temp     = float(target_t_out)
        self.sensor_status   = SensorStatus.NORMAL

        # Computed parameters
        self.heat_duty_kw    = 0.0   # kW heat transferred
        self.pressure_drop   = 0.0   # bar
        self.efficiency      = 0.0   # % of max possible heat extraction
        self.flow_velocity   = 0.0   # m/s in 50mm pipe

        # Demand variation timer
        self._demand_timer     = 0.0
        self._demand_hold_time = random.uniform(15, 30)

    # ------------------------------------------------------------------
    def update(self, dt: float, valve_position: float,
               inlet_temperature: float, available_flow: float):
        """
        Args:
            dt               : delta-time (seconds)
            valve_position   : 0-100 %
            inlet_temperature: fluid temp entering this stage (°C)
            available_flow   : flow available at stage inlet (kg/h)
        """
        # --- demand variation ---
        self._demand_timer += dt
        if self._demand_timer >= self._demand_hold_time:
            self.current_demand    = self.base_demand * (1.0 + random.uniform(-0.1, 0.1))
            self._demand_timer     = 0.0
            self._demand_hold_time = random.uniform(15, 30)

        # --- flow through this stage ---
        self.current_supply = (valve_position / 100.0) * available_flow
        self.inlet_temp     = inlet_temperature

        if self.current_supply > 0 and inlet_temperature > 20:
            demand_ratio = min(1.0, self.current_demand / max(1.0, self.current_supply))
            max_drop     = self.target_t_in - self.target_t_out
            actual_drop  = max_drop * demand_ratio * (valve_position / 100.0)
            self.outlet_temp = max(20.0, inlet_temperature - actual_drop)

            # Heat duty  Q = ṁ · Cp · ΔT  (kW)
            m_dot = self.current_supply / 3600.0
            self.heat_duty_kw = m_dot * self.WATER_CP * (self.inlet_temp - self.outlet_temp) * 1000

            # Pressure drop: turbulent pipe model
            self.pressure_drop = 0.02 * (self.current_supply / 500.0) ** 1.8

            # Thermal efficiency vs maximum possible extraction
            max_heat = m_dot * self.WATER_CP * (inlet_temperature - 20.0) * 1000
            self.efficiency = min(100.0, self.heat_duty_kw / max(1.0, max_heat) * 100.0)

            # Flow velocity (50mm pipe, ρ ≈ 900 kg/m³)
            pipe_area          = math.pi * 0.025 ** 2
            self.flow_velocity = (available_flow / 3600.0) / (900.0 * pipe_area)
        else:
            self.outlet_temp   = inlet_temperature
            self.heat_duty_kw  = 0.0
            self.pressure_drop = 0.0
            self.efficiency    = 0.0
            self.flow_velocity = 0.0

        self._update_sensor_status()

    def _update_sensor_status(self):
        if self.current_supply == 0:
            self.sensor_status = SensorStatus.CRITICAL_LOW
            return
        dev = (self.current_supply - self.current_demand) / self.current_demand
        if abs(dev) <= self.tolerance:
            self.sensor_status = SensorStatus.NORMAL
        elif dev < -self.tolerance * 2:
            self.sensor_status = SensorStatus.CRITICAL_LOW
        elif dev < -self.tolerance:
            self.sensor_status = SensorStatus.WARNING_LOW
        elif dev > self.tolerance * 2:
            self.sensor_status = SensorStatus.CRITICAL_HIGH
        elif dev > self.tolerance:
            self.sensor_status = SensorStatus.WARNING_HIGH
        else:
            self.sensor_status = SensorStatus.NORMAL

    def get_sensor_color(self):
        if self.sensor_status == SensorStatus.NORMAL:
            return (0, 255, 100)
        if self.sensor_status in (SensorStatus.WARNING_LOW, SensorStatus.WARNING_HIGH):
            return (255, 200, 0)
        return (255, 50, 50)

    def needs_adjustment(self):
        return self.sensor_status != SensorStatus.NORMAL

    def get_recommended_adjustment(self):
        if self.sensor_status == SensorStatus.NORMAL:
            return 0
        dev = (self.current_supply - self.current_demand) / self.current_demand
        if self.sensor_status in (SensorStatus.CRITICAL_LOW, SensorStatus.WARNING_LOW):
            return 20 if abs(dev) > 0.3 else 10
        return -20 if abs(dev) > 0.3 else -10


class CascadeManager:
    """Manages all 7 cascade stages in serial (chain) flow order."""

    def __init__(self):
        self.stages      = {}
        self.stage_order = []
        for stage_id, name, demand, t_in, t_out in CASCADE_STAGES:
            self.stages[stage_id] = CascadeStage(stage_id, name, demand, t_in, t_out)
            self.stage_order.append(stage_id)

        # Geochemistry parameters
        self.ph          = 6.5
        self.tds_mg_l    = 2500.0
        self.silica_mg_l = 450.0
        self.silica_risk = "Low"

    def update(self, dt: float, valve_positions: dict,
               main_temp: float, main_flow: float):
        """Propagate cascade: outlet T of stage N → inlet T of stage N+1."""
        current_temp = main_temp
        current_flow = main_flow

        for sid in self.stage_order:
            stage   = self.stages[sid]
            v_pos   = valve_positions.get(sid, 0.0)
            stage.update(dt, v_pos, current_temp, current_flow)
            current_temp = stage.outlet_temp
            # Small fraction consumed; remaining continues downstream
            current_flow = max(0.0, current_flow - stage.current_supply * 0.03)

        self._update_geochemistry(main_temp)

    def _update_geochemistry(self, temp: float):
        self.ph       = max(5.0,  min(7.5,  self.ph  + random.uniform(-0.01, 0.01)))
        self.tds_mg_l = max(2000, min(3500,  self.tds_mg_l + random.uniform(-20, 20)))
        if temp < 80:
            self.silica_risk = "High"
        elif temp < 120:
            self.silica_risk = "Medium"
        else:
            self.silica_risk = "Low"

    def get_all_sensor_status(self) -> dict:
        return {
            sid: {
                'status':                 s.sensor_status,
                'color':                  s.get_sensor_color(),
                'demand':                 s.current_demand,
                'supply':                 s.current_supply,
                'needs_adjustment':       s.needs_adjustment(),
                'recommended_adjustment': s.get_recommended_adjustment(),
                'inlet_temp':             s.inlet_temp,
                'outlet_temp':            s.outlet_temp,
                'heat_duty_kw':           s.heat_duty_kw,
                'pressure_drop':          s.pressure_drop,
                'efficiency':             s.efficiency,
                'flow_velocity':          s.flow_velocity,
            }
            for sid, s in self.stages.items()
        }

    def get_geochemistry(self) -> dict:
        return {
            'ph':          self.ph,
            'tds_mg_l':    self.tds_mg_l,
            'silica_mg_l': self.silica_mg_l,
            'silica_risk': self.silica_risk,
        }

    def get_total_heat_duty_kw(self) -> float:
        return sum(s.heat_duty_kw for s in self.stages.values())

    def get_endpoint(self, sid: str):
        return self.stages.get(sid)

    # Legacy alias for compatibility
    @property
    def endpoints(self):
        return self.stages


# Keep legacy class name for any external references
EndpointManager = CascadeManager
