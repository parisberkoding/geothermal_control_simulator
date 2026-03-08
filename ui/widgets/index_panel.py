"""
Index Panel – E-1 through E-100 parameter index
Inspired by industrial SCADA index displays (similar to АСОДУ ПТК РАДИУС style),
but all text and labels are in English.

Displays a scrollable grid of 100 parameter rows, each showing:
  Tag | Description | Value | Unit | Status badge
"""
from __future__ import annotations
import math
from PyQt5.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QGridLayout, QGroupBox, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

# ── Index definitions ──────────────────────────────────────────────────────────
# (tag, description, unit, data_key, normal_min, normal_max)
# data_key maps to keys in the state dict passed to update_data().
# None means a static/derived value computed locally.

INDEX_DEFINITIONS: list[tuple] = [
    # ── Source (E-1 … E-10) ────────────────────────────────────────────────────
    ('E-1',  'Source Temperature',            '°C',     'temperature',      165.0, 185.0),
    ('E-2',  'Source Pressure',               'bar',    'pressure',           6.0,  10.0),
    ('E-3',  'Source Flow Rate',              'kg/h',   'flow',            2500.0,4500.0),
    ('E-4',  'Source Enthalpy',               'kJ/kg',  'source_enthalpy', 2700.0,2900.0),
    ('E-5',  'Total Heat Duty (all stages)',  'kW',     'total_heat_duty',    0.0,3000.0),
    ('E-6',  'System Efficiency (avg)',       '%',      'avg_efficiency',     20.0,  85.0),
    ('E-7',  'Source System State',           '—',      'state',            None,  None),
    ('E-8',  'Disturbance Active',            'bool',   'disturbance',      None,  None),
    ('E-9',  'Pipeline Length',               'm',      None,                 0.0, 700.0),
    ('E-10', 'Pipe Diameter',                 'in NPS', None,                 0.0,   4.0),

    # ── Main Header Instruments (E-11 … E-20) ──────────────────────────────────
    ('E-11', 'Header Pressure (PT-01)',        'bar',    'pressure',          6.0,  10.0),
    ('E-12', 'Header Temperature (TT-01)',     '°C',     'temperature',     160.0, 185.0),
    ('E-13', 'Header Flow (FT-01)',            'kg/h',   'flow',           2500.0,4500.0),
    ('E-14', 'Header Pressure Drop',           'bar',    None,                0.0,   1.5),
    ('E-15', 'Strainer Differential Pressure', 'bar',    None,                0.0,   0.5),
    ('E-16', 'Rupture Disc Status',            '—',      None,               None,  None),
    ('E-17', 'Steam Trap Status',              '—',      None,               None,  None),
    ('E-18', 'Condensate Flow',                'kg/h',   None,                0.0, 200.0),
    ('E-19', 'Heat Loss Main Header',          'kW',     None,                0.0,  50.0),
    ('E-20', 'Fluid pH',                       '—',      'geo_ph',            5.5,   7.5),

    # ── Cabin Heating – HX-01 (E-21 … E-27) ───────────────────────────────────
    ('E-21', 'Cabin – HX-01 Inlet Temp',       '°C',    'cabin_t_in',       120.0, 175.0),
    ('E-22', 'Cabin – HX-01 Outlet Temp',      '°C',    'cabin_t_out',       28.0,  38.0),
    ('E-23', 'Cabin – Valve Position',         '%',     'cabin_valve',         0.0, 100.0),
    ('E-24', 'Cabin – Heat Duty',              'kW',    'cabin_heat',          0.0, 500.0),
    ('E-25', 'Cabin – Thermal Efficiency',     '%',     'cabin_eff',           0.0, 100.0),
    ('E-26', 'Cabin – Pressure Drop',          'bar',   'cabin_dp',            0.0,   1.0),
    ('E-27', 'Cabin – Sensor Status',          '—',     'cabin_status',      None,  None),

    # ── Hot Pool – HX-02 (E-28 … E-34) ────────────────────────────────────────
    ('E-28', 'Hot Pool – HX-02 Inlet Temp',    '°C',    'hot_pool_t_in',    100.0, 145.0),
    ('E-29', 'Hot Pool – HX-02 Outlet Temp',   '°C',    'hot_pool_t_out',    35.0,  48.0),
    ('E-30', 'Hot Pool – Valve Position',      '%',     'hot_pool_valve',      0.0, 100.0),
    ('E-31', 'Hot Pool – Heat Duty',           'kW',    'hot_pool_heat',       0.0, 600.0),
    ('E-32', 'Hot Pool – Thermal Efficiency',  '%',     'hot_pool_eff',        0.0, 100.0),
    ('E-33', 'Hot Pool – Pressure Drop',       'bar',   'hot_pool_dp',         0.0,   1.0),
    ('E-34', 'Hot Pool – Sensor Status',       '—',     'hot_pool_status',   None,  None),

    # ── Tea Drying – HX-03 (E-35 … E-41) ──────────────────────────────────────
    ('E-35', 'Tea Drying – HX-03 Inlet Temp',  '°C',   'tea_dryer_t_in',    55.0,  80.0),
    ('E-36', 'Tea Drying – HX-03 Outlet Temp', '°C',   'tea_dryer_t_out',   48.0,  65.0),
    ('E-37', 'Tea Drying – Valve Position',    '%',    'tea_dryer_valve',     0.0, 100.0),
    ('E-38', 'Tea Drying – Heat Duty',         'kW',   'tea_dryer_heat',      0.0, 400.0),
    ('E-39', 'Tea Drying – Thermal Efficiency','%',    'tea_dryer_eff',       0.0, 100.0),
    ('E-40', 'Tea Drying – Pressure Drop',     'bar',  'tea_dryer_dp',        0.0,   1.0),
    ('E-41', 'Tea Drying – Sensor Status',     '—',    'tea_dryer_status',  None,  None),

    # ── Food Dehydrator 1 – HX-04 (E-42 … E-48) ───────────────────────────────
    ('E-42', 'Food Dehy – HX-04 Inlet Temp',   '°C',  'food_dehydrator_1_t_in',  42.0, 65.0),
    ('E-43', 'Food Dehy – HX-04 Outlet Temp',  '°C',  'food_dehydrator_1_t_out', 28.0, 50.0),
    ('E-44', 'Food Dehy – Valve Position',     '%',   'food_dehydrator_1_valve',   0.0,100.0),
    ('E-45', 'Food Dehy – Heat Duty',          'kW',  'food_dehydrator_1_heat',    0.0,450.0),
    ('E-46', 'Food Dehy – Thermal Efficiency', '%',   'food_dehydrator_1_eff',     0.0,100.0),
    ('E-47', 'Food Dehy – Pressure Drop',      'bar', 'food_dehydrator_1_dp',      0.0,  1.0),
    ('E-48', 'Food Dehy – Sensor Status',      '—',   'food_dehydrator_1_status', None,None),

    # ── Fish Pond – HX-05 (E-49 … E-55) ───────────────────────────────────────
    ('E-49', 'Fish Pond – HX-05 Inlet Temp',   '°C',  'fish_pond_t_in',    30.0,  52.0),
    ('E-50', 'Fish Pond – HX-05 Outlet Temp',  '°C',  'fish_pond_t_out',   24.0,  32.0),
    ('E-51', 'Fish Pond – Valve Position',     '%',   'fish_pond_valve',     0.0, 100.0),
    ('E-52', 'Fish Pond – Heat Duty',          'kW',  'fish_pond_heat',      0.0, 350.0),
    ('E-53', 'Fish Pond – Thermal Efficiency', '%',   'fish_pond_eff',       0.0, 100.0),
    ('E-54', 'Fish Pond – Pressure Drop',      'bar', 'fish_pond_dp',        0.0,   1.0),
    ('E-55', 'Fish Pond – Sensor Status',      '—',   'fish_pond_status',  None,  None),

    # ── Food Dehydrator 2 – HX-06 (E-56 … E-62) ───────────────────────────────
    ('E-56', 'Food Dehy 2 – HX-06 Inlet Temp', '°C', 'food_dehydrator_2_t_in',  42.0, 65.0),
    ('E-57', 'Food Dehy 2 – HX-06 Outlet Temp','°C', 'food_dehydrator_2_t_out', 28.0, 50.0),
    ('E-58', 'Food Dehy 2 – Valve Position',   '%',  'food_dehydrator_2_valve',   0.0,100.0),
    ('E-59', 'Food Dehy 2 – Heat Duty',        'kW', 'food_dehydrator_2_heat',    0.0,450.0),
    ('E-60', 'Food Dehy 2 – Thermal Efficiency','%', 'food_dehydrator_2_eff',     0.0,100.0),
    ('E-61', 'Food Dehy 2 – Pressure Drop',    'bar','food_dehydrator_2_dp',      0.0,  1.0),
    ('E-62', 'Food Dehy 2 – Sensor Status',    '—',  'food_dehydrator_2_status', None,None),

    # ── Greenhouse – HX-07 (E-63 … E-69) ──────────────────────────────────────
    ('E-63', 'Greenhouse – HX-07 Inlet Temp',  '°C', 'green_house_t_in',   24.0,  32.0),
    ('E-64', 'Greenhouse – HX-07 Outlet Temp', '°C', 'green_house_t_out',  20.0,  28.0),
    ('E-65', 'Greenhouse – Valve Position',    '%',  'green_house_valve',    0.0, 100.0),
    ('E-66', 'Greenhouse – Heat Duty',         'kW', 'green_house_heat',     0.0, 250.0),
    ('E-67', 'Greenhouse – Thermal Efficiency','%',  'green_house_eff',      0.0, 100.0),
    ('E-68', 'Greenhouse – Pressure Drop',     'bar','green_house_dp',       0.0,   1.0),
    ('E-69', 'Greenhouse – Sensor Status',     '—',  'green_house_status', None,  None),

    # ── Geochemistry (E-70 … E-79) ─────────────────────────────────────────────
    ('E-70', 'Fluid pH',                        '—',  'geo_ph',              5.5,   7.5),
    ('E-71', 'TDS (Total Dissolved Solids)',    'mg/L','geo_tds',            800.0,3500.0),
    ('E-72', 'Silica Content',                 'mg/L','geo_silica',           0.0, 600.0),
    ('E-73', 'Scaling Risk Level',             '—',  'geo_silica_risk',     None,  None),
    ('E-74', 'H2S Estimate',                   'ppm','geo_h2s',              0.0,  50.0),
    ('E-75', 'Non-Condensable Gas',            '%',  'geo_ncg',              0.0,   5.0),
    ('E-76', 'Conductivity',                   'µS/cm','geo_cond',           500.0,5000.0),
    ('E-77', 'Chloride Content',               'mg/L','geo_cl',              0.0, 800.0),
    ('E-78', 'Bicarbonate',                    'mg/L','geo_hco3',             0.0, 500.0),
    ('E-79', 'Calcium Hardness',               'mg/L','geo_ca',              0.0, 300.0),

    # ── Calculated / Derived (E-80 … E-100) ────────────────────────────────────
    ('E-80', 'Total Thermal Power Output',     'kW',  'total_heat_duty',     0.0,3000.0),
    ('E-81', 'Cumulative Energy Today',        'MWh', 'cumulative_energy',   0.0, 100.0),
    ('E-82', 'System COP (Coeff. of Performance)','—','system_cop',          1.0,  20.0),
    ('E-83', 'Average Stage Efficiency',       '%',   'avg_efficiency',      0.0, 100.0),
    ('E-84', 'Pipeline Heat Loss (est.)',      'kW',  None,                   0.0, 100.0),
    ('E-85', 'Condensate Recovery Rate',       'kg/h',None,                   0.0, 300.0),
    ('E-86', 'Auto-Control Mode',              '—',   'auto_control',        None,  None),
    ('E-87', 'Valves in Auto-Tune',            '—',   None,                  None,  None),
    ('E-88', 'Highest Valve Position',         '%',   None,                   0.0, 100.0),
    ('E-89', 'Lowest Valve Position',          '%',   None,                   0.0, 100.0),
    ('E-90', 'Stages in Normal State',         '—',   None,                  None,  None),
    ('E-91', 'Stages in Warning State',        '—',   None,                  None,  None),
    ('E-92', 'Stages in Critical State',       '—',   None,                  None,  None),
    ('E-93', 'Peak Heat Duty (session)',        'kW',  None,                   0.0,3000.0),
    ('E-94', 'Min Heat Duty (session)',         'kW',  None,                   0.0,3000.0),
    ('E-95', 'System Uptime',                  'min', None,                   0.0,99999.0),
    ('E-96', 'Total Alarm Events (session)',   '—',   None,                  None,  None),
    ('E-97', 'Last Alarm Description',         '—',   None,                  None,  None),
    ('E-98', 'Active Scheme',                  '—',   'active_scheme',       None,  None),
    ('E-99', 'Simulation Timestamp',           '—',   None,                  None,  None),
    ('E-100','Reserved / Spare',               '—',   None,                  None,  None),
]


