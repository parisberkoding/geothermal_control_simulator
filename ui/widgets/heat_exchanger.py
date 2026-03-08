"""
Heat Exchanger Widget
Custom P&ID-symbol widget for a geothermal heat exchanger (HX).

Standard P&ID HX symbol: a rectangle with two diagonal crossing lines (X).

Each widget shows:
  – ISA HX symbol (rectangle + X)
  – HX tag (e.g. HX-01)
  – Inlet temperature (hot side, geothermal fluid)
  – Outlet temperature (hot side)
  – Secondary-side outlet temperature (process side, computed from setpoint)
  – Flow control valve position indicator (coloured ring)
  – Status indicator dot
  – Heat duty (kW) and efficiency (%) readout

Call  update_data(sensor_dict, valve_pos, scheme_id)  to refresh live data.
Call  apply_theme(theme_dict)  when the scheme changes.
"""
from __future__ import annotations
import math
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush,
                          QFont, QPainterPath, QLinearGradient)

# ── colour helpers (reused from other widgets) ─────────────────────────────────

def _temp_color(temp: float) -> QColor:
    t = max(0.0, min(1.0, (float(temp) - 24.0) / (170.0 - 24.0)))
    if t >= 0.66:
        k = (t - 0.66) / 0.34
        return QColor(220, int(50 + 50 * (1 - k)), 30)
    elif t >= 0.33:
        k = (t - 0.33) / 0.33
        return QColor(int(220 * k), int(180 - 80 * k), 30)
    else:
        k = t / 0.33
        return QColor(30, int(180 * k + 20), int(200 * (1 - k) + 20))


def _valve_color(pos: float) -> QColor:
    if pos < 20:
        return QColor(255, 70, 70)
    if pos < 50:
        return QColor(255, 195, 0)
    return QColor(0, 215, 110)


def _status_color(status_str: str) -> QColor:
    s = str(status_str).lower()
    if 'normal' in s:
        return QColor(0, 220, 120)
    if 'critical' in s:
        return QColor(255, 60, 60)
    return QColor(255, 200, 0)


# ── HeatExchangerWidget ────────────────────────────────────────────────────────

