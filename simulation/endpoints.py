"""
Cascade Endpoints Simulation
Refactored for accurate temperature degradation and flow random
"""
import math
import random

WATER_CP = 4.186   # kJ/(kg·C)  -- liquid water / condensate
STEAM_CP = 2.010   # kJ/(kg·C)  -- superheated steam

# [ADDED] Wellhead temperature safety limits
WELLHEAD_SAFETY_CLAMP = 160.0   # °C — emergency override when main_temp > 170°C
WELLHEAD_NORMAL_MAX   = 140.0   # °C — maximum allowed from wellhead under normal operation
T_AMBIENT             = 20.0    # °C — environment temperature used for heat-loss calculation

# [ADDED] Physical temperature limits per unit (°C) — enforced strictly each timestep
UNIT_LIMITS: dict = {
    'tea_dryer':         (95,  98),
    'food_dehydrator_1': (53,  56),
    'food_dehydrator_2': (53,  56),
    'cabin':             (26,  38),
    'hot_pool':          (27,  38),
    'fish_pond':         (24,  30),
    'green_house':       (21,  26),
}

# [MODIFIED] Cascade ordered high-T → low-T so each stage receives sufficient
# inlet temperature from upstream.  Serial chain: outlet_N → inlet_(N+1).
CASCADE_STAGES = [
    # (id, name, base_demand_kg/h, target_T_in_dari_header, target_T_out_process)
    ('tea_dryer',         'Tea Dryer',          500, 140, 96),
    ('food_dehydrator_1', 'Food Dehydrator 1',  600,  96, 54),
    ('food_dehydrator_2', 'Food Dehydrator 2',  450,  54, 54),
    ('cabin',             'Cabin Warmer',        400,  54, 32),
    ('hot_pool',          'Hot Pool',            800,  32, 30),
    ('fish_pond',         'Fish Pond',           374,  30, 27),
    ('green_house',       'Green House',         300,  27, 23),
]

# Pipe diameter per branch (meters)
BRANCH_PIPE_D = 0.0254
MAIN_PIPE_D   = 0.0508
PIPE_ROUGHNESS = 1.5e-5   # commercial steel, m

class SensorStatus:
    NORMAL        = "Normal"
    WARNING_LOW   = "Need Steam"
    WARNING_HIGH  = "Excess Steam"
    CRITICAL_LOW  = "Critical Low"
    CRITICAL_HIGH = "Critical High"

def _darcy_pressure_drop(flow_kg_h: float, pipe_d: float, pipe_length: float = 8.0,
                          rho: float = 850.0, mu: float = 3e-4) -> float:
    """
    Darcy-Weisbach pressure drop in bar.
    """
    if flow_kg_h <= 0:
        return 0.0
    flow_kg_s = flow_kg_h / 3600.0
    area = math.pi * (pipe_d / 2) ** 2
    v = flow_kg_s / (rho * area)
    if v < 1e-6:
        return 0.0
    Re = rho * v * pipe_d / mu
    if Re < 2300:
        f = 64 / Re  # laminar
    else:
        # Colebrook approximation
        f = 0.0791 * Re ** (-0.25)
    dp_pa = f * (pipe_length / pipe_d) * rho * v ** 2 / 2
    return dp_pa / 1e5  # convert to bar