# ── Colour helpers ─────────────────────────────────────────────────────────────

def _status_color(value, nmin, nmax) -> str:
    """Return hex colour string based on whether value is in normal range."""
    if nmin is None or nmax is None:
        return '#aaaaaa'
    try:
        v = float(value)
        if nmin <= v <= nmax:
            return '#00e888'
        if v < nmin * 0.85 or v > nmax * 1.15:
            return '#ff4040'
        return '#ffcc00'
    except (TypeError, ValueError):
        return '#aaaaaa'


def _status_label(value, nmin, nmax) -> str:
    if nmin is None or nmax is None:
        return 'Info'
    try:
        v = float(value)
        if nmin <= v <= nmax:
            return 'Normal'
        if v < nmin * 0.85 or v > nmax * 1.15:
            return 'ALARM'
        return 'Warning'
    except (TypeError, ValueError):
        return 'Info'


# ── Row widget ─────────────────────────────────────────────────────────────────

class _IndexRow(QWidget):
    """Single row in the index panel (one parameter entry)."""

    _TAG_W   = 48
    _DESC_W  = 250
    _VAL_W   = 80
    _UNIT_W  = 60
    _STAT_W  = 60

    def __init__(self, tag: str, description: str, unit: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)

        hl = QHBoxLayout()
        hl.setContentsMargins(4, 1, 4, 1)
        hl.setSpacing(4)

        # Tag
        self._tag_lbl = QLabel(tag)
        self._tag_lbl.setFixedWidth(self._TAG_W)
        self._tag_lbl.setFont(QFont('Courier New', 8, QFont.Bold))
        self._tag_lbl.setStyleSheet('color:#5588cc; background:transparent;')

        # Description
        self._desc_lbl = QLabel(description)
        self._desc_lbl.setFixedWidth(self._DESC_W)
        self._desc_lbl.setFont(QFont('Arial', 8))
        self._desc_lbl.setStyleSheet('color:#8899aa; background:transparent;')

        # Value
        self._val_lbl = QLabel('—')
        self._val_lbl.setFixedWidth(self._VAL_W)
        self._val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._val_lbl.setFont(QFont('Courier New', 8, QFont.Bold))
        self._val_lbl.setStyleSheet('color:#00e8ff; background:transparent;')

        # Unit
        self._unit_lbl = QLabel(unit)
        self._unit_lbl.setFixedWidth(self._UNIT_W)
        self._unit_lbl.setFont(QFont('Arial', 7))
        self._unit_lbl.setStyleSheet('color:#445566; background:transparent;')

        # Status badge
        self._stat_lbl = QLabel('—')
        self._stat_lbl.setFixedWidth(self._STAT_W)
        self._stat_lbl.setAlignment(Qt.AlignCenter)
        self._stat_lbl.setFont(QFont('Arial', 7, QFont.Bold))
        self._stat_lbl.setStyleSheet(
            'color:#aaaaaa; background:#1a1a1a; border-radius:3px; padding:0 3px;')

        for w in (self._tag_lbl, self._desc_lbl, self._val_lbl,
                  self._unit_lbl, self._stat_lbl):
            hl.addWidget(w)
        hl.addStretch(1)

        self.setLayout(hl)
        self.setStyleSheet('background: transparent;')

    def update_value(self, value, nmin, nmax) -> None:
        if value is None:
            self._val_lbl.setText('—')
            self._stat_lbl.setText('—')
            return

        # Format the value
        if isinstance(value, bool):
            txt = 'YES' if value else 'NO'
        elif isinstance(value, float):
            txt = f'{value:.2f}' if abs(value) < 1000 else f'{value:.0f}'
        else:
            txt = str(value)

        self._val_lbl.setText(txt)

        col = _status_color(value, nmin, nmax)
        lbl = _status_label(value, nmin, nmax)
        self._val_lbl.setStyleSheet(f'color:{col}; background:transparent; '
                                    f'font-family:"Courier New"; font-size:8pt; font-weight:bold;')
        stat_bg = {'Normal': '#0a1f10', 'Warning': '#1f1800',
                   'ALARM': '#1f0808', 'Info': '#0a0e18'}.get(lbl, '#0a0e18')
        self._stat_lbl.setText(lbl)
        self._stat_lbl.setStyleSheet(
            f'color:{col}; background:{stat_bg}; border-radius:3px; padding:0 3px; '
            f'font-size:7pt; font-weight:bold;')

    def apply_theme(self, theme: dict) -> None:
        tag_color   = theme.get('text_label',  '#5588cc')
        val_color   = theme.get('text_value',  '#00e8ff')
        desc_color  = theme.get('text_label',  '#8899aa')
        self._tag_lbl.setStyleSheet(
            f'color:{tag_color}; background:transparent; '
            f'font-family:"Courier New"; font-size:8pt; font-weight:bold;')
        self._val_lbl.setStyleSheet(
            f'color:{val_color}; background:transparent; '
            f'font-family:"Courier New"; font-size:8pt; font-weight:bold;')
        self._desc_lbl.setStyleSheet(f'color:{desc_color}; background:transparent; font-size:8pt;')


