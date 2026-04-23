"""
Valve Slider Widget
Horizontal range-slider control for valve position (0–100 %).
Replaces the old rotary knob; keeps the same public API so the
rest of the codebase requires minimal changes.

The widget shows:
  • The unit's required process temperature range (e.g. 95–98 °C)
  • A horizontal slider for valve opening (0–100 %)
  • The current opening percentage
  • The live process temperature reported by the simulator
"""
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSlider
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


_SLIDER_STYLE = """
QSlider::groove:horizontal {{
    height: 8px;
    background: #1e2a3a;
    border: 1px solid #334455;
    border-radius: 4px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #005533, stop:1 {accent});
    border-radius: 4px;
}}
QSlider::handle:horizontal {{
    background: {accent};
    border: 2px solid {accent_light};
    width: 14px;
    height: 14px;
    margin: -3px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {accent_light};
}}
"""

_ACCENT       = "#00cc88"
_ACCENT_LIGHT = "#44ffbb"


class ValveKnob(QWidget):
    """
    Horizontal slider valve control.
    API-compatible with the old rotary ValveKnob:
        set_value(float)  – update slider position (0–100)
        get_value() → float
        valueChanged signal(float)
    Extra method:
        set_process_temp(float) – display live process temperature
    """

    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None, label: str = "Valve",
                 initial_value: float = 50.0,
                 temp_range: tuple = (20, 100)):
        super().__init__(parent)

        self.label_text = label
        self.value      = float(initial_value)
        self.temp_range = temp_range   # (unit_min, unit_max) in °C

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(4, 2, 4, 2)
        root.setSpacing(2)

        # ── Top row: range label + live process temp ──────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self._range_lbl = QLabel(
            f"{self.temp_range[0]}°C – {self.temp_range[1]}°C")
        self._range_lbl.setStyleSheet(
            "color:#5588aa; font-size:7pt; font-weight:bold;")

        self._proc_lbl = QLabel("–– °C")
        self._proc_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._proc_lbl.setStyleSheet(
            "color:#ffaa40; font-size:8pt; font-weight:bold;")

        top_row.addWidget(self._range_lbl)
        top_row.addStretch(1)
        top_row.addWidget(self._proc_lbl)
        root.addLayout(top_row)

        # ── Slider row ────────────────────────────────────────────────────────
        slider_row = QHBoxLayout()
        slider_row.setSpacing(6)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(int(self.value))
        self._slider.setStyleSheet(
            _SLIDER_STYLE.format(accent=_ACCENT, accent_light=_ACCENT_LIGHT))
        self._slider.valueChanged.connect(self._on_slider_changed)

        self._pct_lbl = QLabel(f"{int(self.value)}%")
        self._pct_lbl.setFixedWidth(34)
        self._pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._pct_lbl.setStyleSheet(
            "color:#80ccff; font-size:9pt; font-weight:bold;")

        slider_row.addWidget(self._slider, stretch=1)
        slider_row.addWidget(self._pct_lbl)
        root.addLayout(slider_row)

        self.setLayout(root)

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_slider_changed(self, int_val: int):
        self.value = float(int_val)
        self._pct_lbl.setText(f"{int_val}%")
        self.valueChanged.emit(self.value)

    # ── Public API (backward-compatible) ──────────────────────────────────────

    def set_value(self, value: float):
        """Update slider position from simulator (does NOT emit valueChanged)."""
        self.value = max(0.0, min(100.0, float(value)))
        self._slider.blockSignals(True)
        self._slider.setValue(int(round(self.value)))
        self._slider.blockSignals(False)
        self._pct_lbl.setText(f"{int(round(self.value))}%")

    def get_value(self) -> float:
        return self.value

    def set_process_temp(self, temp: float):
        """Display the live process temperature reported by the simulator."""
        self._proc_lbl.setText(f"{temp:.1f}°C")

    def set_temp_range(self, t_min: float, t_max: float):
        self.temp_range = (t_min, t_max)
        self._range_lbl.setText(f"{t_min}°C – {t_max}°C")
