"""
Cascade Endpoints Simulation
Thermodynamically accurate model for geothermal direct-use cascade.

Physics (primary / geothermal side):
    m_dot_actual  = m_dot_max × (valve_position / 100)           [kg/h]
    T_geo_out     = T_inlet - Q_demand / (m_dot_actual_kg_s × Cp) [°C]

Physics (secondary / application side):
    m_dot_app     = Q_demand / ((T_target - T_app_in) × Cp)      [kg/s]
    T_app_out     = T_app_in + Q_actual / (m_dot_app × Cp)       [°C]
    CONSTRAINT:   T_app_out ≤ T_geo_out  (2nd Law of Thermodynamics)

Cascade serial order (high-T → low-T):
    T_geo_out of stage N  →  T_inlet of stage N+1

Application temperature filter ranges (secondary / process side):
    Tea Drying      : 95–98 °C
    Food Dehydrator : 53–56 °C
    Cabin Heating   : 43–47 °C
    Hot Pool        : 36–40 °C
    Fish Pond       : 24–30 °C
    Greenhouse      : 21–26 °C

Valve → Flow → Temperature relationship:
    Larger valve  →  more primary flow  →  T_geo_out LOWER (more ΔT across HX)
    Smaller valve →  less primary flow  →  T_geo_out HIGHER (less ΔT across HX)
"""
import math
import random

WATER_CP   = 4.186   # kJ/(kg·K) — liquid water / condensate
STEAM_CP   = 2.010   # kJ/(kg·K) — superheated steam
T_AMBIENT  = 12.5    # °C — environment temperature (Patuha highland)

# Physical temperature limits per unit (°C) — process / secondary side
UNIT_LIMITS: dict = {
    'tea_dryer':         (95,  98),
    'food_dehydrator_1': (53,  56),
    'cabin':             (43,  47),
    'hot_pool':          (36,  40),
    'fish_pond':         (24,  30),
    'green_house':       (21,  26),
}

# Per-application design parameters from P&ID (primary geothermal circuit)
APPLICATION_DATA: dict = {
    'tea_dryer': {
        'm_dot_max': 391.0,   # kg/h — max geothermal primary flow through HX
        'Q_demand':   35.0,   # kW   — heat demand
        'T_target':   96.5,   # °C   — secondary outlet target
        'T_app_in':   80.0,   # °C   — secondary inlet temperature
    },
    'food_dehydrator_1': {
        'm_dot_max': 714.0,
        'Q_demand':   69.0,
        'T_target':   54.5,
        'T_app_in':   40.0,
    },
    'cabin': {
        'm_dot_max': 327.0,
        'Q_demand':   15.0,
        'T_target':   45.0,
        'T_app_in':   30.0,
    },
    'hot_pool': {
        'm_dot_max': 766.0,
        'Q_demand':  502.0,   # NOTE: 502 kW likely a typo for 50.2 kW in P&ID data;
        # with m_dot_max=766 kg/h the max extractable heat is ~141 kW, so hot_pool
        # will always show Critical Low status until this figure is corrected.
        'T_target':   38.0,
        'T_app_in':   25.0,
    },
    'fish_pond': {
        'm_dot_max': 321.0,
        'Q_demand':    8.0,
        'T_target':   27.0,
        'T_app_in':   20.0,
    },
    'green_house': {
        'm_dot_max': 320.0,
        'Q_demand':    8.0,
        'T_target':   23.5,
        'T_app_in':   18.0,
    },
}

# Cascade order: high-T applications first so cooled fluid serves low-T stages
CASCADE_STAGES = [
    ('tea_dryer',         'Tea Dryer'),
    ('food_dehydrator_1', 'Food Dehydrator'),
    ('cabin',             'Cabin Heating'),
    ('hot_pool',          'Hot Pool'),
    ('fish_pond',         'Fish Pond'),
    ('green_house',       'Green House'),
]

# Pipe geometry
BRANCH_PIPE_D  = 0.0254   # m — branch pipe inner diameter
PIPE_ROUGHNESS = 1.5e-5   # m — commercial steel


class SensorStatus:
    NORMAL        = "Normal"
    WARNING_LOW   = "Need Steam"
    WARNING_HIGH  = "Excess Steam"
    CRITICAL_LOW  = "Critical Low"
    CRITICAL_HIGH = "Critical High"


