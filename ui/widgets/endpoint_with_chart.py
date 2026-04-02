"""
Endpoint view wrapper — P&ID view + UnitAnalyticsChart dalam satu panel vertikal.
Digunakan di Tab 2 (Endpoint P&IDs) sebagai pengganti bare endpoint view.
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PyQt5.QtCore import Qt

from ui.endpoint_views import make_endpoint_view
from ui.widgets.unit_analytics_chart import UnitAnalyticsChart


class EndpointWithChart(QWidget):
    """
    Wrapper yang menggabungkan:
      atas  : endpoint P&ID view (make_endpoint_view)
      bawah : UnitAnalyticsChart (trend charts per unit)
    """

    def __init__(self, sid: str, display_name: str, parent=None):
        super().__init__(parent)
        self.sid          = sid
        self._pid_view    = make_endpoint_view(sid)
        self._chart       = UnitAnalyticsChart(sid, display_name)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._pid_view)
        splitter.addWidget(self._chart)
        splitter.setSizes([320, 400])          # P&ID lebih kecil, chart lebih besar
        splitter.setChildrenCollapsible(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(splitter)
        self.setLayout(layout)

    # ── Proxy methods ──────────────────────────────────────────────────────────

    def update_data(self, ep_data: dict, valve_pos: float = 0.0) -> None:
        """Called every UI tick from MainWindow._update_ui."""
        # Update P&ID view
        self._pid_view.update_data(ep_data)

        # Update analytics chart
        self._chart.add_data_point(
            inlet_temp    = ep_data.get('inlet_temp',    0.0),
            outlet_temp   = ep_data.get('outlet_temp',   0.0),
            heat_kw       = ep_data.get('heat_duty_kw',  0.0),
            flow_kg_h     = ep_data.get('flow_rate_kg_h',0.0),
            pressure_drop = ep_data.get('pressure_drop', 0.0),
            efficiency    = ep_data.get('efficiency',    0.0),
            valve_pos     = valve_pos,
        )