"""
Main HMI Window – Geothermal Direct Use SCADA Simulator
PT Geo Dipa Energy (Persero)

Layout:
┌──────────────────────────────────────────────────────────────┐
│  HMI Header – system state banner, main steam digital readouts│
├──────────────────┬───────────────────────────────────────────┤
│  Left Status     │  Tab Area                                  │
│  • Main gauges   │    🗺  Distribution P&ID                   │
│  • Flow/state    │    🏭  Endpoint P&IDs (detail views)        │
│  • Fluid params  │    🔧  Valve Controls                       │
│                  │    📊  Analytics (2×2 charts)               │
├──────────────────┴───────────────────────────────────────────┤
│  Control Bar – scenarios, emergency stop, event log           │
└──────────────────────────────────────────────────────────────┘
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QTextEdit, QGroupBox, QCheckBox,
    QTabWidget, QScrollArea, QGridLayout, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from ui.pid_display import PIDDisplay
from ui.endpoint_views import make_endpoint_view
from ui.widgets.gauge import Gauge
from ui.widgets.valve_knob import ValveKnob
from ui.widgets.trend_chart import PressureChart, TemperatureChart, FlowChart, HeatDutyChart
from utils.logger import EventLogger, EventType
from simulation.endpoints import CASCADE_STAGES

# ── shared style helpers ───────────────────────────────────────────────────────

_GROUP_STYLE = """
    QGroupBox {
        color: white; font-size: 9pt; font-weight: bold;
        border: 2px solid #444; border-radius: 5px;
        margin-top: 10px; padding-top: 8px;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
"""

_BTN_BASE = """
    QPushButton {
        background:#3a3a3a; color:white; border:1px solid #555;
        border-radius:3px; padding:5px 8px;
        font-size:9pt; font-weight:bold;
    }
    QPushButton:hover  { background:#4a4a4a; border-color:#777; }
    QPushButton:pressed{ background:#2a2a2a; }
"""

_TAB_STYLE = """
    QTabWidget::pane { border: 2px solid #444; border-radius:3px; }
    QTabBar::tab {
        background:#222; color:#999; padding:6px 12px;
        font-size:9pt; font-weight:bold; border-radius:3px 3px 0 0;
        min-width: 80px;
    }
    QTabBar::tab:selected { background:#2e4055; color:white; }
    QTabBar::tab:hover    { background:#333; }
"""

_STATUS_COLORS = {
    'EMERGENCY':       '#ff3333',
    'PRESSURE_SPIKE':  '#ffcc00',
    'PRESSURE_DROP':   '#6699ff',
    'FLOW_SURGE':      '#ff9900',
    'STABILIZING':     '#ffaa00',
    'NORMAL':          '#00ff96',
}

# Endpoint order + display names for tabs
_ENDPOINT_TABS = [
    ('cabin',             'Cabin'),
    ('hot_pool',          'Kolam Air Panas'),
    ('tea_dryer',         'Pengering Teh'),
    ('food_dehydrator_1', 'Food Dehy 1'),
    ('fish_pond',         'Fish Pond'),
    ('food_dehydrator_2', 'Food Dehy 2'),
    ('green_house',       'Green House'),
]


class MainWindow(QMainWindow):
    """Main HMI application window."""

    _VALVE_ORDER = [
        ('cabin',             'Cabin Warmer'),
        ('hot_pool',          'Kolam Rendam'),
        ('tea_dryer',         'Pengering Teh'),
        ('food_dehydrator_1', 'Food Dehydrator 1'),
        ('fish_pond',         'Fish Pond'),
        ('food_dehydrator_2', 'Food Dehydrator 2'),
        ('green_house',       'Green House'),
    ]

    def __init__(self):
        super().__init__()
        self.event_logger = EventLogger()
        self.simulator    = None
        self._endpoint_views = {}   # sid → endpoint P&ID widget

        self._setup_ui()

        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_ui)
        self._update_timer.start(100)   # 10 Hz

        self.event_logger.log(EventType.INFO, "System started — Normal operation")

    # ── UI construction ────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle(
            "Geothermal Direct Use SCADA — PT Geo Dipa Energy (Persero)")
        self.setGeometry(50, 30, 1400, 800)
        self.setMinimumSize(1100, 680)

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout()
        root.setContentsMargins(5, 5, 5, 5)
        root.setSpacing(4)

        # ── HMI status header (top banner) ──────────
        root.addWidget(self._build_hmi_header(), stretch=0)

        # ── Main area: status panel + tabs ──────────
        top_split = QSplitter(Qt.Horizontal)
        top_split.addWidget(self._build_status_panel())
        top_split.addWidget(self._build_tab_panel())
        top_split.setSizes([230, 1170])
        top_split.setChildrenCollapsible(False)
        root.addWidget(top_split, stretch=10)

        # ── Control bar ─────────────────────────────
        root.addWidget(self._build_control_bar(), stretch=0)

        central.setLayout(root)

    # ── HMI Header banner ──────────────────────────────────────────────────────

    def _build_hmi_header(self):
        """Top banner: system title, main steam digital readouts, alarm state."""
        bar = QWidget()
        bar.setFixedHeight(58)
        bar.setStyleSheet("background:#0d1628; border-bottom:2px solid #1e3a5f;")

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(18)

        # Company / system title
        title = QLabel("PT GEO DIPA ENERGY  |  GEOTHERMAL SCADA  |  Direct Use HMI")
        title.setStyleSheet(
            "color:#7ab0e0; font-size:10pt; font-weight:bold; "
            "letter-spacing: 1px;")
        layout.addWidget(title)

        layout.addStretch(1)

        # Digital readout helpers
        def _readout(label_txt, attr_name, unit, color="#00e8ff"):
            wrapper = QWidget()
            wrapper.setStyleSheet(
                "background:#0a1220; border:1px solid #1e3a5f; border-radius:4px;")
            wl = QHBoxLayout()
            wl.setContentsMargins(6, 2, 6, 2)
            wl.setSpacing(4)
            lbl = QLabel(label_txt)
            lbl.setStyleSheet("color:#668; font-size:7pt; font-weight:bold;")
            val = QLabel("—")
            val.setStyleSheet(
                f"color:{color}; font-size:14pt; font-weight:bold; "
                f"font-family:'Courier New';")
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            u = QLabel(unit)
            u.setStyleSheet("color:#556; font-size:8pt;")
            wl.addWidget(lbl)
            wl.addWidget(val)
            wl.addWidget(u)
            wrapper.setLayout(wl)
            setattr(self, attr_name, val)
            return wrapper

        layout.addWidget(_readout("PRESS", "_hdr_pressure", "bar", "#00e8ff"))
        layout.addWidget(_readout("TEMP", "_hdr_temperature", "°C", "#ff9040"))
        layout.addWidget(_readout("FLOW", "_hdr_flow", "kg/h", "#40ff90"))
        layout.addWidget(_readout("HEAT", "_hdr_heat", "kW", "#ffd040"))

        # System state pill
        self._hdr_state = QLabel("● NORMAL")
        self._hdr_state.setAlignment(Qt.AlignCenter)
        self._hdr_state.setFixedWidth(180)
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
        panel.setMaximumWidth(238)
        panel.setMinimumWidth(200)

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # ── Main Steam group ────────────────────────
        steam_grp = QGroupBox("Main Steam  (Well DP-6)")
        steam_grp.setStyleSheet(_GROUP_STYLE)
        sg = QVBoxLayout()
        sg.setSpacing(4)

        gauges_row = QHBoxLayout()
        gauges_row.setSpacing(4)

        self.pressure_gauge = Gauge(
            min_value=0, max_value=15,
            unit="bar", label="Pressure",
            warning_threshold=10, critical_threshold=12)
        self.pressure_gauge.set_value(8.0)

        self.temp_gauge = Gauge(
            min_value=150, max_value=200,
            unit="°C", label="Temp")
        self.temp_gauge.set_value(174.0)

        for g in (self.pressure_gauge, self.temp_gauge):
            g.setMinimumSize(88, 88)
            g.setMaximumSize(110, 110)
            g.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            gauges_row.addWidget(g)

        sg.addLayout(gauges_row)

        self._flow_lbl = QLabel("Flow: 3374 kg/h")
        self._flow_lbl.setAlignment(Qt.AlignCenter)
        self._flow_lbl.setStyleSheet(
            "color:#aef; font-size:10pt; font-weight:bold;")
        sg.addWidget(self._flow_lbl)

        self._state_lbl = QLabel("● Normal Operation")
        self._state_lbl.setAlignment(Qt.AlignCenter)
        self._state_lbl.setStyleSheet(
            "color:#00ff96; font-size:9pt; font-weight:bold;")
        sg.addWidget(self._state_lbl)

        steam_grp.setLayout(sg)
        layout.addWidget(steam_grp)

        # ── Fluid Parameters group ───────────────────
        geo_grp = QGroupBox("Fluid Parameters")
        geo_grp.setStyleSheet(_GROUP_STYLE)
        geo_layout = QGridLayout()
        geo_layout.setSpacing(3)
        geo_layout.setContentsMargins(6, 4, 6, 4)

        lbl_s = "color:#aaa; font-size:8pt;"
        val_s = "color:#fff; font-size:8pt; font-weight:bold;"

        params = [
            ("pH",           "ph_val"),
            ("TDS (mg/L)",   "tds_val"),
            ("Silica Risk",  "silica_val"),
            ("Heat (kW)",    "heat_val"),
            ("Enthalpy",     "enthalpy_val"),
            ("Efficiency",   "efficiency_val"),
        ]
        self._geo_labels = {}
        for row, (name, attr) in enumerate(params):
            nl = QLabel(name + ":")
            nl.setStyleSheet(lbl_s)
            vl = QLabel("—")
            vl.setStyleSheet(val_s)
            geo_layout.addWidget(nl, row, 0)
            geo_layout.addWidget(vl, row, 1)
            self._geo_labels[attr] = vl

        geo_grp.setLayout(geo_layout)
        layout.addWidget(geo_grp)

        # ── Total heat summary ───────────────────────
        heat_grp = QGroupBox("Stage Heat Summary")
        heat_grp.setStyleSheet(_GROUP_STYLE)
        hg = QVBoxLayout()
        hg.setSpacing(2)
        hg.setContentsMargins(6, 2, 6, 2)

        self._stage_heat_labels = {}
        for sid, name in self._VALVE_ORDER:
            row_w = QWidget()
            rl = QHBoxLayout()
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(4)
            nl = QLabel(name[:12])
            nl.setStyleSheet("color:#aaa; font-size:7pt;")
            nl.setFixedWidth(84)
            vl = QLabel("— kW")
            vl.setStyleSheet("color:#ffa040; font-size:7pt; font-weight:bold;")
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
        self._tabs.setStyleSheet(_TAB_STYLE)
        self._tabs.addTab(self._build_pipeline_tab(),   "🗺  Distribution P&ID")
        self._tabs.addTab(self._build_endpoints_tab(),  "🏭  Endpoint P&IDs")
        self._tabs.addTab(self._build_controls_tab(),   "🔧  Valve Controls")
        self._tabs.addTab(self._build_analytics_tab(),  "📊  Analytics")
        return self._tabs

    # ── Pipeline (Distribution P&ID) tab ──────────────────────────────────────

    def _build_pipeline_tab(self):
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        legend = QLabel(
            "Pipe colour:  "
            "<span style='color:#dc3219;'>■</span> Hot (>130°C)  "
            "<span style='color:#dc9019;'>■</span> Warm (60–130°C)  "
            "<span style='color:#19aabe;'>■</span> Cool (<60°C)  "
            "  ▶ Valve (green=open, yellow=partial, red=closed)  "
            "  ● Sensor (green=normal, yellow=warning, red=alarm)"
        )
        legend.setStyleSheet("color:#777; font-size:8pt;")
        layout.addWidget(legend)

        self.pid_display = PIDDisplay()
        layout.addWidget(self.pid_display)

        container.setLayout(layout)
        return container

    # ── Endpoint P&IDs tab ─────────────────────────────────────────────────────

    def _build_endpoints_tab(self):
        """Tab with sub-tabs for each endpoint's individual P&ID."""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        lbl = QLabel(
            "Individual endpoint P&IDs — based on actual process drawings.  "
            "Live data updates every 100 ms.")
        lbl.setStyleSheet("color:#666; font-size:8pt; padding:2px 0 4px 0;")
        layout.addWidget(lbl)

        sub_tabs = QTabWidget()
        sub_tabs.setStyleSheet("""
            QTabWidget::pane { border:1px solid #333; }
            QTabBar::tab {
                background:#1a1a1a; color:#888; padding:4px 10px;
                font-size:8pt; border-radius:3px 3px 0 0; min-width:70px;
            }
            QTabBar::tab:selected { background:#253545; color:white; }
            QTabBar::tab:hover    { background:#252525; }
        """)

        for sid, tab_name in _ENDPOINT_TABS:
            view = make_endpoint_view(sid)
            self._endpoint_views[sid] = view
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("background:#0c101a; border:none;")
            scroll.setWidget(view)
            sub_tabs.addTab(scroll, tab_name)

        layout.addWidget(sub_tabs)
        container.setLayout(layout)
        return container

    # ── Valve controls tab ─────────────────────────────────────────────────────

    def _build_controls_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:#131820; border:none;")

        inner  = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Column header
        hdr = QWidget()
        hr  = QHBoxLayout()
        hr.setContentsMargins(0, 0, 0, 0)
        hr.setSpacing(4)
        for txt, w in [("Valve", 72), ("Stage", 135), ("Pos", 46),
                       ("T-in→T-out", 108), ("Heat kW", 62),
                       ("Eff %", 48), ("ΔP bar", 52),
                       ("Status", 115), ("Auto", 55)]:
            l = QLabel(txt)
            l.setFixedWidth(w)
            l.setStyleSheet("color:#666; font-size:8pt; font-weight:bold;")
            hr.addWidget(l)
        hr.addStretch()
        hdr.setLayout(hr)
        layout.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#444; background:#444; max-height:1px;")
        layout.addWidget(sep)

        self.valve_knobs         = {}
        self.valve_auto_tune_cbs = {}
        self.valve_sensor_labels = {}
        self._valve_param_labels = {}

        for sid, display_name in self._VALVE_ORDER:
            row_widget = self._build_valve_row(sid, display_name)
            layout.addWidget(row_widget)
            sep2 = QFrame()
            sep2.setFrameShape(QFrame.HLine)
            sep2.setStyleSheet("color:#222; background:#222; max-height:1px;")
            layout.addWidget(sep2)

        layout.addStretch(1)
        inner.setLayout(layout)
        scroll.setWidget(inner)
        return scroll

    def _build_valve_row(self, sid: str, display_name: str):
        row = QWidget()
        row.setFixedHeight(84)
        rl  = QHBoxLayout()
        rl.setContentsMargins(4, 3, 4, 3)
        rl.setSpacing(4)

        # Knob
        knob = ValveKnob(label="", initial_value=70.0)
        knob.setFixedSize(72, 72)
        knob.valueChanged.connect(lambda v, s=sid: self._on_valve_changed(s, v))
        self.valve_knobs[sid] = knob
        rl.addWidget(knob)

        # Stage name
        nl = QLabel(display_name)
        nl.setFixedWidth(133)
        nl.setWordWrap(True)
        nl.setStyleSheet("color:white; font-size:9pt; font-weight:bold;")
        rl.addWidget(nl)

        # Position label
        pos_lbl = QLabel("70%")
        pos_lbl.setFixedWidth(44)
        pos_lbl.setAlignment(Qt.AlignCenter)
        pos_lbl.setStyleSheet(
            "color:#80ccff; font-size:9pt; font-weight:bold;")

        # Temperature label
        t_lbl = QLabel("—→—")
        t_lbl.setFixedWidth(106)
        t_lbl.setAlignment(Qt.AlignCenter)
        t_lbl.setStyleSheet("color:#ccc; font-size:8pt;")

        # Heat label
        heat_lbl = QLabel("—")
        heat_lbl.setFixedWidth(60)
        heat_lbl.setAlignment(Qt.AlignCenter)
        heat_lbl.setStyleSheet("color:#ffa040; font-size:8pt;")

        # Efficiency label
        eff_lbl = QLabel("—")
        eff_lbl.setFixedWidth(46)
        eff_lbl.setAlignment(Qt.AlignCenter)
        eff_lbl.setStyleSheet("color:#80c8ff; font-size:8pt;")

        # ΔP label
        dp_lbl = QLabel("—")
        dp_lbl.setFixedWidth(50)
        dp_lbl.setAlignment(Qt.AlignCenter)
        dp_lbl.setStyleSheet("color:#ccc; font-size:8pt;")

        # Sensor status
        sensor_lbl = QLabel("● Normal")
        sensor_lbl.setFixedWidth(113)
        sensor_lbl.setStyleSheet("color:#00ff96; font-size:8pt;")
        self.valve_sensor_labels[sid] = sensor_lbl

        # Auto-tune checkbox
        at_cb = QCheckBox("Auto")
        at_cb.setFixedWidth(53)
        at_cb.setChecked(True)
        at_cb.setStyleSheet("color:#aaa; font-size:8pt;")
        at_cb.stateChanged.connect(
            lambda st, s=sid: self._on_auto_tune_changed(s, st))
        self.valve_auto_tune_cbs[sid] = at_cb

        for w in [pos_lbl, t_lbl, heat_lbl, eff_lbl, dp_lbl, sensor_lbl, at_cb]:
            rl.addWidget(w)
        rl.addStretch()

        self._valve_param_labels[sid] = {
            'pos':  pos_lbl,
            'temp': t_lbl,
            'heat': heat_lbl,
            'eff':  eff_lbl,
            'dp':   dp_lbl,
        }

        row.setLayout(rl)
        return row

    # ── Analytics tab (2×2 chart grid) ────────────────────────────────────────

    def _build_analytics_tab(self):
        container = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.pressure_chart  = PressureChart()
        self.temp_chart      = TemperatureChart()
        self.flow_chart      = FlowChart()
        self.heat_duty_chart = HeatDutyChart()

        charts = [
            (self.pressure_chart,  "Pressure (bar)",   0, 0),
            (self.temp_chart,      "Temperature (°C)", 0, 1),
            (self.flow_chart,      "Flow Rate (kg/h)", 1, 0),
            (self.heat_duty_chart, "Heat Duty (kW)",   1, 1),
        ]
        for chart, title, row, col in charts:
            wrapper = QWidget()
            wl = QVBoxLayout()
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(2)
            t = QLabel(title)
            t.setStyleSheet("color:#88a; font-size:9pt; font-weight:bold; "
                            "padding:2px 4px;")
            chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            wl.addWidget(t)
            wl.addWidget(chart)
            wrapper.setLayout(wl)
            layout.addWidget(wrapper, row, col)
            layout.setRowStretch(row, 1)
            layout.setColumnStretch(col, 1)

        container.setLayout(layout)
        return container

    # ── Control bar ────────────────────────────────────────────────────────────

    def _build_control_bar(self):
        bar = QGroupBox("Control Dashboard")
        bar.setStyleSheet(_GROUP_STYLE)
        bar.setMaximumHeight(120)

        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 4, 8, 4)

        # Scenario buttons (2 rows)
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)

        row1 = QHBoxLayout()
        self.btn_normal    = self._btn("Normal Run",        "#1e3a1e")
        self.btn_spike     = self._btn("Force Spike",       "#4a2e00")
        self.btn_drop      = self._btn("Force Drop",        "#00254a")
        row1.addWidget(self.btn_normal)
        row1.addWidget(self.btn_spike)
        row1.addWidget(self.btn_drop)

        row2 = QHBoxLayout()
        self.btn_emergency = self._btn("⚠ EMERGENCY STOP",  "#6a0014")
        self.btn_reset     = self._btn("Reset All",          "#003d30")
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
        sep.setStyleSheet("background:#444; max-width:1px;")
        layout.addWidget(sep)

        # Auto-control checkbox
        self.auto_ctrl_cb = QCheckBox("Auto Control  ON")
        self.auto_ctrl_cb.setChecked(True)
        self.auto_ctrl_cb.setStyleSheet(
            "color:white; font-size:10pt; font-weight:bold;")
        self.auto_ctrl_cb.stateChanged.connect(self._on_auto_control_changed)
        layout.addWidget(self.auto_ctrl_cb, alignment=Qt.AlignVCenter)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("background:#444; max-width:1px;")
        layout.addWidget(sep2)

        # Event log
        log_layout = QVBoxLayout()
        log_layout.setSpacing(2)
        log_lbl = QLabel("Event Log:")
        log_lbl.setStyleSheet("color:white; font-size:9pt; font-weight:bold;")
        log_layout.addWidget(log_lbl)

        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(75)
        self.event_log.setStyleSheet("""
            QTextEdit {
                background:#0a0e18; color:#00ff96;
                border:1px solid #1e3a2e;
                font-family:'Courier New'; font-size:8pt;
            }
        """)
        log_layout.addWidget(self.event_log)

        layout.addLayout(log_layout, stretch=2)
        bar.setLayout(layout)
        return bar

    @staticmethod
    def _btn(text, bg="#3a3a3a"):
        b = QPushButton(text)
        b.setStyleSheet(_BTN_BASE + f"QPushButton {{ background:{bg}; }}")
        return b

    # ── Simulator link ─────────────────────────────────────────────────────────

    def set_simulator(self, simulator):
        self.simulator = simulator

    # ── Update loop ────────────────────────────────────────────────────────────

    def _update_ui(self):
        if not self.simulator:
            return
        state = self.simulator.get_state()

        # ── HMI header digital readouts ─────────────
        self._hdr_pressure.setText(f"{state['pressure']:.2f}")
        self._hdr_temperature.setText(f"{state['temperature']:.1f}")
        self._hdr_flow.setText(f"{state['flow']:.0f}")
        heat_kw = state.get('total_heat_duty_kw', 0)
        self._hdr_heat.setText(f"{heat_kw:.0f}")

        # State banner
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

        # ── Valve controls + Distribution P&ID ──────
        valve_positions = state['valve_positions']
        for sid, data in sensors.items():
            pos = valve_positions.get(sid, 0)

            # Distribution P&ID
            self.pid_display.update_valve_position(sid, pos)
            self.pid_display.update_sensor_status(sid, data['color'])

            # Sync knob
            if sid in self.valve_knobs:
                self.valve_knobs[sid].set_value(pos)

            # Valve row labels
            if sid in self._valve_param_labels:
                pl = self._valve_param_labels[sid]
                pl['pos'].setText(f"{pos:.0f}%")
                pl['temp'].setText(
                    f"{data['inlet_temp']:.0f}→{data['outlet_temp']:.0f}")
                pl['heat'].setText(f"{data['heat_duty_kw']:.0f}")
                pl['eff'].setText(f"{data['efficiency']:.1f}")
                pl['dp'].setText(f"{data['pressure_drop']:.3f}")

            # Sensor status label
            if sid in self.valve_sensor_labels:
                rgb = data['color']
                hex_c = "#{:02x}{:02x}{:02x}".format(*[int(v) for v in rgb])
                self.valve_sensor_labels[sid].setText(f"● {data['status']}")
                self.valve_sensor_labels[sid].setStyleSheet(
                    f"color:{hex_c}; font-size:8pt;")

            # Stage heat summary (left panel)
            if sid in self._stage_heat_labels:
                self._stage_heat_labels[sid].setText(
                    f"{data['heat_duty_kw']:.0f} kW")

            # Endpoint P&ID views
            if sid in self._endpoint_views:
                ep_data = dict(data)
                ep_data['valve_pos'] = pos
                self._endpoint_views[sid].update_data(ep_data)

        # Pipe colours on distribution P&ID
        self.pid_display.update_stage_temps(sensors)

        # ── Event log ───────────────────────────────
        events = self.event_logger.get_recent_events(25)
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

    def _on_valve_changed(self, sid: str, value: float):
        if not self.simulator:
            return
        vc = self.simulator.valve_controller
        if not vc.auto_control_enabled or not vc.get_valve_auto_tune(sid):
            vc.set_valve_position(sid, value)
            name = dict(self._VALVE_ORDER).get(sid, sid)
            self.event_logger.log(EventType.CONTROL,
                                  f"Manual: {name} → {value:.0f}%")

    def _on_auto_tune_changed(self, sid: str, state):
        if self.simulator:
            enabled = (state == Qt.Checked)
            self.simulator.valve_controller.set_valve_auto_tune(sid, enabled)
            name = dict(self._VALVE_ORDER).get(sid, sid)
            self.event_logger.log(
                EventType.CONTROL,
                f"{name} auto-tune {'ON' if enabled else 'OFF'}")

    def _on_normal_clicked(self):
        if self.simulator:
            self.simulator.reset()
            self.event_logger.log(EventType.INFO, "Reset to normal operation")

    def _on_spike_clicked(self):
        if self.simulator:
            self.simulator.steam_source._trigger_spike()
            self.event_logger.log(EventType.WARNING,
                                  "Manual trigger: Pressure spike")

    def _on_drop_clicked(self):
        if self.simulator:
            self.simulator.steam_source._trigger_drop()
            self.event_logger.log(EventType.WARNING,
                                  "Manual trigger: Pressure drop")

    def _on_emergency_clicked(self):
        if self.simulator:
            self.simulator.emergency_shutdown()
            self.event_logger.log(EventType.CRITICAL,
                                  "EMERGENCY SHUTDOWN ACTIVATED")

    def _on_reset_clicked(self):
        if self.simulator:
            self.simulator.reset()
            self.event_logger.log(
                EventType.INFO, "System reset — All parameters normalised")
            for chart in [self.pressure_chart, self.temp_chart,
                          self.flow_chart, self.heat_duty_chart]:
                chart.clear_data()

    def _on_auto_control_changed(self, state):
        if self.simulator:
            enabled = (state == Qt.Checked)
            self.simulator.valve_controller.auto_control_enabled = enabled
            self.auto_ctrl_cb.setText(
                f"Auto Control  {'ON' if enabled else 'OFF'}")
            self.event_logger.log(
                EventType.CONTROL,
                f"Auto-control {'enabled' if enabled else 'disabled'}")