def _darcy_pressure_drop(flow_kg_h: float, pipe_d: float,
                          pipe_length: float = 8.0,
                          rho: float = 850.0, mu: float = 3e-4) -> float:
    """Darcy-Weisbach pressure drop in bar."""
    if flow_kg_h <= 0:
        return 0.0
    flow_kg_s = flow_kg_h / 3600.0
    area = math.pi * (pipe_d / 2) ** 2
    v = flow_kg_s / (rho * area)
    if v < 1e-6:
        return 0.0
    Re = rho * v * pipe_d / mu
    f  = 64 / Re if Re < 2300 else 0.0791 * Re ** (-0.25)
    dp_pa = f * (pipe_length / pipe_d) * rho * v ** 2 / 2
    return dp_pa / 1e5


class CascadeStage:
    """
    Single stage in the geothermal cascade heat-use chain.

    Primary side (geothermal fluid): flows m_dot_actual through the HX,
    exits at T_geo_out which then becomes the inlet for the next cascade stage.

    Secondary side (application circuit): receives heat Q and exits at T_app_out,
    which is always ≤ T_geo_out (2nd Law constraint).
    """

    def __init__(self, stage_id: str, name: str):
        self.stage_id = stage_id
        self.name     = name

        app = APPLICATION_DATA[stage_id]
        unit_min, unit_max = UNIT_LIMITS.get(stage_id, (T_AMBIENT, 200.0))

        # Runtime state — initialised to design-point values so startup looks Normal
        self.flow_rate_kg_h = app['m_dot_max']
        self.inlet_temp     = app['T_target']
        self.outlet_temp    = app['T_target']   # primary-side outlet (cascades to next stage)
        self.process_outlet = app['T_target']   # secondary-side display temperature
        self.heat_duty_kw   = app['Q_demand']
        self.pressure_drop  = 0.0
        self.efficiency     = 100.0
        self.flow_velocity  = 0.0
        self.sensor_status  = SensorStatus.NORMAL

        # Thermal inertia time constant (seconds) — set by mode
        self._tau = 30.0

        # Demand variation (stochastic noise)
        self._demand_timer     = 0.0
        self._demand_hold_time = random.uniform(15, 30)
        self._demand_factor    = 1.0   # multiplicative perturbation on Q_demand

        # Mode parameters (updated by CascadeManager.set_mode)
        self._heat_loss_coeff = 0.003   # kJ per °C above ambient per second
        self._demand_noise    = 0.03    # ±amplitude of demand variation
        self._rob_prob        = 0.03    # Bernoulli probability of heat-robbing event

    # ── public update ──────────────────────────────────────────────────────────

    def update(self, dt: float, valve_position: float,
               inlet_temperature: float, available_flow: float):
        """
        Advance one time-step.

        Args:
            dt               : delta-time (seconds)
            valve_position   : 0–100 %  (controls primary-side flow)
            inlet_temperature: primary-fluid inlet °C from upstream stage
            available_flow   : total geothermal flow available (kg/h) — informational
        """
        app = APPLICATION_DATA[self.stage_id]
        CP  = WATER_CP  # kJ/(kg·K)

        # ── Stochastic demand variation ────────────────────────────────────────
        self._demand_timer += dt
        if self._demand_timer >= self._demand_hold_time:
            self._demand_factor    = 1.0 + random.uniform(-self._demand_noise,
                                                           self._demand_noise)
            self._demand_timer     = 0.0
            self._demand_hold_time = random.uniform(15, 30)

        # ── Primary flow via valve ─────────────────────────────────────────────
        m_dot_kg_h = app['m_dot_max'] * (valve_position / 100.0)
        m_dot_kg_s = m_dot_kg_h / 3600.0

        self.flow_rate_kg_h = m_dot_kg_h
        self.inlet_temp     = inlet_temperature

        if m_dot_kg_s < 1e-6 or inlet_temperature <= T_AMBIENT:
            # No flow → primary passes through unchanged; unit gets no heat
            self.outlet_temp    = inlet_temperature
            self.process_outlet = app['T_app_in']
            self.heat_duty_kw   = 0.0
            self.pressure_drop  = 0.0
            self.efficiency     = 0.0
            self.flow_velocity  = 0.0
            self._update_sensor_status()
            return

        # ── Thermodynamic model ────────────────────────────────────────────────
        Q_demand = app['Q_demand'] * self._demand_factor   # kW

        # Bernoulli heat-robbing event: occasional extra extraction
        if random.random() < self._rob_prob:
            Q_demand *= (1.0 + random.uniform(0.05, 0.15))

        # PRIMARY SIDE — Formula: T_geo_out = T_inlet - Q / (m_dot × Cp)
        # (rearranged heat balance: Q = m_dot × Cp × ΔT)
        T_geo_raw = inlet_temperature - Q_demand / (m_dot_kg_s * CP)

        # Pipe heat loss to environment
        heat_loss_kw = self._heat_loss_coeff * max(0.0, T_geo_raw - T_AMBIENT) * dt
        T_geo_raw -= heat_loss_kw / (m_dot_kg_s * CP) if m_dot_kg_s > 0 else 0.0

        # Physical bound: cannot cool below ambient
        T_geo_out = max(T_AMBIENT, T_geo_raw)

        # Actual heat transferred (may be less than Q_demand when physically limited)
        Q_actual = m_dot_kg_s * CP * max(0.0, inlet_temperature - T_geo_out)

        # SECONDARY SIDE — design flow from Q / ((T_target - T_app_in) × Cp)
        T_app_in = app['T_app_in']
        T_target = app['T_target']
        delta_app = T_target - T_app_in

        if delta_app > 0.1 and Q_actual > 0.0:
            m_dot_app_kg_s = app['Q_demand'] / (delta_app * CP)  # fixed design flow
            T_app_raw = T_app_in + Q_actual / (m_dot_app_kg_s * CP)
        else:
            T_app_raw = T_app_in

        # 2nd-Law constraint: application outlet ≤ geothermal outlet
        T_app_out = min(T_app_raw, T_geo_out)
        T_app_out = max(T_AMBIENT, T_app_out)

        # ── Cascade propagation: outlet_temp updates instantly so the next stage
        #    sees the correct inlet temperature immediately when a valve changes.
        self.outlet_temp = T_geo_out

        # ── Process (secondary) display: smoothed with thermal inertia so the
        #    UI graph shows realistic ramp rather than step changes.
        alpha = dt / (self._tau + dt)
        self.process_outlet = self.process_outlet + alpha * (T_app_out - self.process_outlet)

        # ── Derived metrics ────────────────────────────────────────────────────
        self.heat_duty_kw  = Q_actual
        self.efficiency    = min(100.0, Q_actual / max(0.1, app['Q_demand']) * 100.0)
        self.pressure_drop = _darcy_pressure_drop(m_dot_kg_h, BRANCH_PIPE_D)

        area = math.pi * (BRANCH_PIPE_D / 2) ** 2
        self.flow_velocity = m_dot_kg_s / (850.0 * area)

        self._update_sensor_status()

    # ── status ─────────────────────────────────────────────────────────────────

    def _update_sensor_status(self):
        """Determine sensor status from secondary-side temperature vs UNIT_LIMITS."""
        if self.flow_rate_kg_h < 1.0:
            self.sensor_status = SensorStatus.CRITICAL_LOW
            return

        unit_min, unit_max = UNIT_LIMITS.get(self.stage_id, (T_AMBIENT, 200.0))
        temp = self.process_outlet

        if unit_min <= temp <= unit_max:
            self.sensor_status = SensorStatus.NORMAL
        elif temp > unit_max:
            self.sensor_status = (SensorStatus.CRITICAL_HIGH if temp > unit_max + 5
                                  else SensorStatus.WARNING_HIGH)
        else:  # temp < unit_min
            self.sensor_status = (SensorStatus.CRITICAL_LOW if temp < unit_min - 5
                                  else SensorStatus.WARNING_LOW)

    def get_sensor_color(self):
        if self.sensor_status == SensorStatus.NORMAL:
            return (0, 220, 100)
        if self.sensor_status in (SensorStatus.WARNING_LOW, SensorStatus.WARNING_HIGH):
            return (255, 195, 0)
        return (255, 50, 50)

    def needs_adjustment(self) -> bool:
        return self.sensor_status != SensorStatus.NORMAL

    def get_recommended_adjustment(self) -> float:
        """Return suggested valve position delta (%) to move toward Normal."""
        if self.sensor_status == SensorStatus.NORMAL:
            return 0.0
        if self.sensor_status in (SensorStatus.CRITICAL_HIGH, SensorStatus.WARNING_HIGH):
            return -10.0 if self.sensor_status == SensorStatus.CRITICAL_HIGH else -5.0
        return  10.0 if self.sensor_status == SensorStatus.CRITICAL_LOW  else  5.0