class HeatExchangerWidget(QWidget):
    """
    Custom-painted P&ID heat exchanger symbol with live data overlay.

    The design canvas is 200 × 180 px (logical), scaled to fit the actual
    widget size while keeping the aspect ratio.

    Layout (logical coords):
    ┌──────────────────────────────────────────────────┐
    │  [TI-in]──→──[══╔═══╗══]──→──[TI-out]           │
    │               ║  X  ║   ← HX symbol (rectangle+X)│
    │  [FCV valve]──╚═══╝──[Secondary side outlet]     │
    │  Heat: xxx kW   Eff: xx%   Status badge           │
    └──────────────────────────────────────────────────┘
    """

    _DW = 200
    _DH = 160

    def __init__(self, hx_tag: str = 'HX-01',
                 unit_name: str = 'Heat Exchanger', parent=None):
        super().__init__(parent)
        self.hx_tag    = hx_tag
        self.unit_name = unit_name

        # Live data
        self._inlet_temp:    float = 100.0
        self._outlet_temp:   float = 40.0
        self._process_temp:  float = 35.0   # secondary-side outlet
        self._valve_pos:     float = 50.0
        self._heat_kw:       float = 0.0
        self._efficiency:    float = 0.0
        self._status:        str   = 'Normal'
        self._scheme:        str   = 'scada'
        self._anim:          int   = 0

        # Theme colours (updated by apply_theme)
        self._bg       = QColor(14, 22, 38)
        self._border   = QColor(60, 100, 160)
        self._text_c   = QColor(160, 200, 240)
        self._val_c    = QColor(0, 220, 255)

        self.setMinimumSize(160, 130)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # ── public API ─────────────────────────────────────────────────────────────

    def update_data(self, sensor: dict, valve_pos: float,
                    scheme_id: str = 'scada') -> None:
        self._inlet_temp   = sensor.get('inlet_temp',   0.0)
        self._outlet_temp  = sensor.get('outlet_temp',  0.0)
        self._process_temp = sensor.get('process_temp', self._outlet_temp * 0.8)
        self._heat_kw      = sensor.get('heat_duty_kw', 0.0)
        self._efficiency   = sensor.get('efficiency',   0.0)
        self._status       = sensor.get('status',       'Normal')
        self._valve_pos    = valve_pos
        self._scheme       = scheme_id
        self._anim         = (self._anim + 1) % 40
        self.update()

    def apply_theme(self, theme: dict) -> None:
        self._bg     = QColor(theme.get('bg_widget',  '#0e1626'))
        self._border = QColor(theme.get('border_main','#3c6480'))
        self._text_c = QColor(theme.get('text_primary','#a0c8f0'))
        self._val_c  = QColor(theme.get('text_value',  '#00dcff'))
        self.update()

    # ── painting ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Scale to design canvas
        scale  = min(w / self._DW, h / self._DH)
        ox     = (w - self._DW * scale) / 2.0
        oy     = (h - self._DH * scale) / 2.0

        p.fillRect(0, 0, w, h, self._bg)

        p.save()
        p.translate(ox, oy)
        p.scale(scale, scale)

        self._draw_pid_symbol(p)
        self._draw_instruments(p)
        self._draw_data_strip(p)

        p.restore()

    # ── P&ID symbol ────────────────────────────────────────────────────────────

    def _draw_pid_symbol(self, p: QPainter) -> None:
        """Draw the standard ISA heat exchanger symbol (rectangle + X)."""
        hx_x, hx_y = 65, 40
        hx_w, hx_h = 70, 55

        # Inlet pipe (hot side, left)
        hot_c = _temp_color(self._inlet_temp)
        p.setPen(QPen(hot_c, 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(0, hx_y + hx_h // 2, hx_x, hx_y + hx_h // 2)

        # Outlet pipe (hot side, right)
        out_c = _temp_color(self._outlet_temp)
        p.setPen(QPen(out_c, 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(hx_x + hx_w, hx_y + hx_h // 2,
                   self._DW, hx_y + hx_h // 2)

        # HX box
        status_c = _status_color(self._status)
        p.setPen(QPen(self._border, 2))
        p.setBrush(QBrush(QColor(20, 32, 52)))
        p.drawRect(hx_x, hx_y, hx_w, hx_h)

        # Diagonal X inside box
        p.setPen(QPen(QColor(100, 150, 200), 1.5))
        p.drawLine(hx_x + 4, hx_y + 4, hx_x + hx_w - 4, hx_y + hx_h - 4)
        p.drawLine(hx_x + hx_w - 4, hx_y + 4, hx_x + 4, hx_y + hx_h - 4)

        # HX tag label
        p.setPen(self._text_c)
        p.setFont(QFont('Arial', 7, QFont.Bold))
        p.drawText(QRectF(hx_x, hx_y + hx_h // 2 - 7, hx_w, 14),
                   Qt.AlignCenter, self.hx_tag)

        # Secondary (process) side — vertical pipe from bottom of HX
        sec_c = _temp_color(self._process_temp)
        p.setPen(QPen(sec_c, 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(hx_x + hx_w // 2, hx_y + hx_h,
                   hx_x + hx_w // 2, hx_y + hx_h + 25)

        # Animated flow dots on hot-side inlet pipe
        dot_c = _temp_color(self._inlet_temp)
        p.setBrush(QBrush(dot_c))
        p.setPen(Qt.NoPen)
        dot_offset = (self._anim * 4) % (hx_x - 10)
        p.drawEllipse(QPointF(dot_offset + 5, hx_y + hx_h // 2), 3, 3)

        # Status dot
        p.setBrush(QBrush(status_c))
        p.setPen(QPen(QColor(0, 0, 0, 50), 1))
        p.drawEllipse(hx_x + hx_w - 10, hx_y + 4, 8, 8)

    def _draw_instruments(self, p: QPainter) -> None:
        """Draw ISA instrument circles for TI-in, TI-out, and FCV valve."""
        hx_y = 40
        hx_h = 55
        mid_y = hx_y + hx_h // 2

        def _isa_bubble(cx, cy, tag, val_str, color):
            r = 12
            p.setPen(QPen(color, 1.5))
            p.setBrush(QBrush(QColor(14, 22, 38)))
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            # bisector
            p.drawLine(cx - r, cy, cx + r, cy)
            p.setFont(QFont('Arial', 5, QFont.Bold))
            p.setPen(color)
            p.drawText(QRectF(cx - r, cy - r, r * 2, r), Qt.AlignCenter, tag)
            p.setFont(QFont('Arial', 4))
            p.drawText(QRectF(cx - r, cy, r * 2, r), Qt.AlignCenter, val_str)

        # TI-in (left side)
        ti_in_c = _temp_color(self._inlet_temp)
        _isa_bubble(20, mid_y - 22, 'TI',
                    f'{self._inlet_temp:.0f}°', ti_in_c)
        p.setPen(QPen(ti_in_c, 1))
        p.drawLine(20, mid_y - 10, 20, mid_y)

        # TI-out (right side)
        ti_out_c = _temp_color(self._outlet_temp)
        _isa_bubble(self._DW - 20, mid_y - 22, 'TI',
                    f'{self._outlet_temp:.0f}°', ti_out_c)
        p.setPen(QPen(ti_out_c, 1))
        p.drawLine(self._DW - 20, mid_y - 10, self._DW - 20, mid_y)

        # FCV (Flow Control Valve) on inlet pipe
        fcv_x = 42
        fcv_y = mid_y
        vc = _valve_color(self._valve_pos)
        # Two triangles = valve symbol
        vpath = QPainterPath()
        vpath.moveTo(fcv_x - 7, fcv_y - 7)
        vpath.lineTo(fcv_x + 7, fcv_y)
        vpath.lineTo(fcv_x - 7, fcv_y + 7)
        vpath.closeSubpath()
        vpath2 = QPainterPath()
        vpath2.moveTo(fcv_x + 7, fcv_y - 7)
        vpath2.lineTo(fcv_x - 7, fcv_y)
        vpath2.lineTo(fcv_x + 7, fcv_y + 7)
        vpath2.closeSubpath()
        p.setPen(QPen(vc, 1))
        p.setBrush(QBrush(vc.darker(180)))
        p.drawPath(vpath)
        p.drawPath(vpath2)
        # Actuator
        p.setPen(QPen(vc, 1.5))
        p.drawLine(fcv_x, fcv_y - 8, fcv_x, fcv_y - 18)
        p.setBrush(QBrush(vc.darker(200)))
        p.drawEllipse(fcv_x - 6, fcv_y - 24, 12, 7)
        p.setPen(vc)
        p.setFont(QFont('Arial', 4))
        p.drawText(QRectF(fcv_x - 12, fcv_y - 38, 24, 12),
                   Qt.AlignCenter, f'{self._valve_pos:.0f}%')

    def _draw_data_strip(self, p: QPainter) -> None:
        """Heat duty / efficiency / unit name text at bottom."""
        y0 = self._DH - 30
        p.fillRect(0, y0, self._DW, 30, QColor(0, 0, 0, 80))

        p.setPen(self._text_c)
        p.setFont(QFont('Arial', 6, QFont.Bold))
        p.drawText(QRectF(4, y0 + 2, self._DW - 8, 12),
                   Qt.AlignLeft | Qt.AlignVCenter, self.unit_name)

        p.setPen(QColor(255, 165, 40))
        p.setFont(QFont('Courier New', 7, QFont.Bold))
        p.drawText(QRectF(4, y0 + 14, self._DW // 2 - 4, 12),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   f'{self._heat_kw:.0f} kW')

        p.setPen(QColor(100, 185, 255))
        p.drawText(QRectF(self._DW // 2, y0 + 14, self._DW // 2 - 4, 12),
                   Qt.AlignRight | Qt.AlignVCenter,
                   f'η={self._efficiency:.1f}%')


# ── Factory ────────────────────────────────────────────────────────────────────

def make_hx_widget(hx_tag: str, unit_name: str, parent=None) -> HeatExchangerWidget:
    """Return a configured HeatExchangerWidget."""
    return HeatExchangerWidget(hx_tag=hx_tag, unit_name=unit_name, parent=parent)