#
class CascadeStage:
    """Single stage in the geothermal cascade heat-use chain."""

    def __init__(self, stage_id: str, name: str, base_demand: float,
                 target_t_in: float, target_t_out: float):
        self.stage_id       = stage_id
        self.name           = name
        self.base_demand    = float(base_demand)
        self.target_t_in    = float(target_t_in)
        self.target_t_out   = float(target_t_out)
        self.t_process_req  = float(target_t_out)  # process target = outlet target
        self.tolerance      = 0.12

        # Runtime state
        self.current_demand  = float(base_demand)   # demand flow (kg/h), varies over time
        self.flow_rate_kg_h  = float(base_demand)   # actual flow through this stage
        self.inlet_temp      = float(target_t_in)
        self.outlet_temp     = float(target_t_out)
        self.process_outlet  = float(target_t_out)
        self.heat_duty_kw    = 0.0
        self.pressure_drop   = 0.0                  # bar
        self.efficiency      = 0.0                  # %
        self.flow_velocity   = 0.0                  # m/s
        self.sensor_status   = SensorStatus.NORMAL

        # Demand variation timer
        self._demand_timer     = 0.0
        self._demand_hold_time = random.uniform(15, 30)

        # [ADDED] Thermal inertia and safety state
        self._tau             = 30.0   # thermal time constant (seconds)
        self._safety_override = False  # True when T was clamped to unit limit

    def update(self, dt: float, valve_position: float,
            inlet_temperature: float, available_flow: float):
        """
        Args:
            dt               : delta-time (seconds)
            valve_position   : 0-100 %
            inlet_temperature: suhu fluida masuk dari header (degC)
            available_flow   : flow yang dialokasikan ke stage ini (kg/h)
        """
        # Vary demand slowly every 15-30 seconds
        self._demand_timer += dt
        if self._demand_timer >= self._demand_hold_time:
            self.current_demand    = self.base_demand * (1.0 + random.uniform(-0.08, 0.08))
            self._demand_timer     = 0.0
            self._demand_hold_time = random.uniform(15, 30)

        # Actual flow through this stage, gated by valve position
        self.flow_rate_kg_h = (valve_position / 100.0) * available_flow
        self.inlet_temp     = inlet_temperature

        if self.flow_rate_kg_h > 0.5 and inlet_temperature > T_AMBIENT:
            # [MODIFIED] Thermal model: T_out proportional to valve (flow) fraction
            flow_effect = valve_position / 100.0
            T_raw = inlet_temperature * flow_effect

            # [ADDED] Heat loss to environment (proportional to temperature excess)
            heat_loss = 0.003 * max(0.0, T_raw - T_AMBIENT) * dt
            T_raw = max(T_AMBIENT, T_raw - heat_loss)

            # [ADDED] Thermal inertia — exponential filter prevents instantaneous jumps
            alpha = dt / (self._tau + dt)
            T_filtered = self.outlet_temp + alpha * (T_raw - self.outlet_temp)

            # [ADDED] Enforce unit temperature limits (fail-safe clamp)
            unit_min, unit_max = UNIT_LIMITS.get(self.stage_id, (T_AMBIENT, 100.0))
            self._safety_override = T_filtered > unit_max or T_filtered < unit_min
            self.outlet_temp = max(unit_min, min(unit_max, T_filtered))

            # Process outlet temperature (with slight random deviation, within limits)
            process_deviation   = random.uniform(-1.5, 1.5)
            self.process_outlet = max(unit_min,
                                    min(unit_max,
                                        self.t_process_req + process_deviation))

            # Heat duty: Q = m_dot[kg/s] * Cp[kJ/kg°C] * dT[°C] = kW  (no ×1000)
            m_dot_kg_s     = self.flow_rate_kg_h / 3600.0
            actual_dt_real = max(0.0, inlet_temperature - self.outlet_temp)
            self.heat_duty_kw = m_dot_kg_s * WATER_CP * actual_dt_real

            # Pressure drop via Darcy-Weisbach
            self.pressure_drop = _darcy_pressure_drop(self.flow_rate_kg_h, BRANCH_PIPE_D)

            # Thermal efficiency vs max possible extraction
            max_dt_possible = max(0.1, inlet_temperature - self.t_process_req)
            q_max = m_dot_kg_s * WATER_CP * max_dt_possible * 1000.0
            self.efficiency = min(100.0, self.heat_duty_kw / max(1.0, q_max) * 100.0)

            # Flow velocity in branch pipe
            area = math.pi * (BRANCH_PIPE_D / 2) ** 2
            self.flow_velocity = m_dot_kg_s / (850.0 * area)

        else:
            # No flow — no heat transfer
            self.outlet_temp    = inlet_temperature
            self.process_outlet = inlet_temperature
            self.heat_duty_kw   = 0.0
            self.pressure_drop  = 0.0
            self.efficiency     = 0.0
            self.flow_velocity  = 0.0
            self._safety_override = False

        self._update_sensor_status()

