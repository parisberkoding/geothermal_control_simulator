"""
Individual Endpoint P&ID Detail Views (HMI Style)
Based on actual P&ID drawings provided by PT Geo Dipa Energy (Persero)

  • TeaDryerView    – P&ID Pengering Daun Teh
  • FishPondView    – P&ID Kolam Ikan
  • HotPoolView     – P&ID Kolam Air Panas  (maps to 'hot_pool' / Kolam Rendam)
  • FoodDehydView   – P&ID Food Dehydrator
  • CabinView       – Cabin Warmer schematic
  • GreenHouseView  – Green House schematic

Each view is a QWidget with a custom paintEvent.
Call  view.update_data(sensor_dict)  to refresh live data.
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
import math


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


# ── base class ─────────────────────────────────────────────────────────────────

class _EndpointBase(QWidget):
    """Base for all endpoint P&ID detail views."""

    # Design canvas size – scene is scaled to fit widget
    _DW = 800
    _DH = 340

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.title    = title
        self.subtitle = subtitle
        self._data    = {}
        self.setMinimumSize(500, 220)

    def update_data(self, data: dict):
        self._data = data
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(12, 16, 26))

        # Scale & translate so design fits widget
        scale = min(w / self._DW, h / self._DH)
        p.save()
        p.translate((w - self._DW * scale) / 2, (h - self._DH * scale) / 2)
        p.scale(scale, scale)
        self._draw_pid(p)
        p.restore()

        # Live data overlay (unscaled, always bottom-right)
        self._draw_data_panel(p, w, h)

    def _draw_pid(self, p: QPainter):
        """Override in subclasses to draw the P&ID."""
        pass

    # ── drawing primitives ─────────────────────────────────────────────────────

    def _pipe(self, p, x1, y1, x2, y2, temp=None, w=5):
        c = _temp_color(temp) if temp is not None else QColor(100, 130, 175)
        p.setPen(QPen(c, w, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(x1, y1, x2, y2)

    def _box(self, p, x, y, w, h, text,
             bg=None, border=None, text_color=None):
        p.setPen(QPen(border or QColor(80, 110, 155), 2))
        p.setBrush(QBrush(bg or QColor(22, 35, 55)))
        p.drawRect(x, y, w, h)
        p.setPen(text_color or QColor(195, 215, 255))
        p.setFont(QFont("Arial", 7, QFont.Bold))
        p.drawText(x + 3, y + 3, w - 6, h - 6,
                   Qt.AlignCenter | Qt.TextWordWrap, text)

    def _circle_eq(self, p, cx, cy, r, text,
                   bg=None, border=None):
        p.setPen(QPen(border or QColor(100, 145, 210), 2))
        p.setBrush(QBrush(bg or QColor(30, 48, 72)))
        p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        p.setPen(border or QColor(150, 185, 255))
        p.setFont(QFont("Arial", 7, QFont.Bold))
        p.drawText(int(cx - r), int(cy - r), int(r * 2), int(r * 2),
                   Qt.AlignCenter | Qt.TextWordWrap, text)

    def _valve(self, p, x, y, pos=70):
        c = _valve_color(pos)
        path = QPainterPath()
        path.moveTo(x - 9, y - 9)
        path.lineTo(x + 9, y)
        path.lineTo(x - 9, y + 9)
        path.closeSubpath()
        p.setPen(QPen(c, 2))
        p.setBrush(QBrush(c))
        p.drawPath(path)
        # Actuator
        p.setPen(QPen(QColor(150, 150, 160), 1.5))
        p.drawLine(x, y - 9, x, y - 20)
        p.drawRect(x - 6, y - 25, 12, 6)

    def _solenoid_valve(self, p, x, y):
        p.setPen(QPen(QColor(220, 170, 60), 2))
        p.setBrush(QBrush(QColor(48, 40, 16)))
        p.drawRect(x - 9, y - 11, 18, 22)
        p.setPen(QColor(255, 210, 80))
        p.setFont(QFont("Arial", 8, QFont.Bold))
        p.drawText(x - 7, y - 7, 14, 16, Qt.AlignCenter, "S")

    def _steam_trap(self, p, x, y):
        r = 10
        p.setPen(QPen(QColor(180, 180, 200), 1.5))
        p.setBrush(QBrush(QColor(38, 43, 62)))
        p.drawEllipse(x - r, y - r, r * 2, r * 2)
        p.setPen(QColor(200, 200, 220))
        p.setFont(QFont("Arial", 6, QFont.Bold))
        p.drawText(x - 8, y - 7, 16, 14, Qt.AlignCenter, "ST")

    def _isa_circle(self, p, x, y, tag, val_str="", color=None):
        c = color or QColor(80, 200, 140)
        r = 14
        p.setPen(QPen(c, 1.5))
        p.setBrush(QBrush(QColor(18, 28, 38)))
        p.drawEllipse(x - r, y - r, r * 2, r * 2)
        p.drawLine(x - r, y, x + r, y)
        p.setPen(c)
        p.setFont(QFont("Arial", 6, QFont.Bold))
        p.drawText(x - 10, y - 13, 20, 12, Qt.AlignCenter, tag)
        p.setFont(QFont("Arial", 5))
        p.drawText(x - 12, y + 1, 24, 11, Qt.AlignCenter, val_str)

    def _heat_exchanger(self, p, x, y, w=80, h=30):
        """Draw a shell-and-tube heat exchanger symbol."""
        # Outer shell
        p.setPen(QPen(QColor(160, 160, 180), 2))
        p.setBrush(QBrush(QColor(28, 38, 55)))
        p.drawRect(x, y, w, h)
        # Inner tubes (wavy lines)
        for i in range(3):
            ty = y + 6 + i * 8
            path = QPainterPath()
            path.moveTo(x + 6, ty)
            for j in range(4):
                dx = (w - 12) / 4
                path.cubicTo(x + 6 + j * dx + dx * 0.3, ty - 5,
                             x + 6 + j * dx + dx * 0.7, ty - 5,
                             x + 6 + (j + 1) * dx, ty)
            p.setPen(QPen(QColor(100, 140, 200), 1.5))
            p.drawPath(path)
        p.setPen(QPen(QColor(160, 160, 180), 2))
        p.drawRect(x, y, w, h)  # redraw border on top

    def _rotary_machine(self, p, x, y, w=110, h=55, label="Rotary Machine"):
        """Draw rotary drum dryer symbol (rectangle + ellipse end cap)."""
        # Main cylinder body
        p.setPen(QPen(QColor(90, 130, 190), 2))
        p.setBrush(QBrush(QColor(25, 40, 65)))
        p.drawRect(x, y, w, h)
        # End cap ellipse
        p.drawEllipse(x + w - 14, y + 2, 12, h - 4)
        # Label
        p.setPen(QColor(170, 205, 255))
        p.setFont(QFont("Arial", 6, QFont.Bold))
        p.drawText(x + 2, y + 2, w - 18, h - 4,
                   Qt.AlignCenter | Qt.TextWordWrap, label)

    def _fan(self, p, cx, cy, r=18):
        """Fan / blower symbol (circle with three blades)."""
        p.setPen(QPen(QColor(110, 160, 225), 2))
        p.setBrush(QBrush(QColor(28, 42, 68)))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        # Blade lines
        for ang in (0, 120, 240):
            rad = math.radians(ang)
            p.drawLine(cx, cy,
                       int(cx + r * 0.8 * math.cos(rad)),
                       int(cy - r * 0.8 * math.sin(rad)))

    def _pump(self, p, cx, cy, r=18):
        """Centrifugal pump symbol (circle + arrow)."""
        p.setPen(QPen(QColor(130, 180, 240), 2))
        p.setBrush(QBrush(QColor(28, 45, 72)))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        # Small arrow inside
        path = QPainterPath()
        path.moveTo(cx - 6, cy)
        path.lineTo(cx + 6, cy)
        path.lineTo(cx + 2, cy - 5)
        path.moveTo(cx + 6, cy)
        path.lineTo(cx + 2, cy + 5)
        p.setPen(QPen(QColor(180, 210, 255), 1.5))
        p.drawPath(path)

    def _filter_box(self, p, x, y, w, h, label="FILTER"):
        p.setPen(QPen(QColor(100, 130, 160), 1.5))
        p.setBrush(QBrush(QColor(22, 32, 48)))
        p.drawRect(x, y, w, h)
        # Cross hatch lines to indicate filter media
        p.setPen(QPen(QColor(70, 95, 125), 1))
        for i in range(1, 4):
            yy = y + i * h // 4
            p.drawLine(x, yy, x + w, yy)
        p.setPen(QColor(140, 170, 200))
        p.setFont(QFont("Arial", 6))
        p.drawText(x + 2, y + 2, w - 4, h - 4,
                   Qt.AlignCenter | Qt.TextWordWrap, label)

    def _draw_pid_title(self, p, title, subtitle=""):
        p.setPen(QColor(175, 210, 255))
        p.setFont(QFont("Arial", 10, QFont.Bold))
        p.drawText(8, 22, title)
        if subtitle:
            p.setPen(QColor(110, 150, 195))
            p.setFont(QFont("Arial", 7))
            p.drawText(8, 36, subtitle)

    def _draw_data_panel(self, p: QPainter, w: int, h: int):
        """Floating live-data panel (bottom-right corner, unscaled)."""
        d = self._data
        t_in  = d.get('inlet_temp', 0)
        t_out = d.get('outlet_temp', 0)
        heat  = d.get('heat_duty_kw', 0)
        eff   = d.get('efficiency', 0)
        stat  = d.get('status', '—')
        color = d.get('color', (0, 200, 80))

        bw, bh = 200, 90
        bx, by = w - bw - 6, h - bh - 6

        p.setBrush(QBrush(QColor(16, 22, 36, 210)))
        p.setPen(QPen(QColor(*[int(v) for v in color]), 2))
        p.drawRect(bx, by, bw, bh)

        items = [
            (f"T-in  : {t_in:.1f} °C",  QColor(255, 220, 80)),
            (f"T-out : {t_out:.1f} °C",  QColor(255, 180, 60)),
            (f"Heat  : {heat:.1f} kW",   QColor(255, 140, 50)),
            (f"Eff   : {eff:.1f} %",     QColor(130, 195, 255)),
            (f"Status: {stat}",          QColor(*[int(v) for v in color])),
        ]
        for i, (txt, col) in enumerate(items):
            p.setPen(col)
            p.setFont(QFont("Courier New", 8, QFont.Bold))
            p.drawText(bx + 8, by + 14 + i * 15, txt)


# ── P&ID Pengering Daun Teh (Tea Leaf Dryer) ──────────────────────────────────

class TeaDryerView(_EndpointBase):
    def __init__(self, parent=None):
        super().__init__("P&ID Pengering Daun Teh",
                         "Tea Leaf Dryer – Steam-heated Rotary Dryer", parent)

    def _draw_pid(self, p: QPainter):
        d = self._data
        t_in  = d.get('inlet_temp', 75)
        t_out = d.get('outlet_temp', 60)
        vpos  = d.get('valve_pos', 70)

        self._draw_pid_title(p, "P&ID: Pengering Daun Teh  (Tea Leaf Dryer)")

        # ── Steam inlet pipe from left ──
        self._pipe(p, 10, 145, 60, 145, temp=t_in)

        # ── PI 01 (above pipe) ──
        self._isa_circle(p, 75, 115, "PI", "01", QColor(230, 190, 70))
        p.setPen(QPen(QColor(200, 170, 60), 1.5))
        p.drawLine(75, 130, 75, 145)

        self._pipe(p, 60, 145, 165, 145, temp=t_in)

        # ── TI 01 (above pipe) ──
        self._isa_circle(p, 130, 115, "TI", f"{t_in:.0f}°", QColor(80, 200, 140))
        p.setPen(QPen(QColor(60, 180, 120), 1.5))
        p.drawLine(130, 130, 130, 145)

        # ── Control valve (main 1") ──
        self._valve(p, 175, 145, vpos)
        self._pipe(p, 184, 145, 230, 145, temp=t_in)

        # ── Solenoid valve (1/2") bypass ──
        self._solenoid_valve(p, 205, 115)
        p.setPen(QPen(QColor(200, 150, 50), 1.5))
        p.drawLine(205, 125, 205, 145)

        # ── Rotary Machine 1st & 2nd Stage Dryer ──
        self._rotary_machine(p, 230, 110, 150, 60,
                             "ROTARY MACHINE\n1st & 2nd Stage\nDryer")

        # TI on top of machine
        self._isa_circle(p, 305, 82, "TI", f"{t_in:.0f}°", QColor(80, 200, 140))
        p.setPen(QPen(QColor(60, 180, 120), 1.5))
        p.drawLine(305, 96, 305, 110)

        # Pipe from 1st/2nd machine to 3rd stage area
        self._pipe(p, 305, 170, 305, 210, temp=(t_in + t_out) * 0.5)

        # ── Rotary Machine 3rd Stage Dryer ──
        self._rotary_machine(p, 380, 185, 130, 55,
                             "ROTARY MACHINE\n3rd Stage Dryer")

        # Fan/blower beside 3rd stage
        self._fan(p, 540, 213, 22)
        p.setPen(QPen(QColor(90, 145, 215), 1.5))
        p.drawLine(540, 191, 540, 185)

        # ── Open Top Roller (top right) ──
        p.setPen(QPen(QColor(155, 155, 165), 2))
        p.setBrush(QBrush(QColor(35, 35, 45)))
        p.drawRect(600, 70, 120, 100)
        p.setPen(QColor(180, 180, 195))
        p.setFont(QFont("Arial", 6))
        p.drawText(608, 76, 104, 20, Qt.AlignCenter, "Open Top Roller")
        for yy in range(95, 170, 14):
            p.setPen(QPen(QColor(140, 140, 155), 3))
            p.drawLine(610, yy, 708, yy)

        # Connect 3rd stage to roller area
        self._pipe(p, 510, 213, 600, 213)
        self._pipe(p, 660, 170, 660, 213)

        # ── Steam Trap outlet ──
        self._pipe(p, 440, 240, 440, 265)
        self._steam_trap(p, 440, 278)

        # Drain Pot
        p.setPen(QPen(QColor(110, 130, 180), 1.5))
        p.setBrush(QBrush(QColor(22, 32, 52)))
        p.drawEllipse(415, 292, 50, 28)
        p.setPen(QColor(140, 160, 210))
        p.setFont(QFont("Arial", 6))
        p.drawText(418, 295, 44, 22, Qt.AlignCenter, "Drain\nPot")

        # Drain pipe from steam trap
        p.setPen(QPen(QColor(90, 110, 155), 2))
        p.drawLine(440, 288, 440, 292)

        # ── Steam from CDP label (inlet) ──
        p.setPen(QColor(160, 200, 255))
        p.setFont(QFont("Arial", 6))
        p.drawText(5, 155, "Steam\nFrom CDP")


# ── P&ID Kolam Ikan (Fish Pond) ───────────────────────────────────────────────

class FishPondView(_EndpointBase):
    def __init__(self, parent=None):
        super().__init__("P&ID Kolam Ikan",
                         "Fish Pond – Geothermal Heat Exchange System", parent)

    def _draw_pid(self, p: QPainter):
        d = self._data
        t_in  = d.get('inlet_temp', 48)
        t_out = d.get('outlet_temp', 36)
        vpos  = d.get('valve_pos', 58)

        self._draw_pid_title(p, "P&ID: Kolam Ikan  (Fish Pond)")

        # ── Circulation pump (top) ──
        self._pump(p, 220, 55, 22)
        self._pipe(p, 190, 55, 198, 55)
        self._pipe(p, 242, 55, 340, 55)

        # Valve after pump
        self._valve(p, 280, 55, vpos)

        # Pipe up from pond (return loop)
        self._pipe(p, 190, 55, 190, 195)

        # Arrow down (flow direction)
        p.setPen(QPen(QColor(100, 140, 190), 2))
        p.drawLine(340, 55, 340, 85)
        p.drawLine(335, 80, 340, 85)
        p.drawLine(345, 80, 340, 85)

        # ── Pond 2 (top box) ──
        self._box(p, 340, 85, 120, 70, "POND 2",
                  QColor(24, 40, 65), QColor(80, 120, 180))

        # ── Pond 1 (bottom box) ──
        self._box(p, 340, 195, 120, 75, "POND 1",
                  QColor(22, 36, 58), QColor(70, 110, 170))

        # Inlets from left into ponds
        self._valve(p, 158, 120, vpos)
        self._pipe(p, 10, 120, 147, 120)
        self._pipe(p, 167, 120, 340, 120)

        self._valve(p, 158, 232, vpos)
        self._pipe(p, 10, 232, 147, 232)
        self._pipe(p, 167, 232, 340, 232)

        # ── Filters 1–4 on right side ──
        for i, lbl in enumerate(["FILTER 1", "FILTER 2", "FILTER 3", "FILTER 4"]):
            fy = 85 + i * 45
            self._filter_box(p, 470, fy, 70, 38, lbl)
            self._pipe(p, 460, fy + 19, 470, fy + 19)

        # ── Heat Transfer section ──
        self._heat_exchanger(p, 470, 265, 70, 40)
        lbl_ht = self.scene if hasattr(self, 'scene') else None
        p.setPen(QColor(160, 180, 215))
        p.setFont(QFont("Arial", 5))
        p.drawText(468, 258, 74, 10, Qt.AlignCenter, "HEAT TRANSFER")

        # Steam from manifold → heat exchanger
        self._pipe(p, 560, 285, 640, 285, temp=t_in)
        p.setPen(QColor(160, 200, 255))
        p.setFont(QFont("Arial", 6))
        p.drawText(645, 282, "From Steam\nManifold")
        self._valve(p, 618, 285, vpos)

        # ── Bak Control ──
        self._box(p, 470, 310, 70, 30, "BAK\nCONTROL",
                  QColor(20, 35, 52), QColor(75, 105, 145))

        # ── Supply Air fan (bottom) ──
        self._fan(p, 250, 300, 22)
        p.setPen(QColor(130, 170, 220))
        p.setFont(QFont("Arial", 6))
        p.drawText(215, 328, "Supply Air")

        # ── Drain Pond (bottom right) ──
        p.setPen(QPen(QColor(100, 125, 170), 1.5))
        p.setBrush(QBrush(QColor(18, 28, 45)))
        p.drawRect(560, 305, 90, 28)
        p.setPen(QColor(130, 155, 200))
        p.setFont(QFont("Arial", 6))
        p.drawText(563, 308, 84, 22, Qt.AlignCenter, "DRAIN POND")

        # Arrow labels
        for lbl, x, y in [("DRAIN POND", 650, 195),
                           ("POND JULIET", 650, 240),
                           ("GREEN HOUSE", 650, 285)]:
            p.setPen(QColor(140, 165, 205))
            p.setFont(QFont("Arial", 6))
            p.drawText(x, y, lbl)
            self._pipe(p, 540, y - 4, x - 5, y - 4)

        # Steam inlet label
        p.setPen(QColor(160, 200, 255))
        p.setFont(QFont("Arial", 6))
        p.drawText(5, 125, "Steam\nFrom CDP")
        p.drawText(5, 237, "Steam\nFrom CDP")


# ── P&ID Kolam Air Panas (Hot Water Pool / Kolam Rendam) ──────────────────────

class HotPoolView(_EndpointBase):
    def __init__(self, parent=None):
        super().__init__("P&ID Kolam Air Panas",
                         "Hot Water Pool – Geothermal Pool Heat Exchanger", parent)

    def _draw_pid(self, p: QPainter):
        d = self._data
        t_in  = d.get('inlet_temp', 130)
        t_out = d.get('outlet_temp', 75)
        vpos  = d.get('valve_pos', 75)

        self._draw_pid_title(p, "P&ID: Kolam Air Panas  (Hot Water Pool)")

        # ── TI 40 and TE (top instruments) ──
        self._isa_circle(p, 310, 50, "TI", "40°C", QColor(230, 190, 70))
        self._isa_circle(p, 310, 85, "TE", "", QColor(80, 200, 140))
        p.setPen(QPen(QColor(60, 180, 120), 1.5))
        p.drawLine(310, 99, 310, 140)

        # ── From Pond 2 (left side) ──
        p.setPen(QColor(160, 200, 255))
        p.setFont(QFont("Arial", 6))
        p.drawText(5, 145, "From\nPond 2")
        self._pipe(p, 55, 145, 100, 145)

        # FI (Flow Indicator)
        self._isa_circle(p, 115, 120, "FI", "", QColor(80, 200, 140))
        p.setPen(QPen(QColor(60, 180, 120), 1.5))
        p.drawLine(115, 134, 115, 145)
        self._pipe(p, 100, 145, 200, 145)

        # ── Filter ──
        self._filter_box(p, 200, 120, 50, 50, "FILTER")
        self._pipe(p, 250, 145, 290, 145)

        # ── Control valve (DN60) ──
        self._valve(p, 300, 145, vpos)
        p.setPen(QColor(150, 160, 180))
        p.setFont(QFont("Arial", 6))
        p.drawText(285, 165, "DN60")

        # ── Pool Heat Exchanger ──
        self._pipe(p, 314, 145, 360, 145, temp=t_in)
        self._heat_exchanger(p, 360, 120, 100, 50)
        p.setPen(QColor(160, 185, 220))
        p.setFont(QFont("Arial", 7, QFont.Bold))
        p.drawText(360, 108, 100, 14, Qt.AlignCenter, "POOL HEAT\nEXCHANGER")

        # ── Pool (large box right) ──
        self._box(p, 475, 100, 190, 130, "POOL",
                  QColor(22, 40, 65), QColor(75, 115, 185))

        # Loop pipe: pool → heat exchanger
        self._pipe(p, 475, 145, 460, 145, temp=t_out)
        self._pipe(p, 460, 145, 460, 115)
        self._pipe(p, 460, 115, 360, 115, temp=t_out)

        # Return loop from right side of pool
        self._pipe(p, 665, 165, 700, 165, temp=t_out)
        # Circulation Pump System (lower section)
        p.setPen(QColor(120, 150, 195))
        p.setFont(QFont("Arial", 7, QFont.Bold))
        p.drawText(300, 260, "CIRCULATION PUMP SYSTEM")
        p.setPen(QPen(QColor(80, 110, 155), 1))
        p.drawRect(290, 266, 400, 55)

        # Inside circulation system
        self._filter_box(p, 300, 273, 50, 40, "FILTER")
        self._valve(p, 370, 293, vpos)
        self._pump(p, 430, 293, 18)
        self._valve(p, 480, 293, vpos)
        self._filter_box(p, 510, 273, 50, 40, "FILTER")
        self._valve(p, 575, 293, vpos)
        # Connect circ system
        for x1, x2, y in [(350, 361, 293), (379, 412, 293),
                           (448, 471, 293), (489, 510, 293), (560, 575, 293)]:
            self._pipe(p, x1, y, x2, y, temp=t_out)

        # ── Steam from manifold → solenoid → HX ──
        p.setPen(QColor(160, 200, 255))
        p.setFont(QFont("Arial", 6))
        p.drawText(5, 215, "From Steam\nManifold")
        p.setPen(QColor(150, 165, 185))
        p.setFont(QFont("Arial", 6))
        p.drawText(68, 228, "DN25\n175°C\n904 Kg/h")

        self._pipe(p, 55, 220, 200, 220, temp=t_in)
        self._valve(p, 175, 220, vpos)
        self._solenoid_valve(p, 215, 220)
        self._pipe(p, 224, 220, 360, 165, temp=t_in)

        # ── Steam Trap (T) after HX ──
        self._pipe(p, 310, 175, 310, 220)
        self._steam_trap(p, 310, 232)
        p.setPen(QColor(150, 155, 180))
        p.setFont(QFont("Arial", 6))
        p.drawText(318, 230, "Steam\nTrap")

        # ── Drain Pond (bottom) ──
        self._pipe(p, 430, 321, 430, 338)
        p.setPen(QPen(QColor(100, 125, 170), 1.5))
        p.setBrush(QBrush(QColor(18, 28, 45)))
        p.drawRect(380, 338, 100, 28)
        p.setPen(QColor(130, 155, 200))
        p.setFont(QFont("Arial", 6))
        p.drawText(383, 341, 94, 22, Qt.AlignCenter, "DRAIN POND")


# ── P&ID Food Dehydrator ───────────────────────────────────────────────────────

class FoodDehydView(_EndpointBase):
    def __init__(self, parent=None):
        super().__init__("P&ID Food Dehydrator",
                         "Food Dehydrator – Steam-heated Fin & Tube Heat Exchanger", parent)

    def _draw_pid(self, p: QPainter):
        d = self._data
        t_in  = d.get('inlet_temp', 60)
        t_out = d.get('outlet_temp', 48)
        vpos  = d.get('valve_pos', 65)

        self._draw_pid_title(p, "P&ID: Food Dehydrator")

        # Steam service label (left)
        p.setPen(QColor(160, 200, 255))
        p.setFont(QFont("Arial", 6))
        p.drawText(6, 125, "Steam Service\n1\" ANSI 150#\nP: Max 3 Barg")

        # ── Main steam line ──
        self._pipe(p, 80, 165, 130, 165, temp=t_in)

        # ── Manual Valve ──
        self._valve(p, 140, 165, vpos)
        p.setPen(QColor(150, 160, 180))
        p.setFont(QFont("Arial", 6))
        p.drawText(125, 183, "Manual\nValve")

        self._pipe(p, 149, 165, 190, 165, temp=t_in)

        # ── Y Strainer ──
        path = QPainterPath()
        path.moveTo(190, 157)
        path.lineTo(210, 157)
        path.lineTo(200, 175)
        path.closeSubpath()
        p.setPen(QPen(QColor(180, 180, 180), 2))
        p.setBrush(QBrush(QColor(50, 58, 48)))
        p.drawPath(path)
        p.setPen(QColor(150, 155, 170))
        p.setFont(QFont("Arial", 6))
        p.drawText(183, 182, "Y Strainer")

        self._pipe(p, 210, 165, 280, 165, temp=t_in)

        # ── PI 01 (above pipe) ──
        self._isa_circle(p, 250, 135, "PI", "01", QColor(230, 190, 70))
        p.setPen(QPen(QColor(200, 170, 60), 1.5))
        p.drawLine(250, 150, 250, 165)
        p.setPen(QColor(150, 155, 170))
        p.setFont(QFont("Arial", 6))
        p.drawText(225, 195, "Pressure\nIndicator")

        # ── TI 01 ──
        self._isa_circle(p, 305, 135, "TI", f"{t_in:.0f}°", QColor(80, 200, 140))
        p.setPen(QPen(QColor(60, 180, 120), 1.5))
        p.drawLine(305, 150, 305, 165)
        p.setPen(QColor(150, 155, 170))
        p.setFont(QFont("Arial", 6))
        p.drawText(280, 195, "Temperature\nIndicator")

        self._pipe(p, 280, 165, 360, 165, temp=t_in)

        # ── Solenoid Valve ──
        self._solenoid_valve(p, 370, 165)
        p.setPen(QColor(150, 155, 170))
        p.setFont(QFont("Arial", 6))
        p.drawText(355, 185, "Solenoid\nValve")

        self._pipe(p, 379, 165, 420, 165, temp=t_in)

        # ── Equipment boundary box ──
        p.setPen(QPen(QColor(90, 110, 155), 1, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(415, 90, 280, 200)
        p.setPen(QColor(120, 140, 185))
        p.setFont(QFont("Arial", 7, QFont.Bold))
        p.drawText(418, 80, "Equipment: Food Dehydrator")

        # ── TT (Temperature Transmitter) 80°C inside ──
        self._isa_circle(p, 500, 118, "TT", "80°C", QColor(80, 200, 140))
        p.setPen(QColor(80, 200, 140))
        p.setFont(QFont("Arial", 6))
        p.drawText(458, 108, "Temperature\nTransmitter")

        # ── Fin & Tube Heat Exchanger ──
        self._heat_exchanger(p, 420, 145, 150, 55)
        # Fins (vertical lines on top)
        for fx in range(425, 565, 12):
            p.setPen(QPen(QColor(160, 160, 180), 1))
            p.drawLine(fx, 140, fx, 150)
        p.setPen(QColor(160, 185, 220))
        p.setFont(QFont("Arial", 6, QFont.Bold))
        p.drawText(422, 133, 146, 14, Qt.AlignCenter, "Fin & Tube Heat Exchanger")

        # ── AC Motor / Fan ──
        self._fan(p, 510, 230, 26)
        p.setPen(QColor(130, 170, 220))
        p.setFont(QFont("Arial", 6))
        p.drawText(480, 265, "AC Motor")
        p.drawText(480, 276, "(Fan)")

        # ── Steam Trap at outlet (right of HX) ──
        self._pipe(p, 570, 172, 610, 172)
        self._steam_trap(p, 625, 172)
        p.setPen(QColor(155, 155, 180))
        p.setFont(QFont("Arial", 6))
        p.drawText(615, 155, "Steam\nTrap")

        # ── Drain (with Y symbol) ──
        self._pipe(p, 625, 182, 625, 210)
        # Y-fork drain symbol
        p.setPen(QPen(QColor(140, 150, 190), 2))
        p.drawLine(625, 210, 605, 235)
        p.drawLine(625, 210, 645, 235)
        p.drawLine(625, 210, 625, 255)
        p.setPen(QColor(130, 145, 185))
        p.setFont(QFont("Arial", 6))
        p.drawText(618, 260, "Drain")


# ── Cabin Warmer schematic ─────────────────────────────────────────────────────

class CabinView(_EndpointBase):
    def __init__(self, parent=None):
        super().__init__("Cabin Warmer",
                         "Space Heating – Direct Steam Heat Exchanger", parent)

    def _draw_pid(self, p: QPainter):
        d = self._data
        t_in  = d.get('inlet_temp', 162)
        t_out = d.get('outlet_temp', 130)
        vpos  = d.get('valve_pos', 70)

        self._draw_pid_title(p, "P&ID: Cabin Warmer  (Space Heating)")

        # Steam inlet
        p.setPen(QColor(160, 200, 255))
        p.setFont(QFont("Arial", 6))
        p.drawText(6, 145, "Steam From\nCDP (162°C)")

        self._pipe(p, 80, 150, 140, 150, temp=t_in)

        # PI
        self._isa_circle(p, 155, 120, "PI", "01", QColor(230, 190, 70))
        p.setPen(QPen(QColor(200, 170, 60), 1.5))
        p.drawLine(155, 135, 155, 150)

        # TI
        self._isa_circle(p, 200, 120, "TI", f"{t_in:.0f}°", QColor(80, 200, 140))
        p.setPen(QPen(QColor(60, 180, 120), 1.5))
        p.drawLine(200, 135, 200, 150)

        self._pipe(p, 140, 150, 280, 150, temp=t_in)

        # Control valve
        self._valve(p, 250, 150, vpos)

        # Heat Exchanger (main)
        self._heat_exchanger(p, 290, 120, 180, 60)
        p.setPen(QColor(155, 185, 225))
        p.setFont(QFont("Arial", 7, QFont.Bold))
        p.drawText(292, 108, 176, 14, Qt.AlignCenter, "HEAT EXCHANGER")

        # Cabin building symbol
        self._box(p, 490, 100, 200, 100, "CABIN\n(Space Heating)",
                  QColor(28, 45, 65), QColor(90, 130, 195))
        # Roof shape
        p.setPen(QPen(QColor(110, 145, 200), 2))
        p.drawLine(490, 100, 590, 60)
        p.drawLine(690, 100, 590, 60)

        # Pipes to/from cabin
        self._pipe(p, 470, 150, 490, 150, temp=t_in)
        self._pipe(p, 690, 150, 730, 150, temp=t_out)

        # Return to steam trap
        self._pipe(p, 730, 150, 730, 200)
        self._steam_trap(p, 730, 212)

        # Condensate drain
        self._pipe(p, 730, 222, 730, 255)
        p.setPen(QPen(QColor(140, 155, 195), 2))
        p.drawLine(710, 255, 750, 255)
        p.setPen(QColor(130, 145, 190))
        p.setFont(QFont("Arial", 6))
        p.drawText(755, 252, "Condensate\nDrain")

        # Return from cabin to HX
        self._pipe(p, 490, 175, 290, 175, temp=t_out)
        p.setPen(QColor(140, 160, 200))
        p.setFont(QFont("Arial", 6))
        p.drawText(360, 192, "Condensate Return")


# ── Green House schematic ──────────────────────────────────────────────────────

class GreenHouseView(_EndpointBase):
    def __init__(self, parent=None):
        super().__init__("Green House",
                         "Agricultural Greenhouse – Low-Temperature Heating", parent)

    def _draw_pid(self, p: QPainter):
        d = self._data
        t_in  = d.get('inlet_temp', 28)
        t_out = d.get('outlet_temp', 24)
        vpos  = d.get('valve_pos', 52)

        self._draw_pid_title(p, "P&ID: Green House  (Agricultural Heating)")

        # Steam inlet
        p.setPen(QColor(160, 200, 255))
        p.setFont(QFont("Arial", 6))
        p.drawText(6, 145, "Steam From\nCDP (28°C)")

        self._pipe(p, 80, 150, 160, 150, temp=t_in)

        # TI
        self._isa_circle(p, 175, 118, "TI", f"{t_in:.0f}°", QColor(80, 200, 140))
        p.setPen(QPen(QColor(60, 180, 120), 1.5))
        p.drawLine(175, 132, 175, 150)

        # Control valve
        self._valve(p, 215, 150, vpos)
        self._pipe(p, 224, 150, 280, 150, temp=t_in)

        # Heat Exchanger
        self._heat_exchanger(p, 280, 122, 120, 55)
        p.setPen(QColor(155, 185, 225))
        p.setFont(QFont("Arial", 7, QFont.Bold))
        p.drawText(282, 110, 116, 14, Qt.AlignCenter, "HEAT EXCHANGER")

        # Greenhouse structure
        p.setPen(QPen(QColor(70, 160, 90), 2))
        p.setBrush(QBrush(QColor(20, 45, 28)))
        p.drawRect(420, 80, 280, 150)
        # Glass panes
        for x in range(440, 700, 30):
            p.setPen(QPen(QColor(60, 130, 75), 1))
            p.drawLine(x, 80, x, 230)
        # Greenhouse roof
        p.setPen(QPen(QColor(90, 175, 105), 2))
        p.drawLine(420, 80, 560, 38)
        p.drawLine(700, 80, 560, 38)

        # Plants inside greenhouse
        for px in range(445, 700, 40):
            p.setPen(QPen(QColor(0, 180, 50), 2))
            p.drawLine(px, 220, px, 185)
            # Simple leaf
            p.setBrush(QBrush(QColor(0, 180, 50)))
            p.setPen(QPen(QColor(0, 200, 60), 1))
            p.drawEllipse(px - 8, 175, 16, 12)

        p.setPen(QColor(80, 200, 100))
        p.setFont(QFont("Arial", 7, QFont.Bold))
        p.drawText(422, 248, 276, 14, Qt.AlignCenter, "GREEN HOUSE (Agricultural Heating)")

        # Distribution pipes inside GH
        p.setPen(QPen(QColor(80, 140, 170), 2, Qt.DotLine))
        p.drawLine(420, 210, 700, 210)

        # Pipe connections
        self._pipe(p, 400, 150, 420, 150, temp=t_in)
        self._pipe(p, 700, 150, 740, 150, temp=t_out)
        self._pipe(p, 740, 150, 740, 200)
        self._steam_trap(p, 740, 212)
        self._pipe(p, 740, 222, 740, 255)
        p.setPen(QPen(QColor(140, 155, 195), 2))
        p.drawLine(720, 255, 760, 255)
        p.setPen(QColor(130, 145, 190))
        p.setFont(QFont("Arial", 6))
        p.drawText(765, 252, "Drain")


# ── factory function ───────────────────────────────────────────────────────────

def make_endpoint_view(stage_id: str) -> _EndpointBase:
    """Return the appropriate P&ID view widget for a given stage ID."""
    mapping = {
        'cabin':             CabinView,
        'hot_pool':          HotPoolView,
        'tea_dryer':         TeaDryerView,
        'food_dehydrator_1': FoodDehydView,
        'food_dehydrator_2': FoodDehydView,
        'fish_pond':         FishPondView,
        'green_house':       GreenHouseView,
    }
    cls = mapping.get(stage_id, _EndpointBase)
    if cls is _EndpointBase:
        return _EndpointBase(stage_id)
    return cls()
