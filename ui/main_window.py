"""
Main Window  –  Responsive layout optimised for 14-inch laptops (≤ 1366 × 768).

Layout:
┌────────────────────────────────────────────────────────────────────┐
│  [Left Status Panel: 230px]  │  [Tab Area]                          │
│  • Main steam gauges          │  Tab 1 – Pipeline (Cascade P&ID)    │
│  • Flow / state               │  Tab 2 – Valve Controls (7 stages)  │
│  • Geochemistry               │  Tab 3 – Analytics (Charts)         │
├───────────────────────────────┴────────────────────────────────────┤
│  Control Bar: scenario buttons │ auto-control toggle │ event log    │
└────────────────────────────────────────────────────────────────────┘
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QTextEdit, QGroupBox, QCheckBox,
    QTabWidget, QScrollArea, QGridLayout, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from ui.pid_display import PIDDisplay
from ui.widgets.gauge import Gauge
from ui.widgets.valve_knob import ValveKnob
from ui.widgets.trend_chart import PressureChart, TemperatureChart, FlowChart, HeatDutyChart
from utils.logger import EventLogger, EventType
from simulation.endpoints import CASCADE_STAGES

# ── shared style helpers ──────────────────────────────────────────────────────

_GROUP_STYLE = """
    QGroupBox {
        color: white; font-size: 10pt; font-weight: bold;
        border: 2px solid #444; border-radius: 5px;
        margin-top: 10px; padding-top: 8px;
    }
    QGroupBox::title {
        subcontrol-origin: margin; left: 8px; padding: 0 4px;
    }