# #
    
    def _update_sensor_status(self):
        if self.flow_rate_kg_h < 1.0:
            self.sensor_status = SensorStatus.CRITICAL_LOW
            return
        dev = (self.flow_rate_kg_h - self.current_demand) / max(1.0, self.current_demand)
        tol = self.tolerance
        if abs(dev) <= tol:
            self.sensor_status = SensorStatus.NORMAL
        elif dev < -tol * 2:
            self.sensor_status = SensorStatus.CRITICAL_LOW
        elif dev < -tol:
            self.sensor_status = SensorStatus.WARNING_LOW
        elif dev > tol * 2:
            self.sensor_status = SensorStatus.CRITICAL_HIGH
        elif dev > tol:
            self.sensor_status = SensorStatus.WARNING_HIGH
        else:
            self.sensor_status = SensorStatus.NORMAL

    def get_sensor_color(self):
        if self.sensor_status == SensorStatus.NORMAL:
            return (0, 220, 100)
        if self.sensor_status in (SensorStatus.WARNING_LOW, SensorStatus.WARNING_HIGH):
            return (255, 195, 0)
        return (255, 50, 50)

    def needs_adjustment(self):
        return self.sensor_status != SensorStatus.NORMAL

    def get_recommended_adjustment(self):
        if self.sensor_status == SensorStatus.NORMAL:
            return 0
        dev = (self.flow_rate_kg_h - self.current_demand) / max(1.0, self.current_demand)
        if self.sensor_status in (SensorStatus.CRITICAL_LOW, SensorStatus.WARNING_LOW):
            return 15 if abs(dev) > 0.25 else 8
        return -15 if abs(dev) > 0.25 else -8

#
class CascadeManager:
    """Manages all 7 cascade stages in serial (chain) flow order."""

    def __init__(self):
        self.stages      = {}
        self.stage_order = []
        for stage_id, name, demand, t_in, t_out in CASCADE_STAGES:
            self.stages[stage_id] = CascadeStage(stage_id, name, demand, t_in, t_out)
            self.stage_order.append(stage_id)

        self.ph          = 6.5
        self.tds_mg_l    = 2500.0
        self.silica_mg_l = 450.0
        self.silica_risk = "Low"

        # Data propagasi untuk akses UI
        self.stage_inlet_temps:  dict = {}
        self.stage_outlet_temps: dict = {}

    def update(self, dt: float, valve_positions: dict,
               main_temp: float, main_flow: float):
        """
        Propagate cascade serial:
        outlet temperature stage N menjadi inlet temperature stage N+1.
        Flow berkurang sedikit tiap stage (konsumsi kondensat).
        """
        # [ADDED] Wellhead safety clamp before cascade entry
        if main_temp > 170.0:
            current_temp = WELLHEAD_SAFETY_CLAMP   # emergency override at 160°C
        else:
            current_temp = min(main_temp, WELLHEAD_NORMAL_MAX)  # normal cap at 140°C
        current_flow = main_flow

        for sid in self.stage_order:
            stage   = self.stages[sid]
            v_pos   = valve_positions.get(sid, 0.0)

            # Simpan inlet sebelum update
            self.stage_inlet_temps[sid] = current_temp

            stage.update(dt, v_pos, current_temp, current_flow)

            # Simpan outlet setelah update
            self.stage_outlet_temps[sid] = stage.outlet_temp

            # Outlet temperature stage ini = inlet stage berikutnya
            current_temp = stage.outlet_temp

            # Flow berkurang: sebagian dikonsumsi sebagai kondensat (~5% per stage)
            consumed = stage.flow_rate_kg_h * 0.05
            current_flow = max(0.0, current_flow - consumed)

        self._update_geochemistry(main_temp)

    def _update_geochemistry(self, temp: float):
        self.ph       = max(5.0,  min(7.5,  self.ph  + random.uniform(-0.01, 0.01)))
        self.tds_mg_l = max(2000, min(3500,  self.tds_mg_l + random.uniform(-15, 15)))
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
            'supply':                 s.flow_rate_kg_h,   # ← ganti current_supply
            'flow_rate_kg_h':         s.flow_rate_kg_h,
            'needs_adjustment':       s.needs_adjustment(),
            'recommended_adjustment': s.get_recommended_adjustment(),
            'inlet_temp':             s.inlet_temp,
            'outlet_temp':            s.outlet_temp,
            'heat_duty_kw':           s.heat_duty_kw,
            'pressure_drop':          s.pressure_drop,
            'efficiency':             s.efficiency,
            'flow_velocity':          s.flow_velocity,
            'safety_override':        s._safety_override,  # [ADDED] fail-safe clamp flag
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

    @property
    def endpoints(self):
        return self.stages

