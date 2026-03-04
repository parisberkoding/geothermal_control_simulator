"""
Main Window
3-section layout: P&ID Display, Real-time Charts, Control Dashboard
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextEdit, QGroupBox, 
                             QCheckBox, QSplitter, QGridLayout, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from ui.pid_display import PIDDisplay
from ui.widgets.gauge import Gauge
from ui.widgets.valve_knob import ValveKnob
from ui.widgets.trend_chart import PressureChart, TemperatureChart, FlowChart
from utils.logger import EventLogger, EventType

class MainWindow(QMainWindow):
    """
    Main application window with 3 sections:
    1. P&ID Display + Status (top-left)
    2. Real-time Charts (bottom)
    3. Control Dashboard (top-right)
    """
    
    def __init__(self):
        super().__init__()
        
        # Event logger
        self.event_logger = EventLogger()
        
        # Simulator reference (will be set externally)
        self.simulator = None
        
        # Setup UI
        self._setup_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(100)  # 100ms = 10 FPS
        
        # Log startup
        self.event_logger.log(EventType.INFO, "System started - Normal operation")
    
    def _setup_ui(self):
        """Setup main UI"""
        self.setWindowTitle("Geothermal Direct Use Simulator - PT Geo Dipa Unit Patuha")
        self.setGeometry(100, 100, 1600, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # === TOP ROW: P&ID Display + Control Panel ===
        top_splitter = QSplitter(Qt.Horizontal)
        
        # LEFT: P&ID Display
        self.pid_display = PIDDisplay()
        top_splitter.addWidget(self.pid_display)
        
        # RIGHT: Status and Valve Controls
        right_panel = self._create_right_panel()
        top_splitter.addWidget(right_panel)
        
        # Set splitter ratio (65% left, 35% right)
        top_splitter.setSizes([1000, 600])
        
        main_layout.addWidget(top_splitter, stretch=3)
        
        # === MIDDLE ROW: Real-time Charts ===
        charts_widget = self._create_charts_section()
        main_layout.addWidget(charts_widget, stretch=1)
        
        # === BOTTOM ROW: Control Dashboard ===
        control_dashboard = self._create_control_dashboard()
        main_layout.addWidget(control_dashboard, stretch=0)
        
        central_widget.setLayout(main_layout)
    
    def _create_right_panel(self):
        """Create right panel with status and valve controls"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # === MAIN STEAM STATUS ===
        status_group = QGroupBox("Main Steam Status")
        status_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-size: 11pt;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        status_layout = QVBoxLayout()
        
        # Gauges layout
        gauges_layout = QHBoxLayout()
        
        # Pressure gauge
        self.pressure_gauge = Gauge(
            min_value=0, max_value=15, 
            unit="bar", label="Pressure",
            warning_threshold=10, critical_threshold=12
        )
        self.pressure_gauge.set_value(8.0)
        
        # Temperature gauge
        self.temp_gauge = Gauge(
            min_value=150, max_value=200,
            unit="°C", label="Temperature"
        )
        self.temp_gauge.set_value(174.0)
        
        gauges_layout.addWidget(self.pressure_gauge)
        gauges_layout.addWidget(self.temp_gauge)
        status_layout.addLayout(gauges_layout)
        
        # Flow display
        self.flow_label = QLabel("Flow Rate: 3374 kg/h")
        self.flow_label.setAlignment(Qt.AlignCenter)
        self.flow_label.setStyleSheet("color: white; font-size: 12pt; font-weight: bold;")
        status_layout.addWidget(self.flow_label)
        
        # Status indicator
        self.status_label = QLabel("● Normal Operation")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #00ff96; font-size: 11pt; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # === VALVE CONTROLS ===
        valve_group = QGroupBox("Valve Controls")
        valve_group.setStyleSheet(status_group.styleSheet())
        
        valve_layout = QVBoxLayout()
        valve_layout.setSpacing(5)
        
        # Create 6 valve controls with auto-tune checkboxes and sensor indicators
        self.valve_knobs = {}
        self.valve_auto_tune_checkboxes = {}
        self.valve_sensor_labels = {}
        
        valves = [
            ("food_dehydrator", "Food Dehydrator", 65.0),
            ("hot_pool", "Hot Pool", 80.0),
            ("tea_dryer", "Tea Dryer", 55.0),
            ("cabin", "Cabin", 45.0),
            ("green_house", "Green House", 70.0),
            ("fishery", "Fishery Pond", 60.0)
        ]
        
        for valve_id, label, initial_pos in valves:
            # Container for each valve
            valve_container = QWidget()
            valve_container_layout = QHBoxLayout()
            valve_container_layout.setContentsMargins(5, 5, 5, 5)
            
            # Left: Knob
            knob = ValveKnob(label="", initial_value=initial_pos)
            knob.setMaximumWidth(100)
            knob.valueChanged.connect(lambda v, vid=valve_id: self._on_valve_changed(vid, v))
            self.valve_knobs[valve_id] = knob
            valve_container_layout.addWidget(knob)
            
            # Right: Info panel
            info_panel = QWidget()
            info_layout = QVBoxLayout()
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(3)
            
            # Valve name
            name_label = QLabel(label)
            name_label.setStyleSheet("color: white; font-size: 10pt; font-weight: bold;")
            info_layout.addWidget(name_label)
            
            # Sensor status
            sensor_label = QLabel("● Normal")
            sensor_label.setStyleSheet("color: #00ff96; font-size: 9pt;")
            self.valve_sensor_labels[valve_id] = sensor_label
            info_layout.addWidget(sensor_label)
            
            # Auto-tune checkbox
            auto_tune_cb = QCheckBox("Auto-Tune")
            auto_tune_cb.setChecked(True)
            auto_tune_cb.setStyleSheet("color: #aaa; font-size: 9pt;")
            auto_tune_cb.stateChanged.connect(lambda state, vid=valve_id: self._on_auto_tune_changed(vid, state))
            self.valve_auto_tune_checkboxes[valve_id] = auto_tune_cb
            info_layout.addWidget(auto_tune_cb)
            
            info_layout.addStretch()
            info_panel.setLayout(info_layout)
            valve_container_layout.addWidget(info_panel)
            
            valve_container.setLayout(valve_container_layout)
            valve_layout.addWidget(valve_container)
            
            # Separator line
            if valve_id != "fishery":
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setStyleSheet("background-color: #444;")
                valve_layout.addWidget(line)
        
        valve_group.setLayout(valve_layout)
        layout.addWidget(valve_group)
        
        panel.setLayout(layout)
        return panel
    
    def _create_charts_section(self):
        """Create real-time charts section"""
        charts_widget = QWidget()
        charts_layout = QHBoxLayout()
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(5)
        
        # Create 3 charts
        self.pressure_chart = PressureChart()
        self.temp_chart = TemperatureChart()
        self.flow_chart = FlowChart()
        
        charts_layout.addWidget(self.pressure_chart)
        charts_layout.addWidget(self.temp_chart)
        charts_layout.addWidget(self.flow_chart)
        
        charts_widget.setLayout(charts_layout)
        return charts_widget
    
    def _create_control_dashboard(self):
        """Create control dashboard section"""
        dashboard = QGroupBox("Control Dashboard")
        dashboard.setStyleSheet("""
            QGroupBox {
                color: white;
                font-size: 11pt;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QHBoxLayout()
        
        # LEFT: Scenario buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(5)
        
        button_style = """
            QPushButton {
                background-color: #404040;
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 8px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
                border: 1px solid #888;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
        """
        
        # Row 1: Normal scenarios
        row1 = QHBoxLayout()
        self.btn_normal = QPushButton("Normal Run")
        self.btn_normal.clicked.connect(self._on_normal_clicked)
        self.btn_normal.setStyleSheet(button_style)
        
        self.btn_spike = QPushButton("Force Spike")
        self.btn_spike.clicked.connect(self._on_spike_clicked)
        self.btn_spike.setStyleSheet(button_style + "QPushButton { background-color: #805000; }")
        
        self.btn_drop = QPushButton("Force Drop")
        self.btn_drop.clicked.connect(self._on_drop_clicked)
        self.btn_drop.setStyleSheet(button_style + "QPushButton { background-color: #004080; }")
        
        row1.addWidget(self.btn_normal)
        row1.addWidget(self.btn_spike)
        row1.addWidget(self.btn_drop)
        buttons_layout.addLayout(row1)
        
        # Row 2: Emergency and reset
        row2 = QHBoxLayout()
        self.btn_emergency = QPushButton("⚠ EMERGENCY STOP")
        self.btn_emergency.clicked.connect(self._on_emergency_clicked)
        self.btn_emergency.setStyleSheet(button_style + "QPushButton { background-color: #800020; }")
        
        self.btn_reset = QPushButton("Reset All")
        self.btn_reset.clicked.connect(self._on_reset_clicked)
        self.btn_reset.setStyleSheet(button_style + "QPushButton { background-color: #006040; }")
        
        row2.addWidget(self.btn_emergency)
        row2.addWidget(self.btn_reset)
        buttons_layout.addLayout(row2)
        
        # Auto-control checkbox
        self.auto_control_checkbox = QCheckBox("Auto Control ON")
        self.auto_control_checkbox.setChecked(True)
        self.auto_control_checkbox.stateChanged.connect(self._on_auto_control_changed)
        self.auto_control_checkbox.setStyleSheet("color: white; font-size: 10pt; font-weight: bold;")
        buttons_layout.addWidget(self.auto_control_checkbox)
        
        layout.addLayout(buttons_layout, stretch=1)
        
        # RIGHT: Event log
        log_layout = QVBoxLayout()
        log_label = QLabel("Event Log:")
        log_label.setStyleSheet("color: white; font-size: 10pt; font-weight: bold;")
        log_layout.addWidget(log_label)
        
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(100)
        self.event_log.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff96;
                border: 1px solid #444;
                font-family: 'Courier New';
                font-size: 9pt;
            }
        """)
        log_layout.addWidget(self.event_log)
        
        layout.addLayout(log_layout, stretch=2)
        
        dashboard.setLayout(layout)
        return dashboard
    
    def set_simulator(self, simulator):
        """Set simulator reference"""
        self.simulator = simulator
    
    def _update_ui(self):
        """Update UI with simulator data"""
        if not self.simulator:
            return
        
        # Get current state from simulator
        state = self.simulator.get_state()
        
        # Update gauges
        self.pressure_gauge.set_value(state['pressure'])
        self.temp_gauge.set_value(state['temperature'])
        
        # Update flow label
        self.flow_label.setText(f"Flow Rate: {state['flow']:.0f} kg/h")
        
        # Update status label
        status_text, status_color = self._get_status_display(state)
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 11pt; font-weight: bold;")
        
        # Update charts
        self.pressure_chart.add_data_point(state['pressure'])
        self.temp_chart.add_data_point(state['temperature'])
        self.flow_chart.add_data_point(state['flow'])
        
        # Update valve positions in P&ID and sensor colors
        endpoint_sensors = state.get('endpoint_sensors', {})
        for valve_id, position in state['valve_positions'].items():
            # Update P&ID valve indicators
            self.pid_display.update_valve_position(valve_id, position)
            
            # Update P&ID sensor indicators
            if valve_id in endpoint_sensors:
                sensor_data = endpoint_sensors[valve_id]
                sensor_color = sensor_data['color']
                self.pid_display.update_sensor_status(valve_id, sensor_color)
            
            # Update valve knobs if auto-control moved them
            if valve_id in self.valve_knobs:
                self.valve_knobs[valve_id].set_value(position)
            
            # Update sensor labels in valve panel
            if valve_id in self.valve_sensor_labels and valve_id in endpoint_sensors:
                sensor_data = endpoint_sensors[valve_id]
                status_text = sensor_data['status']
                color_rgb = sensor_data['color']
                color_hex = f"#{int(color_rgb[0]):02x}{int(color_rgb[1]):02x}{int(color_rgb[2]):02x}"
                
                self.valve_sensor_labels[valve_id].setText(f"● {status_text}")
                self.valve_sensor_labels[valve_id].setStyleSheet(f"color: {color_hex}; font-size: 9pt;")
        
        # Update event log
        self._update_event_log()
    
    def _get_status_display(self, state):
        """Get status text and color"""
        system_state = state['state']
        pressure = state['pressure']
        
        if system_state == "EMERGENCY":
            return "⚠ EMERGENCY SHUTDOWN", "#ff3333"
        elif system_state in ["DISTURBANCE_SPIKE", "DISTURBANCE_DROP", "DISTURBANCE_FLOW"]:
            return f"⚠ {system_state.replace('_', ' ')}", "#ffcc00"
        elif system_state == "STABILIZING":
            return "⟳ Stabilizing...", "#ffaa00"
        elif pressure > 10:
            return "⚠ High Pressure Warning", "#ffcc00"
        elif pressure < 6:
            return "⚠ Low Pressure Warning", "#6699ff"
        else:
            return "● Normal Operation", "#00ff96"
    
    def _update_event_log(self):
        """Update event log display"""
        events = self.event_logger.get_recent_events(20)
        self.event_log.setText("\n".join(events))
        
        # Auto-scroll to bottom
        self.event_log.verticalScrollBar().setValue(
            self.event_log.verticalScrollBar().maximum()
        )
    
    # === Event Handlers ===
    
    def _on_valve_changed(self, valve_id, value):
        """Handle manual valve position change"""
        if self.simulator:
            # Only apply if auto-control is off OR auto-tune for this valve is off
            valve_auto_tune = self.simulator.valve_controller.get_valve_auto_tune(valve_id)
            if not self.simulator.valve_controller.auto_control_enabled or not valve_auto_tune:
                self.simulator.valve_controller.set_valve_position(valve_id, value)
                self.event_logger.log(EventType.CONTROL, 
                                     f"Manual: {valve_id.replace('_', ' ').title()} valve set to {value:.0f}%")
    
    def _on_auto_tune_changed(self, valve_id, state):
        """Handle auto-tune checkbox change"""
        if self.simulator:
            enabled = (state == Qt.Checked)
            self.simulator.valve_controller.set_valve_auto_tune(valve_id, enabled)
            
            status = "enabled" if enabled else "disabled"
            valve_name = valve_id.replace('_', ' ').title()
            self.event_logger.log(EventType.CONTROL, f"{valve_name} auto-tune {status}")
    
    def _on_normal_clicked(self):
        """Normal operation"""
        if self.simulator:
            self.simulator.reset()
            self.event_logger.log(EventType.INFO, "Reset to normal operation")
    
    def _on_spike_clicked(self):
        """Force pressure spike"""
        if self.simulator:
            self.simulator.steam_source._trigger_spike()
            self.event_logger.log(EventType.WARNING, "Manual trigger: Pressure spike scenario")
    
    def _on_drop_clicked(self):
        """Force pressure drop"""
        if self.simulator:
            self.simulator.steam_source._trigger_drop()
            self.event_logger.log(EventType.WARNING, "Manual trigger: Pressure drop scenario")
    
    def _on_emergency_clicked(self):
        """Emergency shutdown"""
        if self.simulator:
            self.simulator.emergency_shutdown()
            self.event_logger.log(EventType.CRITICAL, "EMERGENCY SHUTDOWN ACTIVATED")
    
    def _on_reset_clicked(self):
        """Reset everything"""
        if self.simulator:
            self.simulator.reset()
            self.event_logger.log(EventType.INFO, "System reset - All parameters normalized")
            
            # Clear charts
            self.pressure_chart.clear_data()
            self.temp_chart.clear_data()
            self.flow_chart.clear_data()
    
    def _on_auto_control_changed(self, state):
        """Toggle auto-control"""
        if self.simulator:
            enabled = (state == Qt.Checked)
            self.simulator.valve_controller.auto_control_enabled = enabled
            
            status = "enabled" if enabled else "disabled"
            self.event_logger.log(EventType.CONTROL, f"Auto-control {status}")
            
            # Update checkbox text
            self.auto_control_checkbox.setText(f"Auto Control {'ON' if enabled else 'OFF'}")

# Test window standalone
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Apply dark theme
    app.setStyle('Fusion')
    from PyQt5.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(40, 40, 40))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(40, 40, 40))
    palette.setColor(QPalette.ButtonText, Qt.white)
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())