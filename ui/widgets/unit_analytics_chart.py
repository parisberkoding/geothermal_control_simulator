"""
Unit Analytics Chart
Per-unit mini trend chart menampilkan:
  - T inlet dan T outlet (dual line)
  - Heat duty (kW)
  - Flow rate (kg/h)
  - Pressure drop (bar)
  - Efficiency (%)
"""
from __future__ import annotations
import time
from collections import deque
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PyQt5.QtCore import Qt
import pyqtgraph as pg


class UnitAnalyticsChart(QWidget):
    """Mini analytics panel per unit direct use."""

    WINDOW_S = 120   # tampilkan 120 detik terakhir
    MAXLEN   = 1500

    def __init__(self, unit_id: str, display_name: str, parent=None):
        super().__init__(parent)
        self.unit_id      = unit_id
        self.display_name = display_name
        self._t0          = time.time()

        # Data buffers
        self._ts      = deque(maxlen=self.MAXLEN)
        self._t_in    = deque(maxlen=self.MAXLEN)
        self._t_out   = deque(maxlen=self.MAXLEN)
        self._heat    = deque(maxlen=self.MAXLEN)
        self._flow    = deque(maxlen=self.MAXLEN)
        self._dp      = deque(maxlen=self.MAXLEN)
        self._eff     = deque(maxlen=self.MAXLEN)
        self._valve   = deque(maxlen=self.MAXLEN)

        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(2)

        # Header
        hdr = QLabel(self.display_name)
        hdr.setStyleSheet(
            "color:#8ab0cc; font-size:8pt; font-weight:bold; "
            "background:#0a1220; padding:2px 4px;")
        root.addWidget(hdr)

        # Live value readout strip
        self._readout = QLabel("T-in: -- | T-out: -- | Q: -- kW | F: -- kg/h | dP: -- bar | n: --")
        self._readout.setStyleSheet(
            "color:#aaaacc; font-size:7pt; font-family:'Courier New'; "
            "background:#080e18; padding:2px 4px;")
        root.addWidget(self._readout)

        # Charts grid: 2 baris x 3 kolom
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(2)

        def _make_plot(title, y_label, color):
            pw = pg.PlotWidget()
            pw.setBackground('#080e18')
            pw.showGrid(x=False, y=True, alpha=0.2)
            pw.setLabel('left', y_label,
                        **{'color': '#556677', 'font-size': '7pt'})
            pw.getAxis('bottom').setStyle(showValues=False)
            pw.setMinimumHeight(70)
            pen = pg.mkPen(color=color, width=1.5)
            curve = pw.plot([], [], pen=pen)
            return pw, curve

        self._pw_temp,  self._cv_tin  = _make_plot("Temp", "degC",   (255, 160, 50))
        self._pw_temp2, self._cv_tout = _make_plot("",     "",       (80, 180, 255))
        # Tambahkan outlet ke plot temp yang sama
        pen2 = pg.mkPen(color=(80, 180, 255), width=1.5, style=Qt.DashLine)
        self._cv_tout = self._pw_temp.plot([], [], pen=pen2)

        self._pw_heat, self._cv_heat = _make_plot("Heat", "kW",     (255, 100, 180))
        self._pw_flow, self._cv_flow = _make_plot("Flow", "kg/h",   (100, 210, 255))
        self._pw_dp,   self._cv_dp   = _make_plot("dP",   "bar",    (180, 180, 100))
        self._pw_eff,  self._cv_eff  = _make_plot("Eff",  "%",      (100, 255, 150))

        # Label temp chart
        legend_lbl = QLabel("  -- Tin (orange)   -- Tout (blue-dash)")
        legend_lbl.setStyleSheet("color:#445566; font-size:6pt; background:#080e18;")

        grid.addWidget(legend_lbl,     0, 0, 1, 3)
        grid.addWidget(self._pw_temp,  1, 0)
        grid.addWidget(self._pw_heat,  1, 1)
        grid.addWidget(self._pw_flow,  1, 2)
        grid.addWidget(self._pw_dp,    2, 0)
        grid.addWidget(self._pw_eff,   2, 1)

        # Valve position bar (simple label)
        self._valve_lbl = QLabel("Valve: --%")
        self._valve_lbl.setStyleSheet(
            "color:#668899; font-size:7pt; background:#080e18; padding:2px 4px;")
        grid.addWidget(self._valve_lbl, 2, 2)

        for col in range(3):
            grid.setColumnStretch(col, 1)
        for row in range(1, 3):
            grid.setRowStretch(row, 1)

        root.addLayout(grid)
        self.setLayout(root)

    def add_data_point(self, inlet_temp: float, outlet_temp: float,
                       heat_kw: float, flow_kg_h: float,
                       pressure_drop: float, efficiency: float,
                       valve_pos: float) -> None:
        now = time.time() - self._t0
        self._ts.append(now)
        self._t_in.append(inlet_temp)
        self._t_out.append(outlet_temp)
        self._heat.append(heat_kw)
        self._flow.append(flow_kg_h)
        self._dp.append(pressure_drop)
        self._eff.append(efficiency)
        self._valve.append(valve_pos)

        ts = list(self._ts)
        x_min = ts[-1] - self.WINDOW_S if ts[-1] > self.WINDOW_S else 0

        def _upd(curve, buf):
            curve.setData(ts, list(buf))
            curve.getViewBox().setXRange(x_min, ts[-1], padding=0)

        try:
            _upd(self._cv_tin,  self._t_in)
            _upd(self._cv_tout, self._t_out)
            _upd(self._cv_heat, self._heat)
            _upd(self._cv_flow, self._flow)
            _upd(self._cv_dp,   self._dp)
            _upd(self._cv_eff,  self._eff)
        except Exception:
            pass

        self._readout.setText(
            f"T-in:{inlet_temp:.0f}C | T-out:{outlet_temp:.0f}C | "
            f"Q:{heat_kw:.0f}kW | F:{flow_kg_h:.0f}kg/h | "
            f"dP:{pressure_drop:.4f}bar | n:{efficiency:.1f}%"
        )
        self._valve_lbl.setText(f"Valve: {valve_pos:.0f}%")