"""

_BTN_BASE = """
    QPushButton {
        background:#3a3a3a; color:white; border:1px solid #555;
        border-radius:3px; padding:6px 10px;
        font-size:9pt; font-weight:bold;
    }
    QPushButton:hover { background:#4a4a4a; border-color:#777; }
    QPushButton:pressed { background:#2a2a2a; }
"""

_STATUS_COLORS = {
    'EMERGENCY':          '#ff3333',
    'PRESSURE_SPIKE':     '#ffcc00',
    'PRESSURE_DROP':      '#6699ff',
    'FLOW_SURGE':         '#ff9900',
    'STABILIZING':        '#ffaa00',
    'NORMAL':             '#00ff96',
}


class MainWindow(QMainWindow):
    """Main application window."""

    # Cascade stage IDs in display order
    _VALVE_ORDER = [
        ('cabin',              'Cabin Warmer'),
        ('hot_pool',           'Kolam Rendam'),
        ('tea_dryer',          'Pengering Teh'),
        ('food_dehydrator_1',  'Food Dehydrator 1'),
        ('fish_pond',          'Fish Pond'),
        ('food_dehydrator_2',  'Food Dehydrator 2'),
        ('green_house',        'Green House'),
    ]

    def __init__(self):
        super().__init__()
        self.event_logger = EventLogger()
        self.simulator    = None

        self._setup_ui()

        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_ui)
        self._update_timer.start(100)   # 10 FPS

        self.event_logger.log(EventType.INFO, "System started — Normal operation")

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle("Geothermal SCADA Simulator — PT Geo Dipa Unit Patuha")
        self.setGeometry(60, 40, 1340, 720)
        self.setMinimumSize(1100, 640)

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout()
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(5)

        # ── Top area: left status + tab panel ────
        top_split = QSplitter(Qt.Horizontal)
        top_split.addWidget(self._build_status_panel())
        top_split.addWidget(self._build_tab_panel())
        top_split.setSizes([230, 1100])
        top_split.setChildrenCollapsible(False)
        root.addWidget(top_split, stretch=10)

        # ── Bottom: control bar ───────────────────
        root.addWidget(self._build_control_bar(), stretch=0)

        central.setLayout(root)

    # ── Left status panel ─────────────────────────────────────────────────────

    def _build_status_panel(self):
        panel = QWidget()
        panel.setMaximumWidth(235)
        panel.setMinimumWidth(200)
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # ── Main Steam ──────────────────────────
        steam_grp = QGroupBox("Main Steam  (Well DP-6)")
        steam_grp.setStyleSheet(_GROUP_STYLE)
        sg_layout = QVBoxLayout()
        sg_layout.setSpacing(4)

        gauges_row = QHBoxLayout()

        self.pressure_gauge = Gauge(
            min_value=0, max_value=15,
            unit="bar", label="Pressure",
            warning_threshold=10, critical_threshold=12
        )
        self.pressure_gauge.set_value(8.0)
        self.pressure_gauge.setMaximumSize(100, 100)

        self.temp_gauge = Gauge(
            min_value=150, max_value=200,
            unit="°C", label="Temp"
        )
        self.temp_gauge.set_value(174.0)
        self.temp_gauge.setMaximumSize(100, 100)

        gauges_row.addWidget(self.pressure_gauge)
        gauges_row.addWidget(self.temp_gauge)
        sg_layout.addLayout(gauges_row)

        self._flow_lbl = QLabel("Flow: 3374 kg/h")
        self._flow_lbl.setAlignment(Qt.AlignCenter)
        self._flow_lbl.setStyleSheet("color:#aef; font-size:10pt; font-weight:bold;")
        sg_layout.addWidget(self._flow_lbl)

        self._state_lbl = QLabel("● Normal Operation")
        self._state_lbl.setAlignment(Qt.AlignCenter)
        self._state_lbl.setStyleSheet("color:#00ff96; font-size:9pt; font-weight:bold;")
        sg_layout.addWidget(self._state_lbl)

        steam_grp.setLayout(sg_layout)
        layout.addWidget(steam_grp)

        # ── Geochemistry ─────────────────────────
        geo_grp = QGroupBox("Fluid Parameters")
        geo_grp.setStyleSheet(_GROUP_STYLE)
        geo_layout = QGridLayout()
        geo_layout.setSpacing(3)

        lbl_style  = "color:#ccc; font-size:8pt;"
        val_style  = "color:#fff; font-size:8pt; font-weight:bold;"

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
            nl.setStyleSheet(lbl_style)
            vl = QLabel("—")
            vl.setStyleSheet(val_style)
            geo_layout.addWidget(nl, row, 0)
            geo_layout.addWidget(vl, row, 1)
            self._geo_labels[attr] = vl

        geo_grp.setLayout(geo_layout)
        layout.addWidget(geo_grp)

        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    # ── Tab panel ────────────────────────────────────────────────────────────

    def _build_tab_panel(self):
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: 2px solid #444; border-radius:3px; }
            QTabBar::tab {
                background:#2a2a2a; color:#aaa; padding:6px 14px;
                font-size:9pt; font-weight:bold; border-radius:3px 3px 0 0;
            }
            QTabBar::tab:selected { background:#3a4a5a; color:white; }
            QTabBar::tab:hover    { background:#353535; }
        """)
        self._tabs.addTab(self._build_pipeline_tab(),  "🗺  Pipeline")
        self._tabs.addTab(self._build_controls_tab(),  "🔧  Valves")
        self._tabs.addTab(self._build_analytics_tab(), "📊  Analytics")
        return self._tabs

    # ── Pipeline tab ──────────────────────────────────────────────────────────

    def _build_pipeline_tab(self):
        container = QWidget()
        layout    = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)

        # Legend bar
        legend = QLabel(
            "Pipe colour:  "
            "<span style='color:#dc3219;'>■</span> Hot (>130°C)  "
            "<span style='color:#dc9019;'>■</span> Warm (60–130°C)  "
            "<span style='color:#19aabe;'>■</span> Cool (<60°C)  "
            "  ▶ Valve  ●Sensor"
        )
        legend.setStyleSheet("color:#888; font-size:8pt;")
        layout.addWidget(legend)

        self.pid_display = PIDDisplay()
        layout.addWidget(self.pid_display)

        container.setLayout(layout)
        return container

    # ── Valve controls tab ────────────────────────────────────────────────────

    def _build_controls_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:#1a1a1a; border:none;")

        inner  = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Column header
        hdr = QWidget()
        hr  = QHBoxLayout()
        hr.setContentsMargins(0, 0, 0, 0)
        for txt, w in [("Valve", 70), ("Stage", 130), ("Pos %", 50),
                       ("T-in→T-out (°C)", 115), ("Heat kW", 68),
                       ("Eff %", 50), ("ΔP bar", 55),
                       ("Status", 110), ("Auto-Tune", 75)]:
            l = QLabel(txt)
            l.setFixedWidth(w)
            l.setStyleSheet("color:#888; font-size:8pt; font-weight:bold;")
            hr.addWidget(l)
        hr.addStretch()
        hdr.setLayout(hr)
        layout.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#444;")
        layout.addWidget(sep)

        self.valve_knobs          = {}
        self.valve_auto_tune_cbs  = {}
        self.valve_sensor_labels  = {}
        self._valve_param_labels  = {}   # sid → {t_label, heat_label, eff_label, dp_label}

        for sid, display_name in self._VALVE_ORDER:
            row_widget = self._build_valve_row(sid, display_name)
            layout.addWidget(row_widget)

            sep2 = QFrame()
            sep2.setFrameShape(QFrame.HLine)
            sep2.setStyleSheet("background:#2a2a2a;")
            layout.addWidget(sep2)

        layout.addStretch(1)
        inner.setLayout(layout)
        scroll.setWidget(inner)
        return scroll

    def _build_valve_row(self, sid: str, display_name: str):
        row = QWidget()
        row.setFixedHeight(78)
        rl  = QHBoxLayout()
        rl.setContentsMargins(4, 2, 4, 2)
        rl.setSpacing(6)

        # Knob
        knob = ValveKnob(label="", initial_value=70.0)
        knob.setFixedSize(68, 68)
        knob.valueChanged.connect(lambda v, s=sid: self._on_valve_changed(s, v))
        self.valve_knobs[sid] = knob
        rl.addWidget(knob)

        # Stage name
        nl = QLabel(display_name)
        nl.setFixedWidth(128)
        nl.setWordWrap(True)
        nl.setStyleSheet("color:white; font-size:9pt; font-weight:bold;")
        rl.addWidget(nl)

        # Position label (updated dynamically)
        pos_lbl = QLabel("70%")
        pos_lbl.setFixedWidth(48)
        pos_lbl.setAlignment(Qt.AlignCenter)
        pos_lbl.setStyleSheet("color:#aef; font-size:9pt; font-weight:bold;")

        # Parameter labels
        t_lbl    = QLabel("—→—")
        heat_lbl = QLabel("—")
        eff_lbl  = QLabel("—")
        dp_lbl   = QLabel("—")
        for lbl, w in [(t_lbl, 113), (heat_lbl, 66), (eff_lbl, 48), (dp_lbl, 53)]:
            lbl.setFixedWidth(w)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color:#ccc; font-size:8pt;")

        # Sensor status
        sensor_lbl = QLabel("● Normal")
        sensor_lbl.setFixedWidth(108)
        sensor_lbl.setStyleSheet("color:#00ff96; font-size:8pt;")
        self.valve_sensor_labels[sid] = sensor_lbl

        # Auto-tune checkbox
        at_cb = QCheckBox("Auto")
        at_cb.setChecked(True)
        at_cb.setStyleSheet("color:#aaa; font-size:8pt;")
        at_cb.stateChanged.connect(lambda st, s=sid: self._on_auto_tune_changed(s, st))
        self.valve_auto_tune_cbs[sid] = at_cb

        for w in [pos_lbl, t_lbl, heat_lbl, eff_lbl, dp_lbl,
                  sensor_lbl, at_cb]:
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

    # ── Analytics tab ─────────────────────────────────────────────────────────

    def _build_analytics_tab(self):
        container = QWidget()
        layout    = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(5)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(5)

        self.pressure_chart  = PressureChart()
        self.temp_chart      = TemperatureChart()
        self.flow_chart      = FlowChart()
        self.heat_duty_chart = HeatDutyChart()

        for chart in [self.pressure_chart, self.temp_chart,
                      self.flow_chart, self.heat_duty_chart]:
            chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            charts_row.addWidget(chart)

        layout.addLayout(charts_row)
        container.setLayout(layout)
        return container

    # ── Control bar (always visible at bottom) ────────────────────────────────

    def _build_control_bar(self):
        bar = QGroupBox("Control Dashboard")
        bar.setStyleSheet(_GROUP_STYLE)
        bar.setMaximumHeight(115)

        layout = QHBoxLayout()
        layout.setSpacing(8)

        # Scenario buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)

        row1 = QHBoxLayout()
        self.btn_normal    = self._btn("Normal Run",       "#2a4a2a")
        self.btn_spike     = self._btn("Force Spike",      "#5a3800")
        self.btn_drop      = self._btn("Force Drop",       "#00305a")
        row1.addWidget(self.btn_normal)
        row1.addWidget(self.btn_spike)
        row1.addWidget(self.btn_drop)

        row2 = QHBoxLayout()
        self.btn_emergency = self._btn("⚠ EMERGENCY STOP", "#7a0018")
        self.btn_reset     = self._btn("Reset All",         "#005040")
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

        # Auto-control
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background:#444;")
        layout.addWidget(sep)

        self.auto_ctrl_cb = QCheckBox("Auto Control  ON")
        self.auto_ctrl_cb.setChecked(True)
        self.auto_ctrl_cb.setStyleSheet("color:white; font-size:10pt; font-weight:bold;")
        self.auto_ctrl_cb.stateChanged.connect(self._on_auto_control_changed)
        layout.addWidget(self.auto_ctrl_cb, alignment=Qt.AlignVCenter)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("background:#444;")
        layout.addWidget(sep2)

        # Event log
        log_layout = QVBoxLayout()
        log_layout.setSpacing(2)
        log_lbl = QLabel("Event Log:")
        log_lbl.setStyleSheet("color:white; font-size:9pt; font-weight:bold;")
        log_layout.addWidget(log_lbl)

        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(72)
        self.event_log.setStyleSheet("""
            QTextEdit {
                background:#111; color:#00ff96;
                border:1px solid #333;
                font-family:'Courier New'; font-size:8pt;
            }
        """)
        log_layout.addWidget(self.event_log)

        layout.addLayout(log_layout, stretch=2)
        bar.setLayout(layout)
        return bar

    @staticmethod
    def _btn(text, bg_color="#3a3a3a"):
        b = QPushButton(text)
        b.setStyleSheet(_BTN_BASE + f"QPushButton {{ background:{bg_color}; }}")
        return b

    # ── Simulator link ────────────────────────────────────────────────────────

    def set_simulator(self, simulator):
        self.simulator = simulator

    # ── Update loop ───────────────────────────────────────────────────────────

    def _update_ui(self):
        if not self.simulator:
            return
        state = self.simulator.get_state()

        # Gauges
        self.pressure_gauge.set_value(state['pressure'])
        self.temp_gauge.set_value(state['temperature'])

        # Flow / state
        self._flow_lbl.setText(f"Flow: {state['flow']:.0f} kg/h")
        txt, color = self._state_display(state)
        self._state_lbl.setText(txt)
        self._state_lbl.setStyleSheet(
            f"color:{color}; font-size:9pt; font-weight:bold;")

        # Geochemistry panel
        geo = state.get('geochemistry', {})
        heat_kw = state.get('total_heat_duty_kw', 0)
        silica_risk = geo.get('silica_risk', '—')
        silica_color = {'High': '#ff6060', 'Medium': '#ffcc00',
                        'Low': '#00ff96'}.get(silica_risk, '#aaa')

        self._geo_labels['ph_val'].setText(f"{geo.get('ph', 0):.2f}")
        self._geo_labels['tds_val'].setText(f"{geo.get('tds_mg_l', 0):.0f}")
        lbl = self._geo_labels['silica_val']
        lbl.setText(silica_risk)
        lbl.setStyleSheet(f"color:{silica_color}; font-size:8pt; font-weight:bold;")
        self._geo_labels['heat_val'].setText(f"{heat_kw:.0f}")
        # Enthalpy approx from steam tables: h ≈ 2600–2800 kJ/kg for steam
        enthalpy = 419 + 2.09 * state['temperature']
        self._geo_labels['enthalpy_val'].setText(f"{enthalpy:.0f} kJ/kg")
        sensors = state.get('endpoint_sensors', {})
        if sensors:
            avg_eff = sum(d.get('efficiency', 0) for d in sensors.values()) / len(sensors)
            self._geo_labels['efficiency_val'].setText(f"{avg_eff:.1f} %")

        # Charts (analytics tab)
        self.pressure_chart.add_data_point(state['pressure'])
        self.temp_chart.add_data_point(state['temperature'])
        self.flow_chart.add_data_point(state['flow'])
        self.heat_duty_chart.add_data_point(heat_kw)

        # Valve controls + P&ID updates
        valve_positions = state['valve_positions']
        for sid, data in sensors.items():
            pos = valve_positions.get(sid, 0)

            # P&ID
            self.pid_display.update_valve_position(sid, pos)
            self.pid_display.update_sensor_status(sid, data['color'])

            # Sync knob (auto-control may have moved it)
            if sid in self.valve_knobs:
                self.valve_knobs[sid].set_value(pos)

            # Valve row labels
            if sid in self._valve_param_labels:
                pl = self._valve_param_labels[sid]
                pl['pos'].setText(f"{pos:.0f}%")
                pl['temp'].setText(f"{data['inlet_temp']:.0f}→{data['outlet_temp']:.0f}")
                pl['heat'].setText(f"{data['heat_duty_kw']:.0f}")
                pl['eff'].setText(f"{data['efficiency']:.1f}")
                pl['dp'].setText(f"{data['pressure_drop']:.3f}")

            # Sensor status label
            if sid in self.valve_sensor_labels:
                color_rgb = data['color']
                hex_c = "#{:02x}{:02x}{:02x}".format(*[int(v) for v in color_rgb])
                self.valve_sensor_labels[sid].setText(f"● {data['status']}")
                self.valve_sensor_labels[sid].setStyleSheet(
                    f"color:{hex_c}; font-size:8pt;")

        # P&ID temperature pipe colours
        self.pid_display.update_stage_temps(sensors)

        # Event log
        events = self.event_logger.get_recent_events(20)
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
            return "⚠ High Pressure Warning", "#ffcc00"
        if p < 6:
            return "⚠ Low Pressure Warning", "#6699ff"
        return "● Normal Operation", "#00ff96"

    # ── Event handlers ────────────────────────────────────────────────────────

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
            self.event_logger.log(EventType.CONTROL,
                                  f"{name} auto-tune {'ON' if enabled else 'OFF'}")

    def _on_normal_clicked(self):
        if self.simulator:
            self.simulator.reset()
            self.event_logger.log(EventType.INFO, "Reset to normal operation")

    def _on_spike_clicked(self):
        if self.simulator:
            self.simulator.steam_source._trigger_spike()
            self.event_logger.log(EventType.WARNING, "Manual trigger: Pressure spike")

    def _on_drop_clicked(self):
        if self.simulator:
            self.simulator.steam_source._trigger_drop()
            self.event_logger.log(EventType.WARNING, "Manual trigger: Pressure drop")

    def _on_emergency_clicked(self):
        if self.simulator:
            self.simulator.emergency_shutdown()
            self.event_logger.log(EventType.CRITICAL, "EMERGENCY SHUTDOWN ACTIVATED")

    def _on_reset_clicked(self):
        if self.simulator:
            self.simulator.reset()
            self.event_logger.log(EventType.INFO, "System reset — All parameters normalised")
            for chart in [self.pressure_chart, self.temp_chart,
                          self.flow_chart, self.heat_duty_chart]:
                chart.clear_data()

    def _on_auto_control_changed(self, state):
        if self.simulator:
            enabled = (state == Qt.Checked)
            self.simulator.valve_controller.auto_control_enabled = enabled
            self.auto_ctrl_cb.setText(f"Auto Control  {'ON' if enabled else 'OFF'}")
            self.event_logger.log(EventType.CONTROL,
                                  f"Auto-control {'enabled' if enabled else 'disabled'}")
