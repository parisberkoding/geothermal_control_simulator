"""
Unit Icon Widgets
Visually distinct custom-painted widgets for each of the 6 direct-use units.
Each widget exposes:
    update_data(sensor_dict, valve_pos, scheme_id)
    apply_theme(theme_dict)

Units
-----
  TeaDryingIcon     – drying room with racks + hot-air flow
  GreenhouseIcon    – glass building with plant silhouettes
  FoodDehydIcon     – box with trays + fan symbol
  CabinIcon         – room outline with furniture silhouettes
  HotPoolIcon       – oval pool with steam ripples
  FishPondIcon      – round pond with fish symbols
"""
from __future__ import annotations
import math
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush, QFont,
                          QPainterPath, QLinearGradient, QRadialGradient)


# ── helpers ────────────────────────────────────────────────────────────────────

def _temp_color(temp: float) -> QColor:
    t = max(0.0, min(1.0, (float(temp) - 24) / (170 - 24)))
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


# ── Base class ─────────────────────────────────────────────────────────────────

class _UnitIconBase(QWidget):
    """Base painted widget for a direct-use unit."""

    # Override in subclasses
    _BG_COLOR:   QColor = QColor(22, 28, 42)
    _BORDER_CLR: QColor = QColor(60, 90, 140)
    _TITLE_CLR:  QColor = QColor(180, 210, 255)
    _TITLE:      str    = 'Unit'
    _SUBTITLE:   str    = ''

    def __init__(self, parent=None):
        super().__init__(parent)
        self._inlet_temp:  float = 0.0
        self._outlet_temp: float = 0.0
        self._valve_pos:   float = 50.0
        self._heat_kw:     float = 0.0
        self._efficiency:  float = 0.0
        self._status:      str   = '—'
        self._scheme:      str   = 'scada'
        self._anim:        int   = 0

        self.setMinimumSize(160, 140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # ── public API ────────────────────────────────────────────────────────────

    def update_data(self, sensor: dict, valve_pos: float, scheme_id: str = 'scada') -> None:
        self._inlet_temp  = sensor.get('inlet_temp',    0.0)
        self._outlet_temp = sensor.get('outlet_temp',   0.0)
        self._heat_kw     = sensor.get('heat_duty_kw',  0.0)
        self._efficiency  = sensor.get('efficiency',    0.0)
        self._status      = sensor.get('status',        '—')
        self._valve_pos   = valve_pos
        self._scheme      = scheme_id
        self._anim        = (self._anim + 1) % 30
        self.update()

    def apply_theme(self, theme: dict) -> None:
        self.update()

    # ── painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        p.fillRect(0, 0, w, h, self._BG_COLOR)

        # Status border
        status_c = _status_color(self._status)
        p.setPen(QPen(status_c, 2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)

        # Title strip
        p.fillRect(2, 2, w - 4, 20, QColor(0, 0, 0, 80))
        p.setPen(self._TITLE_CLR)
        p.setFont(QFont('Arial', 8, QFont.Bold))
        p.drawText(QRectF(4, 2, w - 8, 18), Qt.AlignLeft | Qt.AlignVCenter, self._TITLE)

        # Status dot
        p.setBrush(QBrush(status_c))
        p.setPen(Qt.NoPen)
        p.drawEllipse(w - 14, 6, 8, 8)

        # Custom graphic (override in subclass)
        self._draw_unit(p, 2, 24, w - 4, h - 58)

        # Data readout strip at bottom
        self._draw_data_strip(p, w, h)

    def _draw_unit(self, p: QPainter, x: int, y: int, w: int, h: int) -> None:
        """Override in subclasses to draw the unit graphic."""
        pass

    def _draw_data_strip(self, p: QPainter, w: int, h: int) -> None:
        y0 = h - 54
        p.fillRect(2, y0, w - 4, 52, QColor(0, 0, 0, 100))

        # Valve indicator bar
        bar_w = int((w - 16) * self._valve_pos / 100.0)
        vc = _valve_color(self._valve_pos)
        p.fillRect(8, y0 + 2, w - 16, 6, QColor(30, 30, 30))
        p.fillRect(8, y0 + 2, max(0, bar_w), 6, vc)
        p.setPen(vc)
        p.setFont(QFont('Arial', 7))
        p.drawText(QRectF(4, y0, w - 8, 14), Qt.AlignRight | Qt.AlignVCenter,
                   f'V:{self._valve_pos:.0f}%')

        # Temperatures
        p.setPen(QColor(255, 200, 80))
        p.setFont(QFont('Courier New', 8, QFont.Bold))
        tin  = f'{self._inlet_temp:.0f}°C'
        tout = f'{self._outlet_temp:.0f}°C'
        p.drawText(QRectF(4, y0 + 12, w - 8, 14), Qt.AlignLeft | Qt.AlignVCenter,
                   f'IN: {tin}')
        p.setPen(QColor(80, 200, 255))
        p.drawText(QRectF(4, y0 + 24, w - 8, 14), Qt.AlignLeft | Qt.AlignVCenter,
                   f'OUT:{tout}')

        # Heat & efficiency
        p.setPen(QColor(255, 160, 40))
        p.setFont(QFont('Arial', 7))
        p.drawText(QRectF(4, y0 + 36, (w - 8) // 2, 14),
                   Qt.AlignLeft | Qt.AlignVCenter, f'{self._heat_kw:.0f} kW')
        p.setPen(QColor(100, 180, 255))
        p.drawText(QRectF(w // 2, y0 + 36, (w - 8) // 2, 14),
                   Qt.AlignRight | Qt.AlignVCenter, f'η={self._efficiency:.0f}%')


# ── Tea Drying ─────────────────────────────────────────────────────────────────

class TeaDryingIcon(_UnitIconBase):
    """Drying room with racks and hot-air flow arrows."""

    _BG_COLOR   = QColor(28, 18, 8)
    _BORDER_CLR = QColor(120, 80, 40)
    _TITLE_CLR  = QColor(240, 200, 120)
    _TITLE      = 'Tea Drying  (HX-03)'
    _SUBTITLE   = '50 – 70°C'

    def _draw_unit(self, p, x, y, w, h):
        cx = x + w // 2
        # Room outline
        p.setPen(QPen(QColor(150, 100, 50), 2))
        p.setBrush(QColor(38, 22, 10))
        p.drawRect(x + 8, y + 2, w - 16, h - 4)

        # Racks (3 shelves)
        shelf_c = QColor(140, 90, 40)
        rack_x  = x + 16
        rack_w  = w - 32
        for i in range(3):
            sy = y + 8 + i * (h - 12) // 3
            p.setPen(QPen(shelf_c, 2))
            p.drawLine(rack_x, sy, rack_x + rack_w, sy)
            # Tea leaves (small ellipses on each shelf)
            leaf_c = QColor(60, 100, 30)
            p.setBrush(QBrush(leaf_c))
            p.setPen(Qt.NoPen)
            for j in range(4):
                lx = rack_x + 4 + j * (rack_w - 8) // 4
                p.drawEllipse(lx, sy - 6, 12, 5)

        # Hot-air flow arrows (animated)
        arrow_y = y + h - 8
        arrow_c = _temp_color(self._inlet_temp)
        p.setPen(QPen(arrow_c, 2))
        offset  = (self._anim % 10) * 2
        for i in range(3):
            ax = x + 20 + i * (w // 3) + offset % 10
            ax = min(ax, x + w - 20)
            p.drawLine(ax, arrow_y, ax, arrow_y - 10)
            p.drawLine(ax, arrow_y - 10, ax - 4, arrow_y - 5)
            p.drawLine(ax, arrow_y - 10, ax + 4, arrow_y - 5)


# ── Greenhouse ─────────────────────────────────────────────────────────────────

class GreenhouseIcon(_UnitIconBase):
    """Glass-roof greenhouse with plant silhouettes."""

    _BG_COLOR   = QColor(8, 22, 10)
    _BORDER_CLR = QColor(40, 140, 60)
    _TITLE_CLR  = QColor(140, 240, 140)
    _TITLE      = 'Greenhouse  (HX-07)'
    _SUBTITLE   = '25 – 30°C  RH 70-80%'

    def _draw_unit(self, p, x, y, w, h):
        # Glass walls
        wall_c = QColor(50, 180, 60, 80)
        p.setBrush(QBrush(wall_c))
        p.setPen(QPen(QColor(80, 200, 90), 1))
        p.drawRect(x + 8, y + h // 2, w - 16, h // 2 - 2)

        # Peaked roof
        roof_path = QPainterPath()
        roof_path.moveTo(x + 8, y + h // 2)
        roof_path.lineTo(x + w // 2, y + 4)
        roof_path.lineTo(x + w - 8, y + h // 2)
        roof_path.closeSubpath()
        p.setBrush(QBrush(QColor(40, 160, 50, 80)))
        p.setPen(QPen(QColor(80, 200, 90), 1))
        p.drawPath(roof_path)

        # Plants (simple triangles)
        plant_c = QColor(30, 140, 40)
        p.setBrush(QBrush(plant_c))
        p.setPen(Qt.NoPen)
        for i in range(4):
            px = x + 18 + i * (w - 32) // 4
            py = y + h - 4
            # Stem
            p.setPen(QPen(QColor(80, 60, 20), 2))
            p.drawLine(px + 6, py, px + 6, py - 10)
            # Leaves
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(plant_c))
            leaf = QPainterPath()
            leaf.moveTo(px + 6, py - 10)
            leaf.lineTo(px, py - 22)
            leaf.lineTo(px + 12, py - 22)
            leaf.closeSubpath()
            p.drawPath(leaf)

        # Humidity indicator dots (animated)
        if self._anim % 5 == 0:
            drop_c = QColor(100, 200, 255, 180)
            p.setBrush(QBrush(drop_c))
            p.setPen(Qt.NoPen)
            for i in range(3):
                dx = x + 30 + i * (w // 4)
                dy = y + 8 + (self._anim // 2) % (h // 2 - 16)
                p.drawEllipse(dx, dy, 3, 4)


# ── Food Dehydrator ────────────────────────────────────────────────────────────

class FoodDehydIcon(_UnitIconBase):
    """Box unit with trays and a fan symbol."""

    _BG_COLOR   = QColor(28, 14, 4)
    _BORDER_CLR = QColor(200, 100, 30)
    _TITLE_CLR  = QColor(255, 180, 80)
    _TITLE      = 'Food Dehydrator  (HX-04)'
    _SUBTITLE   = '40 – 60°C'

    def _draw_unit(self, p, x, y, w, h):
        # Outer box
        p.setPen(QPen(QColor(180, 90, 30), 2))
        p.setBrush(QColor(38, 20, 8))
        p.drawRect(x + 8, y + 2, w - 16, h - 4)

        # Trays
        tray_c = QColor(180, 130, 60)
        for i in range(4):
            ty = y + 6 + i * (h - 12) // 4
            p.setPen(QPen(tray_c, 1))
            p.drawRect(x + 14, ty, w - 28, (h - 12) // 4 - 2)
            # Food items on tray (small circles)
            p.setBrush(QBrush(QColor(200, 150, 80)))
            p.setPen(Qt.NoPen)
            for j in range(5):
                fx = x + 18 + j * (w - 36) // 5
                p.drawEllipse(fx, ty + 2, 6, 5)

        # Fan symbol (right side, animated rotation)
        fan_cx = x + w - 14
        fan_cy = y + h // 2
        p.setPen(QPen(QColor(255, 180, 60), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(fan_cx - 8, fan_cy - 8, 16, 16)
        # Blades
        for b in range(4):
            angle = math.radians(b * 90 + self._anim * 12)
            bx1 = fan_cx + int(3 * math.cos(angle))
            by1 = fan_cy + int(3 * math.sin(angle))
            bx2 = fan_cx + int(7 * math.cos(angle + 0.8))
            by2 = fan_cy + int(7 * math.sin(angle + 0.8))
            p.setPen(QPen(QColor(255, 180, 60), 2))
            p.drawLine(bx1, by1, bx2, by2)


# ── Cabin ─────────────────────────────────────────────────────────────────────

class CabinIcon(_UnitIconBase):
    """Small room silhouette with furniture outlines."""

    _BG_COLOR   = QColor(22, 18, 8)
    _BORDER_CLR = QColor(160, 140, 60)
    _TITLE_CLR  = QColor(255, 230, 140)
    _TITLE      = 'Cabin Heating  (HX-01)'
    _SUBTITLE   = '30 – 35°C'

    def _draw_unit(self, p, x, y, w, h):
        # Floor
        p.setPen(QPen(QColor(120, 100, 50), 2))
        p.setBrush(QColor(35, 28, 12))
        p.drawRect(x + 8, y + 4, w - 16, h - 8)

        # Window (glowing warm light)
        win_grad = QLinearGradient(x + 20, y + 8, x + 48, y + 28)
        win_grad.setColorAt(0, QColor(255, 220, 80, 160))
        win_grad.setColorAt(1, QColor(255, 160, 40, 60))
        p.setBrush(QBrush(win_grad))
        p.setPen(QPen(QColor(200, 180, 80), 1))
        p.drawRect(x + 20, y + 8, 28, 20)

        # Chair silhouette
        p.setPen(QPen(QColor(140, 110, 50), 2))
        p.setBrush(QColor(80, 60, 25))
        cx2 = x + w - 28
        cy2 = y + h - 20
        p.drawRect(cx2, cy2 - 14, 18, 12)     # seat
        p.drawRect(cx2, cy2 - 26, 4, 12)      # back left
        p.drawRect(cx2 + 14, cy2 - 26, 4, 12) # back right

        # Radiator (heat ripples)
        rad_x = x + 14
        rad_y = y + h // 2
        p.setPen(QPen(QColor(180, 80, 30), 2))
        for i in range(4):
            rx = rad_x + i * 6
            p.drawLine(rx, rad_y, rx, rad_y - 18)

        # Warm air lines (animated)
        air_c = _temp_color(self._outlet_temp)
        p.setPen(QPen(air_c, 1))
        for i in range(3):
            ay = rad_y - 22 - i * 6
            offset = (self._anim + i * 3) % 20
            p.drawLine(rad_x + offset % 10, ay, rad_x + 20 + offset % 10, ay)


# ── Hot Pool ──────────────────────────────────────────────────────────────────

class HotPoolIcon(_UnitIconBase):
    """Oval pool with animated steam/ripple lines."""

    _BG_COLOR   = QColor(4, 16, 30)
    _BORDER_CLR = QColor(40, 130, 200)
    _TITLE_CLR  = QColor(120, 200, 255)
    _TITLE      = 'Hot Pool  (HX-02)'
    _SUBTITLE   = '38 – 42°C'

    def _draw_unit(self, p, x, y, w, h):
        cx = x + w // 2
        cy = y + h // 2

        # Pool (radial gradient for depth effect)
        grad = QRadialGradient(cx, cy, max(w, h) // 2)
        grad.setColorAt(0.0, QColor(60, 160, 220, 200))
        grad.setColorAt(0.5, QColor(30, 100, 170, 180))
        grad.setColorAt(1.0, QColor(10, 50, 100, 220))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(80, 170, 240), 2))
        pool_w = w - 20
        pool_h = h - 16
        p.drawEllipse(x + 10, y + 8, pool_w, pool_h)

        # Water ripples (animated concentric ellipses)
        ripple_c = QColor(180, 230, 255, 120)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(ripple_c, 1))
        for i in range(3):
            phase = (self._anim + i * 10) % 30
            rw = 20 + phase * 2
            rh = 10 + phase
            if rw < pool_w - 4 and rh < pool_h - 4:
                p.drawEllipse(cx - rw // 2, cy - rh // 2, rw, rh)

        # Steam wisps (rising, animated)
        steam_c = QColor(200, 230, 255, 100)
        p.setPen(QPen(steam_c, 2))
        for i in range(5):
            sx  = x + 18 + i * (w - 36) // 5
            sy0 = y + 6
            phase = (self._anim + i * 4) % 20
            p.drawLine(sx, sy0 - phase % 10, sx + 2, sy0 - phase % 10 - 6)
            p.drawLine(sx + 2, sy0 - phase % 10 - 6, sx - 2, sy0 - phase % 10 - 12)

        # Temperature label in pool
        p.setPen(QColor(220, 240, 255))
        p.setFont(QFont('Arial', 9, QFont.Bold))
        p.drawText(QRectF(x + 4, y + 4, w - 8, h - 8),
                   Qt.AlignCenter, f'{self._outlet_temp:.0f}°C')


# ── Fish Pond ─────────────────────────────────────────────────────────────────

class FishPondIcon(_UnitIconBase):
    """Round pond with animated fish silhouettes."""

    _BG_COLOR   = QColor(4, 12, 22)
    _BORDER_CLR = QColor(30, 90, 160)
    _TITLE_CLR  = QColor(100, 180, 255)
    _TITLE      = 'Fish Pond  (HX-05)'
    _SUBTITLE   = '28 – 30°C  Tilapia / Carp'

    # Static fish positions (cx offset fraction, cy offset fraction, direction)
    _FISH: list[tuple] = [
        (0.25, 0.35, 1), (0.60, 0.55, -1), (0.40, 0.70, 1),
        (0.75, 0.30, -1), (0.15, 0.65, 1),
    ]

    def _draw_unit(self, p, x, y, w, h):
        cx = x + w // 2
        cy = y + h // 2
        pr = min(w, h) // 2 - 6

        # Water fill
        grad = QRadialGradient(cx, cy, pr)
        grad.setColorAt(0.0, QColor(20, 80, 140, 200))
        grad.setColorAt(0.7, QColor(10, 50, 100, 200))
        grad.setColorAt(1.0, QColor(5, 25, 60, 220))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(50, 120, 200), 2))
        p.drawEllipse(cx - pr, cy - pr, pr * 2, pr * 2)

        # Ripples
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(100, 180, 255, 80), 1))
        for i in range(2):
            phase = (self._anim + i * 12) % 24
            rr = 8 + phase * 2
            if rr < pr - 2:
                p.drawEllipse(cx - rr, cy - rr, rr * 2, rr * 2)

        # Fish silhouettes (animated movement)
        fish_c = QColor(200, 170, 60)
        p.setBrush(QBrush(fish_c))
        p.setPen(Qt.NoPen)
        for (fx_frac, fy_frac, direction) in self._FISH:
            swim_offset = ((self._anim * direction * 2) % 30) - 15
            fx = x + int(fx_frac * w) + swim_offset
            fy = y + int(fy_frac * h)
            # Keep inside pond ellipse (approximate)
            dx, dy = fx - cx, fy - cy
            if dx * dx + dy * dy > (pr - 8) ** 2:
                continue
            # Fish body (small ellipse)
            p.setBrush(QBrush(fish_c))
            p.drawEllipse(fx - 7, fy - 3, 14, 6)
            # Tail
            tail = QPainterPath()
            tail_x = fx + direction * 7
            tail.moveTo(tail_x, fy)
            tail.lineTo(tail_x + direction * 6, fy - 4)
            tail.lineTo(tail_x + direction * 6, fy + 4)
            tail.closeSubpath()
            p.drawPath(tail)

        # Temperature label
        p.setPen(QColor(180, 220, 255))
        p.setFont(QFont('Arial', 8, QFont.Bold))
        p.drawText(QRectF(x + 4, y + 4, w - 8, 16),
                   Qt.AlignCenter, f'{self._outlet_temp:.0f}°C')


# ── Factory function ───────────────────────────────────────────────────────────

def make_unit_icon(unit_id: str, parent=None) -> _UnitIconBase:
    """Return the appropriate unit icon widget for the given unit ID."""
    _MAP = {
        'cabin':             CabinIcon,
        'hot_pool':          HotPoolIcon,
        'tea_dryer':         TeaDryingIcon,
        'food_dehydrator_1': FoodDehydIcon,
        'fish_pond':         FishPondIcon,
        'food_dehydrator_2': FoodDehydIcon,   # reuse with different tag
        'green_house':       GreenhouseIcon,
    }
    cls = _MAP.get(unit_id, _UnitIconBase)
    widget = cls(parent)
    # Patch title for food_dehydrator_2
    if unit_id == 'food_dehydrator_2':
        widget._TITLE = 'Food Dehydrator 2  (HX-06)'
    return widget
