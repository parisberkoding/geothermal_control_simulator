"""
Main HMI Window – Geothermal Direct Use SCADA Simulator
PT Geo Dipa Energi (Persero) – Patuha Unit

Layout:
┌────────────────────────────────────────────────────────────────────┐
│  [Scheme Bar]  Full SCADA | Full IoT | Hybrid  +  scheme info      │
│  [HMI Header]  System title, main steam digital readouts, state    │
├──────────────┬─────────────────────────────────────────────────────┤
│  Left Status │  Tab Area                                            │
│  • Gauges    │    Tab 1 – Distribution P&ID                        │
│  • Flow/stat │    Tab 2 – Endpoint P&IDs (detail views)            │
│  • Geochem   │    Tab 3 – Valve Controls                           │
│  • Heat summ │    Tab 4 – Unit Icons (6 distinct visuals)          │
│              │    Tab 5 – Analytics (charts)                        │
│              │    Tab 6 – Index Panel (E-1 … E-100)                │
├──────────────┴─────────────────────────────────────────────────────┤
│  Control Bar – simulation buttons │ auto-control │ event log       │
└────────────────────────────────────────────────────────────────────┘

Supports three visual schemes (selectable via top-bar buttons):
  • Full SCADA  – industrial grey / blue
  • Full IoT    – tech green
  • Hybrid      – mixed

All text / labels are in ENGLISH.
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QTextEdit, QGroupBox, QCheckBox,
    QTabWidget, QScrollArea, QGridLayout, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from ui.pid_display import PIDDisplay

# Tambah ini:
from ui.widgets.endpoint_with_chart import EndpointWithChart
from ui.widgets.gauge import Gauge
from ui.widgets.valve_knob import ValveKnob
from ui.widgets.trend_chart import PressureChart, TemperatureChart, FlowChart, HeatDutyChart
from ui.widgets.index_panel import IndexPanel
from ui.widgets.unit_icon import make_unit_icon
from ui.widgets.heat_exchanger import make_hx_widget
from utils.logger import EventLogger, EventType
from utils.theme_manager import get_theme, get_stylesheet, get_scheme_button_style
from simulation.endpoints import CASCADE_STAGES, UNIT_LIMITS
from simulation.scenarios import get_scenario

# ── English display names for all stages ──────────────────────────────────────

_VALVE_ORDER = [
    ('tea_dryer',         'Tea Drying'),
    ('food_dehydrator_1', 'Food Dehydrator'),
    ('cabin',             'Cabin Heating'),
    ('hot_pool',          'Hot Pool'),
    ('fish_pond',         'Fish Pond'),
    ('green_house',       'Greenhouse'),
]

_ENDPOINT_TABS = [
    ('tea_dryer',         'Tea Drying'),
    ('food_dehydrator_1', 'Food Dehy'),
    ('cabin',             'Cabin'),
    ('hot_pool',          'Hot Pool'),
    ('fish_pond',         'Fish Pond'),
    ('green_house',       'Greenhouse'),
]

# HX tags mapped to stage IDs (cascade order)
_HX_MAP = {
    'tea_dryer':         ('HX-01', 'Tea Drying'),
    'food_dehydrator_1': ('HX-02', 'Food Dehydrator'),
    'cabin':             ('HX-03', 'Cabin Heating'),
    'hot_pool':          ('HX-04', 'Hot Pool'),
    'fish_pond':         ('HX-05', 'Fish Pond'),
    'green_house':       ('HX-06', 'Greenhouse'),
}

_STATUS_COLORS = {
    'EMERGENCY':      '#ff3333',
    'PRESSURE_SPIKE': '#ffcc00',
    'PRESSURE_DROP':  '#6699ff',
    'FLOW_SURGE':     '#ff9900',
    'STABILIZING':    '#ffaa00',
    'NORMAL':         '#00ff96',
}


class MainWindow(QMainWindow):
    """Main HMI application window with three selectable visual schemes."""

    def __init__(self):
        super().__init__()
        self.event_logger    = EventLogger()
        self.simulator       = None
        self._endpoint_views = {}   # sid → endpoint P&ID widget
        self._hx_widgets     = {}   # sid → HeatExchangerWidget
        self._unit_icons     = {}   # sid → unit icon widget
        self._current_scheme = 'scada'

        self._setup_ui()
        self._apply_scheme('scada', initial=True)

        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_ui)
        self._update_timer.start(100)   # 10 Hz

        self.event_logger.log(EventType.INFO, "System started — Normal operation")
        self.event_logger.log(EventType.INFO, "Active scheme: Full SCADA")

    # ── UI construction ────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle(
            "Geothermal Direct Use SCADA — PT Geo Dipa Energi (Persero) – Patuha")
        self.setGeometry(50, 30, 1440, 840)
        self.setMinimumSize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout()
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(3)

        # ── Scheme selector bar (top) ─────────────────
        root.addWidget(self._build_scheme_bar(), stretch=0)

        # ── HMI status header ─────────────────────────
        root.addWidget(self._build_hmi_header(), stretch=0)

        # ── Main area: left panel + tab area ──────────
        top_split = QSplitter(Qt.Horizontal)
        top_split.addWidget(self._build_status_panel())
        top_split.addWidget(self._build_tab_panel())
        top_split.setSizes([235, 1200])
        top_split.setChildrenCollapsible(False)
        root.addWidget(top_split, stretch=10)

        # ── Control bar ───────────────────────────────
        root.addWidget(self._build_control_bar(), stretch=0)

        central.setLayout(root)

    # ── Scheme selector bar ────────────────────────────────────────────────────

    def _build_scheme_bar(self):
        """Top bar with Full SCADA / Full IoT / Hybrid scheme buttons."""
        bar = QWidget()
        bar.setFixedHeight(42)
        bar.setObjectName('scheme_bar')
        bar.setStyleSheet(
            "QWidget#scheme_bar { background:#080c14; border-bottom:1px solid #1e3a5f; }")

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Label
        lbl = QLabel("Architecture Scheme:")
        lbl.setStyleSheet("color:#5577aa; font-size:8pt; font-weight:bold; background:transparent;")
        layout.addWidget(lbl)

        # Three scheme buttons
        self._scheme_btns: dict[str, QPushButton] = {}
        for scheme_id, label_txt in [
            ('scada',  '🏭  Full SCADA'),
            ('iot',    '📡  Full IoT'),
            ('hybrid', '⚙  Hybrid'),
        ]:
            btn = QPushButton(label_txt)
            btn.setFixedHeight(30)
            btn.setMinimumWidth(130)
            btn.clicked.connect(lambda checked, s=scheme_id: self._apply_scheme(s))
            self._scheme_btns[scheme_id] = btn
            layout.addWidget(btn)

        # Scheme info label (right side)
        self._scheme_info_lbl = QLabel('')
        self._scheme_info_lbl.setStyleSheet(
            "color:#556677; font-size:8pt; background:transparent;")
        layout.addWidget(self._scheme_info_lbl, stretch=1)

        # Active indicator
        self._scheme_active_lbl = QLabel('')
        self._scheme_active_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._scheme_active_lbl.setStyleSheet(
            "color:#7ab0e0; font-size:8pt; font-weight:bold; background:transparent;")
        layout.addWidget(self._scheme_active_lbl)

        bar.setLayout(layout)
        return bar

    # ── HMI Header banner ──────────────────────────────────────────────────────

    def _build_hmi_header(self):
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setObjectName('hmi_header')

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(16)

        # Title
        self._hdr_title = QLabel(
            "PT GEO DIPA ENERGI  |  GEOTHERMAL SCADA  |  Direct Use HMI  |  Patuha")
        self._hdr_title.setStyleSheet(
            "color:#7ab0e0; font-size:10pt; font-weight:bold; letter-spacing:1px;")
        layout.addWidget(self._hdr_title)
        layout.addStretch(1)

        # Digital readout helper
        def _readout(label_txt, attr_name, unit, color='#00e8ff'):
            wrapper = QWidget()
            wrapper.setObjectName('readout_box')
            wl = QHBoxLayout()
            wl.setContentsMargins(6, 2, 6, 2)
            wl.setSpacing(4)
            lbl = QLabel(label_txt)
            lbl.setStyleSheet("color:#557799; font-size:7pt; font-weight:bold;")
            val = QLabel('—')
            val.setStyleSheet(
                f"color:{color}; font-size:14pt; font-weight:bold; "
                f"font-family:'Courier New';")
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            u = QLabel(unit)
            u.setStyleSheet("color:#445566; font-size:8pt;")
            wl.addWidget(lbl)
            wl.addWidget(val)
            wl.addWidget(u)
            wrapper.setLayout(wl)
            setattr(self, attr_name, val)
            return wrapper

        layout.addWidget(_readout('PRESS', '_hdr_pressure',    'bar',  '#00e8ff'))
        layout.addWidget(_readout('TEMP',  '_hdr_temperature', '°C',   '#ff9040'))
        layout.addWidget(_readout('FLOW',  '_hdr_flow',        'kg/h', '#40ff90'))
        layout.addWidget(_readout('HEAT',  '_hdr_heat',        'kW',   '#ffd040'))

        # System state pill
        self._hdr_state = QLabel('● NORMAL')
        self._hdr_state.setAlignment(Qt.AlignCenter)
        self._hdr_state.setFixedWidth(185)
        self._hdr_state.setStyleSheet(
            "color:#00ff96; font-size:10pt; font-weight:bold; "
            "background:#0a1e14; border:1px solid #00ff96; border-radius:5px; "
            "padding:4px 8px;")
        layout.addWidget(self._hdr_state)

        bar.setLayout(layout)
        return bar

    # ── Left status panel ──────────────────────────────────────────────────────

    def _build_status_panel(self):
        panel = QWidget()
        panel.setMaximumWidth(240)
        panel.setMinimumWidth(200)

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(5)

        # ── Main Steam ───────────────────────────────
        steam_grp = QGroupBox('Main Steam  (Well DP-6)')
        sg = QVBoxLayout()
        sg.setSpacing(3)

        gauges_row = QHBoxLayout()
        gauges_row.setSpacing(3)

        self.pressure_gauge = Gauge(
            min_value=0, max_value=15,
            unit='bar', label='Pressure',
            warning_threshold=10, critical_threshold=12)
        self.pressure_gauge.set_value(8.0)

        self.temp_gauge = Gauge(
            min_value=150, max_value=200,
            unit='°C', label='Temp')
        self.temp_gauge.set_value(174.0)

        for g in (self.pressure_gauge, self.temp_gauge):
            g.setMinimumSize(86, 86)
            g.setMaximumSize(108, 108)
            g.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            gauges_row.addWidget(g)

        sg.addLayout(gauges_row)

        self._flow_lbl = QLabel('Flow: 3374 kg/h')
        self._flow_lbl.setAlignment(Qt.AlignCenter)
        self._flow_lbl.setStyleSheet(
            'color:#aaeeff; font-size:10pt; font-weight:bold;')
        sg.addWidget(self._flow_lbl)

        self._state_lbl = QLabel('● Normal Operation')
        self._state_lbl.setAlignment(Qt.AlignCenter)
        self._state_lbl.setStyleSheet(
            'color:#00ff96; font-size:9pt; font-weight:bold;')
        sg.addWidget(self._state_lbl)

        steam_grp.setLayout(sg)
        layout.addWidget(steam_grp)

        # ── Geochemistry / Fluid Parameters ──────────
        geo_grp = QGroupBox('Fluid & Geochemistry')
        geo_layout = QGridLayout()
        geo_layout.setSpacing(2)
        geo_layout.setContentsMargins(6, 3, 6, 3)

        lbl_s = 'color:#7799aa; font-size:8pt;'
        val_s = 'color:#ffffff; font-size:8pt; font-weight:bold;'

        params = [
            ('pH',              'ph_val'),
            ('TDS  (mg/L)',     'tds_val'),
            ('Silica Risk',     'silica_val'),
            ('H2S  (ppm)',      'h2s_val'),
            ('NCG  (%)',        'ncg_val'),
            ('Conductivity',    'cond_val'),
            ('Heat  (kW)',      'heat_val'),
            ('Enthalpy',        'enthalpy_val'),
            ('Avg Efficiency',  'efficiency_val'),
        ]
        self._geo_labels: dict = {}
        for row, (name, attr) in enumerate(params):
            nl = QLabel(name + ':')
            nl.setStyleSheet(lbl_s)
            vl = QLabel('—')
            vl.setStyleSheet(val_s)
            geo_layout.addWidget(nl, row, 0)
            geo_layout.addWidget(vl, row, 1)
            self._geo_labels[attr] = vl

        geo_grp.setLayout(geo_layout)
        layout.addWidget(geo_grp)

        # ── Stage heat summary ────────────────────────
        heat_grp = QGroupBox('Stage Heat Summary')
        hg = QVBoxLayout()
        hg.setSpacing(1)
        hg.setContentsMargins(6, 2, 6, 2)

        self._stage_heat_labels: dict = {}
        for sid, name in _VALVE_ORDER:
            row_w = QWidget()
            rl = QHBoxLayout()
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(3)
            nl = QLabel(name[:14])
            nl.setStyleSheet('color:#8899aa; font-size:7pt;')
            nl.setFixedWidth(90)
            vl = QLabel('— kW')
            vl.setStyleSheet('color:#ffaa40; font-size:7pt; font-weight:bold;')
            vl.setAlignment(Qt.AlignRight)
            rl.addWidget(nl)
            rl.addWidget(vl)
            row_w.setLayout(rl)
            hg.addWidget(row_w)
            self._stage_heat_labels[sid] = vl

        heat_grp.setLayout(hg)
        layout.addWidget(heat_grp)

        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    # ── Tab panel ──────────────────────────────────────────────────────────────

    def _build_tab_panel(self):
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_pipeline_tab(),   '🗺  Distribution P&ID')
        self._tabs.addTab(self._build_endpoints_tab(),  '🏭  Endpoint P&IDs')
        self._tabs.addTab(self._build_controls_tab(),   '🔧  Valve Controls')
        self._tabs.addTab(self._build_unit_icons_tab(), '🏠  Unit Views')
        self._tabs.addTab(self._build_analytics_tab(),  '📊  Analytics')
        self._tabs.addTab(self._build_index_tab(),      '📋  Index (E-1…E-100)')
        return self._tabs

    # ── Tab 1 – Distribution P&ID ──────────────────────────────────────────────

    def _build_pipeline_tab(self):
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Legend
        legend = QLabel(
            "Pipe colour:  "
            "<span style='color:#dc3219;'>■</span> Hot (>130°C)  "
            "<span style='color:#dc9019;'>■</span> Warm (60–130°C)  "
            "<span style='color:#19aabe;'>■</span> Cool (<60°C)  "
            "  ▶ Valve (green=open, yellow=partial, red=closed)  "
            "  ● Sensor (green=normal, yellow=warning, red=alarm)")
        legend.setStyleSheet("color:#556677; font-size:8pt;")
        layout.addWidget(legend)

        self.pid_display = PIDDisplay()
        layout.addWidget(self.pid_display)

        container.setLayout(layout)
        return container

    # ── Tab 2 – Endpoint P&IDs ─────────────────────────────────────────────────

    def _build_endpoints_tab(self):
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        lbl = QLabel(
            "Individual endpoint P&IDs with live trend charts.  "
            "Top: process diagram  |  Bottom: real-time analytics  |  Updates every 100 ms.")
        lbl.setStyleSheet("color:#556677; font-size:8pt; padding:2px 0 4px 0;")
        layout.addWidget(lbl)

        sub_tabs = QTabWidget()
        for sid, tab_name in _ENDPOINT_TABS:
            display_name = dict(_VALVE_ORDER).get(sid, tab_name)
            view = EndpointWithChart(sid, display_name)
            self._endpoint_views[sid] = view          # simpan referensi
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(view)
            sub_tabs.addTab(scroll, tab_name)

        layout.addWidget(sub_tabs)
        container.setLayout(layout)
        return container
     # ── Tab 3 – Valve Controls ─────────────────────────────────────────────────

    def _build_controls_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        inner  = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        # Column header
        hdr = QWidget()
        hr  = QHBoxLayout()
        hr.setContentsMargins(0, 0, 0, 0)
        hr.setSpacing(4)
        for txt, w in [('Stage', 140), ('Valve Opening  (range = unit process temp)', 270),
                       ('T-in → T-out', 112), ('Heat kW', 62),
                       ('Eff %', 48), ('ΔP bar', 52),
                       ('Status', 120), ('Auto', 55)]:
            l = QLabel(txt)
            l.setFixedWidth(w)
            l.setStyleSheet('color:#556677; font-size:8pt; font-weight:bold;')
            hr.addWidget(l)
        hr.addStretch()
        hdr.setLayout(hr)
        layout.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:#333; background:#333; max-height:1px;')
        layout.addWidget(sep)

        self.valve_knobs          = {}
        self.valve_auto_tune_cbs  = {}
        self.valve_sensor_labels  = {}
        self._valve_param_labels  = {}

        for sid, display_name in _VALVE_ORDER:
            row_widget = self._build_valve_row(sid, display_name)
            layout.addWidget(row_widget)
            sep2 = QFrame()
            sep2.setFrameShape(QFrame.HLine)
            sep2.setStyleSheet('color:#222; background:#222; max-height:1px;')
            layout.addWidget(sep2)

        layout.addStretch(1)
        inner.setLayout(layout)
        scroll.setWidget(inner)
        return scroll

    def _build_valve_row(self, sid: str, display_name: str):
        row = QWidget()
        row.setFixedHeight(72)
        rl  = QHBoxLayout()
        rl.setContentsMargins(4, 4, 4, 4)
        rl.setSpacing(4)

        # Stage name label
        nl = QLabel(display_name)
        nl.setFixedWidth(138)
        nl.setWordWrap(True)
        nl.setStyleSheet('color:white; font-size:9pt; font-weight:bold;')
        rl.addWidget(nl)

        # Slider with unit temp range
        t_min, t_max = UNIT_LIMITS.get(sid, (20, 100))
        default_pos  = {
            'tea_dryer': 85.0, 'food_dehydrator_1': 80.0,
            'cabin': 75.0, 'hot_pool': 70.0,
            'fish_pond': 65.0, 'green_house': 60.0,
        }.get(sid, 70.0)
        knob = ValveKnob(label='', initial_value=default_pos,
                         temp_range=(t_min, t_max))
        knob.setFixedSize(268, 58)
        knob.valueChanged.connect(lambda v, s=sid: self._on_valve_changed(s, v))
        self.valve_knobs[sid] = knob
        rl.addWidget(knob)

        t_lbl = QLabel('—→—')
        t_lbl.setFixedWidth(110)
        t_lbl.setAlignment(Qt.AlignCenter)
        t_lbl.setStyleSheet('color:#cccccc; font-size:8pt;')

        heat_lbl = QLabel('—')
        heat_lbl.setFixedWidth(60)
        heat_lbl.setAlignment(Qt.AlignCenter)
        heat_lbl.setStyleSheet('color:#ffa040; font-size:8pt;')

        eff_lbl = QLabel('—')
        eff_lbl.setFixedWidth(46)
        eff_lbl.setAlignment(Qt.AlignCenter)
        eff_lbl.setStyleSheet('color:#80c8ff; font-size:8pt;')

        dp_lbl = QLabel('—')
        dp_lbl.setFixedWidth(50)
        dp_lbl.setAlignment(Qt.AlignCenter)
        dp_lbl.setStyleSheet('color:#cccccc; font-size:8pt;')

        sensor_lbl = QLabel('● Normal')
        sensor_lbl.setFixedWidth(118)
        sensor_lbl.setStyleSheet('color:#00ff96; font-size:8pt;')
        self.valve_sensor_labels[sid] = sensor_lbl

        at_cb = QCheckBox('Auto')
        at_cb.setFixedWidth(53)
        at_cb.setChecked(True)
        at_cb.stateChanged.connect(
            lambda st, s=sid: self._on_auto_tune_changed(s, st))
        self.valve_auto_tune_cbs[sid] = at_cb

        for w in [t_lbl, heat_lbl, eff_lbl, dp_lbl, sensor_lbl, at_cb]:
            rl.addWidget(w)
        rl.addStretch()

        self._valve_param_labels[sid] = {
            'temp': t_lbl,
            'heat': heat_lbl,
            'eff':  eff_lbl,
            'dp':   dp_lbl,
        }

        row.setLayout(rl)
        return row

    # ── Tab 4 – Unit Icons (6 distinct visual representations) ─────────────────

    def _build_unit_icons_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        inner  = QWidget()
        grid   = QGridLayout()
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setSpacing(8)

        # Header
        info_lbl = QLabel(
            "Unit Visual Overview — each icon shows the live process state of the direct-use endpoint. "
            "Color border indicates sensor status (green=normal, yellow=warning, red=alarm).")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet('color:#556677; font-size:8pt; padding:2px;')
        grid.addWidget(info_lbl, 0, 0, 1, 4)

        # HX widgets (row 1-2) — 4 columns
        self._hx_widgets = {}
        hx_row = 1
        for col, (sid, (hx_tag, unit_name)) in enumerate(_HX_MAP.items()):
            hx = make_hx_widget(hx_tag, unit_name)
            hx.setMinimumHeight(160)
            self._hx_widgets[sid] = hx
            r = hx_row + col // 4
            c = col % 4
            grid.addWidget(hx, r, c)

        # Unit icon widgets (row 3-4)
        icon_header = QLabel("Direct Use Unit Visual Representations")
        icon_header.setStyleSheet(
            'color:#7799aa; font-size:9pt; font-weight:bold; '
            'padding:4px 0 2px 0;')
        grid.addWidget(icon_header, 3, 0, 1, 4)

        self._unit_icons = {}
        icon_row = 4
        for col, (sid, _) in enumerate(_VALVE_ORDER):
            icon = make_unit_icon(sid)
            icon.setMinimumHeight(200)
            self._unit_icons[sid] = icon
            r = icon_row + col // 4
            c = col % 4
            grid.addWidget(icon, r, c)

        for col in range(4):
            grid.setColumnStretch(col, 1)

        inner.setLayout(grid)
        scroll.setWidget(inner)
        return scroll

    # ── Tab 5 – Analytics ──────────────────────────────────────────────────────
    def _build_analytics_tab(self):
        """Tab 5: Analytics — system level only (per-unit sudah di Endpoint tab)."""
        container = QWidget()
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(4)

        info = QLabel(
            "System-level analytics.  "
            "Per-unit trend charts are available in the  🏭 Endpoint P&IDs  tab.")
        info.setStyleSheet("color:#556677; font-size:8pt; padding:2px;")
        root_layout.addWidget(info)

        sys_grp = QGroupBox("System Overview")
        sys_grid = QGridLayout()
        sys_grid.setContentsMargins(4, 4, 4, 4)
        sys_grid.setSpacing(6)

        self.pressure_chart  = PressureChart()
        self.temp_chart      = TemperatureChart()
        self.flow_chart      = FlowChart()
        self.heat_duty_chart = HeatDutyChart()

        for chart, title, row, col in [
            (self.pressure_chart,  "Source Pressure (bar)",     0, 0),
            (self.temp_chart,      "Source Temperature (degC)",  0, 1),
            (self.flow_chart,      "Source Flow (kg/h)",         1, 0),
            (self.heat_duty_chart, "Total Heat Duty (kW)",       1, 1),
        ]:
            w = QWidget()
            wl = QVBoxLayout()
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(2)
            tl = QLabel(title)
            tl.setStyleSheet(
                "color:#6688aa; font-size:8pt; font-weight:bold; padding:1px 4px;")
            chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            wl.addWidget(tl)
            wl.addWidget(chart)
            w.setLayout(wl)
            sys_grid.addWidget(w, row, col)
            sys_grid.setRowStretch(row, 1)
            sys_grid.setColumnStretch(col, 1)

        sys_grp.setLayout(sys_grid)
        root_layout.addWidget(sys_grp, stretch=1)

        container.setLayout(root_layout)
        return container

    # ── Tab 6 – Index Panel ────────────────────────────────────────────────────

    def _build_index_tab(self):
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(28)
        hdr.setStyleSheet('background:#080c14; border-bottom:1px solid #1e3a5f;')
        hl = QHBoxLayout()
        hl.setContentsMargins(8, 2, 8, 2)
        hl.setSpacing(0)
        info = QLabel(
            "Parameter Index E-1 … E-100  —  Real-time values, status, and unit for all "
            "monitored points in the geothermal direct-use system.")
        info.setStyleSheet('color:#4466aa; font-size:8pt;')
        hl.addWidget(info)
        hdr.setLayout(hl)
        layout.addWidget(hdr)

        self._index_panel = IndexPanel()
        layout.addWidget(self._index_panel, stretch=1)

        container.setLayout(layout)
        return container

    # ── Control bar ────────────────────────────────────────────────────────────

    def _build_control_bar(self):
        bar = QGroupBox('Control Dashboard')
        bar.setMaximumHeight(118)

        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 4, 8, 4)

        # Simulation scenario buttons (2 rows)
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(3)

        row1 = QHBoxLayout()
        self.btn_normal    = self._btn('Normal Run',      '#1e3a1e')
        self.btn_spike     = self._btn('Force Spike',     '#4a2e00')
        self.btn_drop      = self._btn('Force Drop',      '#00254a')
        row1.addWidget(self.btn_normal)
        row1.addWidget(self.btn_spike)
        row1.addWidget(self.btn_drop)

        row2 = QHBoxLayout()
        self.btn_emergency = self._btn('⚠ EMERGENCY STOP', '#6a0014')
        self.btn_reset     = self._btn('Reset All',         '#003d30')
        row2.addWidget(self.btn_emergency)
        row2.addWidget(self.btn_reset)

        btn_layout.addLayout(row1)
        btn_layout.addLayout(row2)

        self.btn_normal.clicked.connect(self._on_normal_clicked)
        self.btn_spike.clicked.connect(self._on_spike_clicked)
        self.btn_drop.clicked.connect(self._on_drop_clicked)
        self.btn_emergency.clicked.connect(self._on_emergency_clicked)
        self.btn_reset.clicked.connect(self._on_reset_clicked)

        layout.addLayout(btn_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet('background:#333; max-width:1px;')
        layout.addWidget(sep)

        # Auto-control checkbox
        self.auto_ctrl_cb = QCheckBox('Auto Control  ON')
        self.auto_ctrl_cb.setChecked(True)
        self.auto_ctrl_cb.setStyleSheet(
            'color:white; font-size:10pt; font-weight:bold;')
        self.auto_ctrl_cb.stateChanged.connect(self._on_auto_control_changed)
        layout.addWidget(self.auto_ctrl_cb, alignment=Qt.AlignVCenter)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet('background:#333; max-width:1px;')
        layout.addWidget(sep2)

        # Event log
        log_layout = QVBoxLayout()
        log_layout.setSpacing(2)
        log_lbl = QLabel('Event Log:')
        log_lbl.setStyleSheet('color:white; font-size:9pt; font-weight:bold;')
        log_layout.addWidget(log_lbl)

        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(72)
        log_layout.addWidget(self.event_log)

        layout.addLayout(log_layout, stretch=2)
        bar.setLayout(layout)
        return bar

    @staticmethod
    def _btn(text, bg='#2a2a2a'):
        b = QPushButton(text)
        b.setStyleSheet(
            f"QPushButton {{ background:{bg}; color:white; border:1px solid #444; "
            f"border-radius:3px; padding:5px 8px; font-size:9pt; font-weight:bold; }}"
            "QPushButton:hover { background:#4a4a4a; }"
            "QPushButton:pressed { background:#1a1a1a; }")
        return b

    # ── Scheme application ─────────────────────────────────────────────────────

    def _apply_scheme(self, scheme_id: str, initial: bool = False) -> None:
        """Switch the visual theme and update scheme-dependent UI elements."""
        self._current_scheme = scheme_id
        theme    = get_theme(scheme_id)
        scenario = get_scenario(scheme_id)

        # Apply global stylesheet
        self.setStyleSheet(get_stylesheet(scheme_id))

        # Update scheme selector buttons
        for sid, btn in self._scheme_btns.items():
            btn.setStyleSheet(get_scheme_button_style(sid, is_active=(sid == scheme_id)))

        # Scheme info text
        self._scheme_info_lbl.setText(
            f"{theme['scheme_icon']}  {scenario['description']}")
        self._scheme_active_lbl.setText(
            f"Active: {theme['name']}  |  Comm: {scenario['comm_protocol']}")

        # Header style
        hdr_bg = theme['bg_header']
        self._hdr_title.setStyleSheet(
            f"color:{theme['text_primary']}; font-size:10pt; "
            f"font-weight:bold; letter-spacing:1px;")

        # Update index panel theme
        if hasattr(self, '_index_panel'):
            self._index_panel.apply_theme(theme)

        # Update HX widgets and unit icons theme
        for hx in self._hx_widgets.values():
            hx.apply_theme(theme)
        for icon in self._unit_icons.values():
            icon.apply_theme(theme)

        # Log event (skip on initial build to avoid duplicates)
        if not initial:
            self.event_logger.log(
                EventType.INFO,
                f"Scheme changed → {theme['name']}  "
                f"({scenario['comm_protocol']})")

    # ── Simulator link ─────────────────────────────────────────────────────────

    def set_simulator(self, simulator) -> None:
        self.simulator = simulator

    # ── Update loop ────────────────────────────────────────────────────────────

    def _update_ui(self) -> None:
        if not self.simulator:
            return
        state = self.simulator.get_state()

        # Inject active scheme into state for index panel
        state['active_scheme'] = self._current_scheme

        # ── HMI header ──────────────────────────────
        self._hdr_pressure.setText(f"{state['pressure']:.2f}")
        self._hdr_temperature.setText(f"{state['temperature']:.1f}")
        self._hdr_flow.setText(f"{state['flow']:.0f}")
        heat_kw = state.get('total_heat_duty_kw', 0.0)
        self._hdr_heat.setText(f"{heat_kw:.0f}")

        txt, color = self._state_display(state)
        self._hdr_state.setText(txt)
        self._hdr_state.setStyleSheet(
            f"color:{color}; font-size:10pt; font-weight:bold; "
            f"background:#0a1e14; border:2px solid {color}; "
            f"border-radius:5px; padding:3px 8px;")

        # ── Status panel ────────────────────────────
        self.pressure_gauge.set_value(state['pressure'])
        self.temp_gauge.set_value(state['temperature'])
        self._flow_lbl.setText(f"Flow: {state['flow']:.0f} kg/h")
        self._state_lbl.setText(txt)
        self._state_lbl.setStyleSheet(
            f"color:{color}; font-size:9pt; font-weight:bold;")

        # Geochemistry
        geo = state.get('geochemistry', {})
        silica_risk  = geo.get('silica_risk', '—')
        silica_color = {'High': '#ff6060', 'Medium': '#ffcc00',
                        'Low': '#00ff96'}.get(silica_risk, '#aaa')
        self._geo_labels['ph_val'].setText(f"{geo.get('ph', 0):.2f}")
        self._geo_labels['tds_val'].setText(f"{geo.get('tds_mg_l', 0):.0f}")
        sl = self._geo_labels['silica_val']
        sl.setText(silica_risk)
        sl.setStyleSheet(
            f"color:{silica_color}; font-size:8pt; font-weight:bold;")
        self._geo_labels['h2s_val'].setText('8.5')
        self._geo_labels['ncg_val'].setText('0.8')
        self._geo_labels['cond_val'].setText('2200')
        self._geo_labels['heat_val'].setText(f"{heat_kw:.0f}")
        enthalpy = 419 + 2.09 * state['temperature']
        self._geo_labels['enthalpy_val'].setText(f"{enthalpy:.0f} kJ/kg")

        sensors = state.get('endpoint_sensors', {})
        if sensors:
            avg_eff = (sum(d.get('efficiency', 0) for d in sensors.values())
                       / len(sensors))
            self._geo_labels['efficiency_val'].setText(f"{avg_eff:.1f} %")

        # ── Charts ──────────────────────────────────
        self.pressure_chart.add_data_point(state['pressure'])
        self.temp_chart.add_data_point(state['temperature'])
        self.flow_chart.add_data_point(state['flow'])
        self.heat_duty_chart.add_data_point(heat_kw)

        # ── Per-stage widgets ────────────────────────
        valve_positions = state['valve_positions']
        for sid, data in sensors.items():
            pos = valve_positions.get(sid, 0.0)

            # Distribution P&ID
            self.pid_display.update_valve_position(sid, pos)
            self.pid_display.update_sensor_status(sid, data['color'])

            # Slider sync (position + live process temperature)
            if sid in self.valve_knobs:
                self.valve_knobs[sid].set_value(pos)
                proc_temp = data.get('process_outlet', data.get('outlet_temp', 0.0))
                self.valve_knobs[sid].set_process_temp(proc_temp)

            # Valve row labels
            if sid in self._valve_param_labels:
                pl = self._valve_param_labels[sid]
                pl['temp'].setText(
                    f"{data['inlet_temp']:.0f}→{data['outlet_temp']:.0f}")
                pl['heat'].setText(f"{data['heat_duty_kw']:.0f}")
                pl['eff'].setText(f"{data['efficiency']:.1f}")
                pl['dp'].setText(f"{data['pressure_drop']:.3f}")

            # Sensor status badge
            if sid in self.valve_sensor_labels:
                rgb   = data['color']
                hex_c = "#{:02x}{:02x}{:02x}".format(*[int(v) for v in rgb])
                self.valve_sensor_labels[sid].setText(f"● {data['status']}")
                self.valve_sensor_labels[sid].setStyleSheet(
                    f"color:{hex_c}; font-size:8pt;")

            # Stage heat summary
            if sid in self._stage_heat_labels:
                self._stage_heat_labels[sid].setText(
                    f"{data['heat_duty_kw']:.0f} kW")

            # Endpoint P&ID views
            if sid in self._endpoint_views:
                ep_data = dict(data)
                ep_data['valve_pos'] = pos
                self._endpoint_views[sid].update_data(ep_data, valve_pos=pos)

            # HX widgets
            if sid in self._hx_widgets:
                self._hx_widgets[sid].update_data(
                    data, pos, self._current_scheme)

            # Unit icon widgets
            if sid in self._unit_icons:
                self._unit_icons[sid].update_data(
                    data, pos, self._current_scheme)

        # Distribution P&ID pipe colours
        self.pid_display.update_stage_temps(sensors)

        # ── Index panel ─────────────────────────────
        self._index_panel.update_data(state)

        # ── Event log ───────────────────────────────
        events = self.event_logger.get_recent_events(30)
        self.event_log.setPlainText("\n".join(events))
        sb = self.event_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    @staticmethod
    def _state_display(state):
        s = state['state']
        p = state['pressure']
        if s == 'EMERGENCY':
            return "⚠ EMERGENCY SHUTDOWN", "#ff3333"
        if s in ('PRESSURE_SPIKE', 'PRESSURE_DROP', 'FLOW_SURGE'):
            return f"⚠ {s.replace('_', ' ')}", "#ffcc00"
        if s == 'STABILIZING':
            return "⟳ Stabilizing…", "#ffaa00"
        if p > 10:
            return "⚠ High Pressure!", "#ffcc00"
        if p < 6:
            return "⚠ Low Pressure!", "#6699ff"
        return "● NORMAL", "#00ff96"

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _on_valve_changed(self, sid: str, value: float) -> None:
        if not self.simulator:
            return
        vc = self.simulator.valve_controller
        if not vc.auto_control_enabled or not vc.get_valve_auto_tune(sid):
            vc.set_valve_position(sid, value)
            name = dict(_VALVE_ORDER).get(sid, sid)
            self.event_logger.log(EventType.CONTROL,
                                  f"Manual: {name} → {value:.0f}%")

    def _on_auto_tune_changed(self, sid: str, state) -> None:
        if self.simulator:
            enabled = (state == Qt.Checked)
            self.simulator.valve_controller.set_valve_auto_tune(sid, enabled)
            name = dict(_VALVE_ORDER).get(sid, sid)
            self.event_logger.log(
                EventType.CONTROL,
                f"{name} auto-tune {'ON' if enabled else 'OFF'}")

    def _on_normal_clicked(self) -> None:
        if self.simulator:
            self.simulator.reset()
            self.event_logger.log(EventType.INFO, "Reset to normal operation")

    def _on_spike_clicked(self) -> None:
        if self.simulator:
            self.simulator.steam_source._trigger_spike()
            self.event_logger.log(EventType.WARNING,
                                  "Manual trigger: Pressure spike")

    def _on_drop_clicked(self) -> None:
        if self.simulator:
            self.simulator.steam_source._trigger_drop()
            self.event_logger.log(EventType.WARNING,
                                  "Manual trigger: Pressure drop")

    def _on_emergency_clicked(self) -> None:
        if self.simulator:
            self.simulator.emergency_shutdown()
            self.event_logger.log(EventType.CRITICAL,
                                  "EMERGENCY SHUTDOWN ACTIVATED")
            if hasattr(self, '_index_panel'):
                self._index_panel.notify_alarm("Emergency shutdown activated")

    def _on_reset_clicked(self) -> None:
        if self.simulator:
            self.simulator.reset()
            self.event_logger.log(
                EventType.INFO, "System reset — All parameters normalised")
            for chart in [self.pressure_chart, self.temp_chart,
                          self.flow_chart, self.heat_duty_chart]:
                chart.clear_data()

    def _on_auto_control_changed(self, state) -> None:
        if self.simulator:
            enabled = (state == Qt.Checked)
            self.simulator.valve_controller.auto_control_enabled = enabled
            self.auto_ctrl_cb.setText(
                f"Auto Control  {'ON' if enabled else 'OFF'}")
            self.event_logger.log(
                EventType.CONTROL,
                f"Auto-control {'enabled' if enabled else 'disabled'}")