# ── Main IndexPanel ────────────────────────────────────────────────────────────

class IndexPanel(QWidget):
    """
    Scrollable panel showing E-1 … E-100 parameter indices.
    Call  update_data(state_dict)  on every UI tick to refresh values.
    Call  apply_theme(theme_dict)  when the scheme changes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: dict[str, _IndexRow] = {}
        self._peak_heat: float = 0.0
        self._min_heat:  float = 1e9
        self._uptime_s:  float = 0.0
        self._alarm_count: int = 0
        self._cumulative_energy: float = 0.0
        self._last_alarm: str = '—'
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        hdr = QWidget()
        hdr.setFixedHeight(26)
        hdr.setStyleSheet('background:#0a1220; border-bottom:1px solid #1e3a5f;')
        hdr_l = QHBoxLayout()
        hdr_l.setContentsMargins(8, 2, 8, 2)
        hdr_l.setSpacing(4)

        for txt, w in [('Tag', 48), ('Parameter Description', 250),
                       ('Value', 80), ('Unit', 60), ('Status', 60)]:
            lbl = QLabel(txt)
            lbl.setFixedWidth(w)
            lbl.setFont(QFont('Arial', 8, QFont.Bold))
            lbl.setStyleSheet('color:#5577aa; background:transparent;')
            if txt == 'Value':
                lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        hdr.setLayout(hdr_l)
        root.addWidget(hdr)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('background:#0c1018; border:none;')

        inner = QWidget()
        inner.setStyleSheet('background:#0c1018;')
        vbox  = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        for i, (tag, desc, unit, _, nmin, nmax) in enumerate(INDEX_DEFINITIONS):
            row = _IndexRow(tag, desc, unit)
            # Alternating row background
            if i % 2 == 0:
                row.setStyleSheet('background:#0e1520;')
            else:
                row.setStyleSheet('background:#0c1018;')
            self._rows[tag] = row
            vbox.addWidget(row)

        vbox.addStretch(1)
        inner.setLayout(vbox)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        self.setLayout(root)

    # ── Data update ────────────────────────────────────────────────────────────

    def update_data(self, state: dict) -> None:
        """Refresh all rows from the simulator state dict."""
        self._uptime_s += 0.1   # called at ~10 Hz

        # Flatten stage sensor data for easy lookup
        sensors   = state.get('endpoint_sensors', {})
        valves    = state.get('valve_positions', {})
        geochem   = state.get('geochemistry', {})
        heat      = state.get('total_heat_duty_kw', 0.0)
        avg_eff   = 0.0
        if sensors:
            avg_eff = sum(d.get('efficiency', 0) for d in sensors.values()) / len(sensors)

        # Track session extremes
        self._peak_heat = max(self._peak_heat, heat)
        if heat > 0:
            self._min_heat = min(self._min_heat, heat)
        self._cumulative_energy += heat / 3600.0 / 1000.0  # kWh → MWh per tick (0.1s)

        enthalpy = 419.0 + 2.09 * state.get('temperature', 174.0)

        # Build flat lookup for data_key → value
        flat: dict = {
            'temperature':      state.get('temperature', 0.0),
            'pressure':         state.get('pressure', 0.0),
            'flow':             state.get('flow', 0.0),
            'source_enthalpy':  enthalpy,
            'total_heat_duty':  heat,
            'avg_efficiency':   avg_eff,
            'state':            state.get('state', '—'),
            'disturbance':      state.get('disturbance_active', False),
            'auto_control':     state.get('auto_control_enabled', False),
            'active_scheme':    state.get('active_scheme', 'scada'),
            'cumulative_energy': self._cumulative_energy,
            'system_cop':       heat / max(heat * 0.1, 1.0),   # simplistic COP

            # Geochemistry
            'geo_ph':         geochem.get('ph', 0.0),
            'geo_tds':        geochem.get('tds_mg_l', 0.0),
            'geo_silica':     geochem.get('silica_mg_l', 0.0),
            'geo_silica_risk':geochem.get('silica_risk', '—'),
            'geo_h2s':        geochem.get('h2s_ppm', 8.5),
            'geo_ncg':        geochem.get('ncg_pct', 0.8),
            'geo_cond':       geochem.get('conductivity', 2200.0),
            'geo_cl':         geochem.get('chloride', 320.0),
            'geo_hco3':       geochem.get('bicarbonate', 185.0),
            'geo_ca':         geochem.get('calcium', 95.0),
        }

        # Per-stage flatten
        for sid, sdata in sensors.items():
            flat[f'{sid}_t_in']   = sdata.get('inlet_temp', 0.0)
            flat[f'{sid}_t_out']  = sdata.get('outlet_temp', 0.0)
            flat[f'{sid}_valve']  = valves.get(sid, 0.0)
            flat[f'{sid}_heat']   = sdata.get('heat_duty_kw', 0.0)
            flat[f'{sid}_eff']    = sdata.get('efficiency', 0.0)
            flat[f'{sid}_dp']     = sdata.get('pressure_drop', 0.0)
            flat[f'{sid}_status'] = sdata.get('status', '—')

        # Session-derived
        import time as _time
        flat['peak_heat']   = self._peak_heat
        flat['min_heat']    = self._min_heat if self._min_heat < 1e8 else 0.0
        flat['uptime_min']  = self._uptime_s / 60.0
        flat['alarm_count'] = self._alarm_count

        valve_list = list(valves.values())
        flat['max_valve'] = max(valve_list) if valve_list else 0.0
        flat['min_valve'] = min(valve_list) if valve_list else 0.0

        normal_cnt  = sum(1 for d in sensors.values() if d.get('status') == 'Normal')
        warning_cnt = sum(1 for d in sensors.values()
                         if 'Warning' in str(d.get('status', '')))
        critical_cnt = len(sensors) - normal_cnt - warning_cnt

        # Map to static values
        flat['pipeline_length'] = 665.6
        flat['pipe_diameter']   = 2.0

        # Update each row
        for tag, desc, unit, data_key, nmin, nmax in INDEX_DEFINITIONS:
            row = self._rows.get(tag)
            if row is None:
                continue

            value = None
            if data_key == 'pipeline_length':
                value = 665.6
            elif data_key == 'pipe_diameter':
                value = 2.0
            elif tag == 'E-84':
                value = flat.get('flow', 0.0) * 0.002   # ~0.2% heat loss estimate
            elif tag == 'E-85':
                value = flat.get('flow', 0.0) * 0.03
            elif tag == 'E-87':
                value = f"{sum(1 for _ in sensors)} / {len(sensors)}"
            elif tag == 'E-88':
                value = flat.get('max_valve', 0.0)
            elif tag == 'E-89':
                value = flat.get('min_valve', 0.0)
            elif tag == 'E-90':
                value = str(normal_cnt)
            elif tag == 'E-91':
                value = str(warning_cnt)
            elif tag == 'E-92':
                value = str(critical_cnt)
            elif tag == 'E-93':
                value = flat.get('peak_heat', 0.0)
            elif tag == 'E-94':
                value = flat.get('min_heat', 0.0)
            elif tag == 'E-95':
                value = flat.get('uptime_min', 0.0)
            elif tag == 'E-96':
                value = str(flat.get('alarm_count', 0))
            elif tag == 'E-97':
                value = self._last_alarm
            elif tag == 'E-99':
                import datetime
                value = datetime.datetime.now().strftime('%H:%M:%S')
            elif tag == 'E-100':
                value = 'Spare'
            elif tag == 'E-16':
                value = 'OK'
            elif tag == 'E-17':
                value = 'Operational'
            elif data_key and data_key in flat:
                value = flat[data_key]

            row.update_value(value, nmin, nmax)

    def notify_alarm(self, description: str) -> None:
        """Called externally when an alarm event occurs."""
        self._alarm_count += 1
        self._last_alarm = description

    def apply_theme(self, theme: dict) -> None:
        """Update row colours to match the active visual scheme."""
        for row in self._rows.values():
            row.apply_theme(theme)