class CascadeManager:
    """Manages all cascade stages in serial (chain) flow order."""

    def __init__(self):
        self.stages: dict      = {}
        self.stage_order: list = []
        for stage_id, name in CASCADE_STAGES:
            self.stages[stage_id] = CascadeStage(stage_id, name)
            self.stage_order.append(stage_id)

        self.stage_inlet_temps:  dict = {}
        self.stage_outlet_temps: dict = {}

        # Geochemistry (slowly varying)
        self.ph          = 6.5
        self.tds_mg_l    = 2500.0
        self.silica_mg_l = 450.0
        self.silica_risk = "Low"

        # Architecture mode: 'scada' (p=0.03, tight) or 'sequential' (p=0.18, loose)
        self._mode = 'scada'
        self._apply_mode_params()

    # ── mode switching ─────────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        """Switch between 'scada' and 'sequential' physics mode."""
        self._mode = mode
        self._apply_mode_params()

    def _apply_mode_params(self) -> None:
        """Push mode-specific physics parameters to every stage."""
        if self._mode == 'scada':
            # SCADA: tight control, fast PID response — visible in ~3s at 10 Hz
            tau          = 3.0     # seconds — fast thermal response for display
            heat_loss    = 0.003   # kJ per °C·s
            demand_noise = 0.03    # ±3% demand variation
            rob_prob     = 0.03    # 3% Bernoulli heat-robbing probability
        else:
            # Sequential / IoT: loose control, slower response, higher losses
            tau          = 15.0    # seconds — sluggish response visible at 10 Hz
            heat_loss    = 0.012
            demand_noise = 0.08
            rob_prob     = 0.18

        for stage in self.stages.values():
            stage._tau            = tau
            stage._heat_loss_coeff = heat_loss
            stage._demand_noise   = demand_noise
            stage._rob_prob       = rob_prob

    # ── main update loop ───────────────────────────────────────────────────────

    def update(self, dt: float, valve_positions: dict,
               main_temp: float, main_flow: float) -> None:
        """
        Update all cascade stages in parallel.

        Each stage independently draws from the geothermal wellhead at main_temp
        (confirmed by the prompt examples where every stage sees T_source=170.9°C).
        Cascade order is preserved conceptually (high-T → low-T units) but the
        primary fluid temperature does NOT cascade serially — each branch is fed
        directly from the main header.
        """
        current_flow = main_flow

        for sid in self.stage_order:
            stage = self.stages[sid]
            v_pos = valve_positions.get(sid, 0.0)

            # Parallel architecture: every stage sees the wellhead temperature
            self.stage_inlet_temps[sid] = main_temp
            stage.update(dt, v_pos, main_temp, current_flow)
            self.stage_outlet_temps[sid] = stage.outlet_temp

            # Reduce available flow by condensate consumed at this stage (~5%)
            current_flow = max(0.0, current_flow - stage.flow_rate_kg_h * 0.05)

        self._update_geochemistry(main_temp)

    # ── geochemistry (slowly varying display data) ─────────────────────────────

    def _update_geochemistry(self, temp: float) -> None:
        self.ph       = max(5.0,  min(7.5,  self.ph       + random.uniform(-0.01,  0.01)))
        self.tds_mg_l = max(2000, min(3500,  self.tds_mg_l + random.uniform(-15,    15)))
        self.silica_risk = ("High" if temp < 80
                            else "Medium" if temp < 120
                            else "Low")

    # ── accessors ──────────────────────────────────────────────────────────────

    def get_all_sensor_status(self) -> dict:
        return {
            sid: {
                'status':                 s.sensor_status,
                'color':                  s.get_sensor_color(),
                'flow_rate_kg_h':         s.flow_rate_kg_h,
                'demand':                 APPLICATION_DATA[sid]['Q_demand'],
                'supply':                 s.flow_rate_kg_h,
                'needs_adjustment':       s.needs_adjustment(),
                'recommended_adjustment': s.get_recommended_adjustment(),
                'inlet_temp':             s.inlet_temp,
                'outlet_temp':            s.outlet_temp,
                'process_outlet':         s.process_outlet,
                'heat_duty_kw':           s.heat_duty_kw,
                'pressure_drop':          s.pressure_drop,
                'efficiency':             s.efficiency,
                'flow_velocity':          s.flow_velocity,
                # Convenience keys used by some UI widgets
                'process_temp':           s.process_outlet,
                'T_target':               APPLICATION_DATA[sid]['T_target'],
                'T_app_in':               APPLICATION_DATA[sid]['T_app_in'],
                'm_dot_max':              APPLICATION_DATA[sid]['m_dot_max'],
                'Q_demand':               APPLICATION_DATA[sid]['Q_demand'],
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
