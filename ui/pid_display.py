"""
Distribution P&ID HMI Display
Geothermal Direct Use Heat Distribution System - CDP Well DP-6 (PT Geo Dipa)

Based on actual P&ID drawings:
  • P&ID Heat Sources  - parallel distribution from CDP Excess Steam
  • P&ID Pengering Daun Teh, Kolam Ikan, Kolam Air Panas, Food Dehydrator

Layout (scene coords, 960 × 360):
┌───────────────────────────────────────────────────────────────────────────────────┐
│  [CDP DP-6]─[ST]─2"──[PT][TT]──[Strainer]──[PI]─────────────────────[Rupture]   │
│  Excess Steam           Main Header                                    Disc       │
│                          │     │     │     │     │     │     │                   │
│                         [V]   [V]   [V]   [V]   [V]   [V]   [V]                 │
│                          │     │     │     │     │     │     │                   │
│                         [TI]  [TI]  [TI]  [TI]  [TI]  [TI]  [TI]               │
│                          │     │     │     │     │     │     │                   │
│                       [Cabin][KolR][PengT][Food1][FishP][Food2][Green]           │
│                          T°C   T°C   T°C   T°C   T°C   T°C   T°C                │
└───────────────────────────────────────────────────────────────────────────────────┘
"""
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

# ── helpers ────────────────────────────────────────────────────────────────────

def _temp_color(temp: float) -> QColor:
    """Map fluid temperature to a colour (170°C=red … 24°C=blue)."""
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


# ── Layout constants ───────────────────────────────────────────────────────────
SCENE_W   = 960
SCENE_H   = 370
HEADER_Y  = 88        # y-centre of main 2" steam header
PIPE_W    = 6         # main header pipe width
BRANCH_W  = 4         # branch pipe width

# 7 parallel branch x-positions (evenly spaced)
_BRANCHES = [
    ('cabin',             'Cabin\nWarmer',    180),
    ('hot_pool',          'Kolam\nRendam',    287),
    ('tea_dryer',         'Pengering\nTeh',   394),
    ('food_dehydrator_1', 'Food\nDehy 1',     501),
    ('fish_pond',         'Fish\nPond',       608),
    ('food_dehydrator_2', 'Food\nDehy 2',     715),
    ('green_house',       'Green\nHouse',     822),
]

VALVE_Y   = 122    # valve symbol y on branch
TI_Y      = 155    # TI instrument circle y
BOX_TOP   = 182    # endpoint box top y
BOX_W     = 104
BOX_H     = 88
DRAIN_Y   = BOX_TOP + BOX_H + 18   # steam trap drain y


class PIDDisplay(QWidget):
    """
    Distribution P&ID diagram (HMI style).
    Shows parallel steam distribution from CDP Well DP-6 to 7 direct-use endpoints.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor(12, 16, 26)))

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background:#0c101a; border:none;")

        # Dynamic item references
        self._valve_items      = {}   # sid → path item
        self._sensor_dots      = {}   # sid → ellipse item
        self._ti_val_labels    = {}   # sid → text (TI circle value)
        self._box_temp_labels  = {}   # sid → text (T-in→T-out in box)
        self._heat_labels      = {}   # sid → text (heat kW in box)
        self._eff_labels       = {}   # sid → text (efficiency in box)
        self._status_borders   = {}   # sid → rect item (colored border)
        self._branch_pipes     = {}   # sid → line item
        self._flow_dots        = []   # animated dots list
        self._anim_phase       = 0

        self._build_diagram()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

        _timer = QTimer(self)
        _timer.timeout.connect(self._tick)
        _timer.start(100)

    # ── diagram construction ───────────────────────────────────────────────────

    def _build_diagram(self):
        # Title
        t = self.scene.addText(
            "P&ID — Geothermal Direct Use Distribution System  |  CDP Well DP-6  |  PT Geo Dipa Energy (Persero)")
        t.setDefaultTextColor(QColor(90, 130, 180))
        t.setFont(QFont("Arial", 7, QFont.Bold))
        t.setPos(6, 4)

        self._draw_source()
        self._draw_main_header()
        self._draw_header_instruments()
        self._draw_strainer()
        self._draw_rupture_and_drain()
        self._draw_all_branches()
        self._fit_view()

    # ── source box ─────────────────────────────────────────────────────────────

    def _draw_source(self):
        s = self.scene
        cx, cy = 68, HEADER_Y

        # CDP source box
        s.addRect(cx - 52, cy - 32, 80, 62,
                  QPen(QColor(200, 150, 50), 2), QBrush(QColor(48, 38, 18)))
        lbl = s.addText("CDP DP-6")
        lbl.setDefaultTextColor(QColor(255, 190, 70))
        lbl.setFont(QFont("Arial", 7, QFont.Bold))
        lbl.setPos(cx - 48, cy - 30)
        sub = s.addText("Excess\nSteam")
        sub.setDefaultTextColor(QColor(220, 180, 100))
        sub.setFont(QFont("Arial", 6))
        sub.setPos(cx - 48, cy - 14)

        # Separator vessel (circle right of box)
        sep_cx = cx + 38
        s.addEllipse(sep_cx - 14, cy - 16, 28, 32,
                     QPen(QColor(130, 155, 200), 2), QBrush(QColor(32, 42, 65)))
        sep_t = s.addText("Sep")
        sep_t.setDefaultTextColor(QColor(170, 195, 240))
        sep_t.setFont(QFont("Arial", 6, QFont.Bold))
        sep_t.setPos(sep_cx - 10, cy - 6)

        # Isolation valve on source outlet
        vx = cx + 58
        self._draw_gate_valve_symbol(vx, cy, color=QColor(190, 190, 210))

        # Steam trap on source line
        self._draw_steam_trap_sym(vx + 22, cy - 14)

        # Pipe from source to header
        s.addLine(vx + 10, cy, 130, cy,
                  QPen(QColor(120, 150, 190), PIPE_W, Qt.SolidLine, Qt.RoundCap))

    def _draw_gate_valve_symbol(self, x, y, color=None):
        """Two facing triangles = gate/butterfly valve."""
        c = color or QColor(200, 200, 220)
        path = QPainterPath()
        path.moveTo(x - 8, y - 8)
        path.lineTo(x + 8, y)
        path.lineTo(x - 8, y + 8)
        path.closeSubpath()
        path2 = QPainterPath()
        path2.moveTo(x + 8, y - 8)
        path2.lineTo(x - 8, y)
        path2.lineTo(x + 8, y + 8)
        path2.closeSubpath()
        self.scene.addPath(path, QPen(c, 1.5), QBrush(c.darker(180)))
        self.scene.addPath(path2, QPen(c, 1.5), QBrush(c.darker(180)))
        # stem + hand-wheel
        self.scene.addLine(x, y - 10, x, y - 20, QPen(c, 1.5))
        self.scene.addEllipse(x - 7, y - 26, 14, 7,
                              QPen(c, 1.5), QBrush(QColor(50, 50, 50)))

    def _draw_steam_trap_sym(self, x, y):
        """Circle with 'T' inside = steam trap."""
        r = 9
        self.scene.addEllipse(x - r, y - r, r * 2, r * 2,
                              QPen(QColor(180, 180, 200), 1.5),
                              QBrush(QColor(40, 45, 62)))
        t = self.scene.addText("T")
        t.setDefaultTextColor(QColor(200, 200, 220))
        t.setFont(QFont("Arial", 7, QFont.Bold))
        t.setPos(x - 5, y - 9)

    # ── main header pipe ───────────────────────────────────────────────────────

    def _draw_main_header(self):
        """Horizontal 2" steam header from source to rupture disc."""
        x_start, x_end = 130, 896
        pen = QPen(QColor(110, 140, 185), PIPE_W, Qt.SolidLine, Qt.RoundCap)
        self.scene.addLine(x_start, HEADER_Y, x_end, HEADER_Y, pen)
        # Size label
        lbl = self.scene.addText('2"')
        lbl.setDefaultTextColor(QColor(90, 120, 165))
        lbl.setFont(QFont("Arial", 6))
        lbl.setPos(140, HEADER_Y - 18)

    # ── instruments on header ──────────────────────────────────────────────────

    def _draw_header_instruments(self):
        """PT, TT, PI instrument bubbles above the main header."""
        # PT - Pressure Transmitter
        self._draw_isa_instrument(148, HEADER_Y - 34, "PT", "01",
                                  QColor(80, 150, 230))
        self.scene.addLine(148, HEADER_Y - 18, 148, HEADER_Y,
                           QPen(QColor(80, 150, 230), 1.5))

        # TT - Temperature Transmitter
        self._draw_isa_instrument(192, HEADER_Y - 34, "TT", "01",
                                  QColor(80, 210, 140))
        self.scene.addLine(192, HEADER_Y - 18, 192, HEADER_Y,
                           QPen(QColor(80, 210, 140), 1.5))

        # PI - Pressure Indicator (after strainer)
        self._draw_isa_instrument(370, HEADER_Y - 34, "PI", "02",
                                  QColor(230, 190, 70))
        self.scene.addLine(370, HEADER_Y - 18, 370, HEADER_Y,
                           QPen(QColor(230, 190, 70), 1.5))

    def _draw_isa_instrument(self, x, y, tag, num, color):
        """ISA instrument bubble: circle bisected by horizontal line."""
        r = 15
        self.scene.addEllipse(x - r, y - r, r * 2, r * 2,
                              QPen(color, 1.5), QBrush(QColor(18, 26, 42)))
        self.scene.addLine(x - r, y, x + r, y, QPen(color, 1))
        t1 = self.scene.addText(tag)
        t1.setDefaultTextColor(color)
        t1.setFont(QFont("Arial", 6, QFont.Bold))
        t1.setPos(x - 10, y - 14)
        t2 = self.scene.addText(num)
        t2.setDefaultTextColor(color.lighter(140))
        t2.setFont(QFont("Arial", 5))
        t2.setPos(x - 5, y)

    # ── strainer ───────────────────────────────────────────────────────────────

    def _draw_strainer(self):
        """Y-strainer symbol on main header."""
        x, y = 278, HEADER_Y
        path = QPainterPath()
        path.moveTo(x - 14, y - 8)
        path.lineTo(x + 14, y - 8)
        path.lineTo(x, y + 12)
        path.closeSubpath()
        self.scene.addPath(path, QPen(QColor(180, 180, 180), 2),
                           QBrush(QColor(50, 58, 48)))
        lbl = self.scene.addText("Strainer")
        lbl.setDefaultTextColor(QColor(150, 150, 150))
        lbl.setFont(QFont("Arial", 6))
        lbl.setPos(x - 18, y + 14)

    # ── rupture disc + drain ───────────────────────────────────────────────────

    def _draw_rupture_and_drain(self):
        """Rupture disc safety device at right end of header + steam trap/drain."""
        s = self.scene
        rx, ry = 896, HEADER_Y

        # Rupture disc (two vertical bars with gap = pressure membrane)
        s.addLine(rx - 5, ry - 14, rx - 5, ry + 14,
                  QPen(QColor(255, 100, 100), 2.5))
        s.addLine(rx + 5, ry - 14, rx + 5, ry + 14,
                  QPen(QColor(255, 100, 100), 2.5))
        s.addLine(rx - 5, ry, rx + 5, ry,
                  QPen(QColor(255, 100, 100), 1))
        # vent pipe going down
        s.addLine(rx, ry + 14, rx, ry + 48,
                  QPen(QColor(200, 90, 90), BRANCH_W))
        s.addLine(rx - 18, ry + 48, rx + 18, ry + 48,
                  QPen(QColor(200, 90, 90), 3))
        lbl = s.addText("RD\n1\"")
        lbl.setDefaultTextColor(QColor(255, 140, 140))
        lbl.setFont(QFont("Arial", 6, QFont.Bold))
        lbl.setPos(rx + 8, ry - 12)

        # Steam trap at top of condensate leg (to the left of rupture disc)
        trap_x = rx - 42
        s.addLine(trap_x, HEADER_Y, trap_x, HEADER_Y + 32,
                  QPen(QColor(140, 150, 175), BRANCH_W))
        self._draw_steam_trap_sym(trap_x, HEADER_Y + 44)
        # drain pot (circle)
        s.addLine(trap_x, HEADER_Y + 53, trap_x, HEADER_Y + 68,
                  QPen(QColor(100, 120, 165), 2))
        s.addEllipse(trap_x - 13, HEADER_Y + 66, 26, 22,
                     QPen(QColor(110, 130, 175), 2), QBrush(QColor(22, 32, 52)))
        dp = s.addText("DP")
        dp.setDefaultTextColor(QColor(140, 155, 195))
        dp.setFont(QFont("Arial", 5))
        dp.setPos(trap_x - 8, HEADER_Y + 72)

    # ── branches ───────────────────────────────────────────────────────────────

    def _draw_all_branches(self):
        for sid, name, bx in _BRANCHES:
            self._draw_single_branch(sid, name, bx)

    def _draw_single_branch(self, sid, name, bx):
        s = self.scene

        # Vertical branch pipe (header → box)
        pen = QPen(QColor(75, 100, 135), BRANCH_W, Qt.SolidLine, Qt.RoundCap)
        pipe = s.addLine(bx, HEADER_Y + PIPE_W // 2, bx, BOX_TOP, pen)
        self._branch_pipes[sid] = pipe

        # Pipe size label
        pl = s.addText('1"')
        pl.setDefaultTextColor(QColor(70, 95, 130))
        pl.setFont(QFont("Arial", 5))
        pl.setPos(bx + 3, HEADER_Y + 6)

        # Valve
        self._draw_branch_valve(bx, VALVE_Y, sid)

        # TI instrument circle
        self._draw_ti_circle(bx, TI_Y, sid)

        # Endpoint box
        self._draw_endpoint_box(bx, BOX_TOP, sid, name)

    def _draw_branch_valve(self, x, y, sid):
        """Single-triangle valve (gate) on branch, colour reflects position."""
        path = QPainterPath()
        r = 9
        path.moveTo(x - r, y - r)
        path.lineTo(x + r, y)
        path.lineTo(x - r, y + r)
        path.closeSubpath()
        color = QColor(0, 200, 120)
        item = self.scene.addPath(path, QPen(color, 2), QBrush(color))
        self._valve_items[sid] = item
        # Actuator stem + handwheel
        self.scene.addLine(x, y - r, x, y - r - 10, QPen(QColor(160, 160, 165), 1.5))
        self.scene.addEllipse(x - 6, y - r - 16, 12, 6,
                              QPen(QColor(140, 140, 148), 1.5),
                              QBrush(QColor(55, 55, 58)))

    def _draw_ti_circle(self, x, y, sid):
        """TI (Temperature Indicator) instrument circle on branch."""
        r = 13
        self.scene.addEllipse(x - r, y - r, r * 2, r * 2,
                              QPen(QColor(75, 200, 140), 1.5),
                              QBrush(QColor(18, 34, 28)))
        tag = self.scene.addText("TI")
        tag.setDefaultTextColor(QColor(75, 200, 140))
        tag.setFont(QFont("Arial", 5, QFont.Bold))
        tag.setPos(x - 8, y - 12)
        val = self.scene.addText("—°C")
        val.setDefaultTextColor(QColor(170, 255, 210))
        val.setFont(QFont("Arial", 5))
        val.setPos(x - 10, y - 1)
        self._ti_val_labels[sid] = val

    def _draw_endpoint_box(self, cx, top_y, sid, name):
        """Endpoint process box showing live T, heat duty, efficiency."""
        s = self.scene
        bx = cx - BOX_W // 2

        # Status-border rect (colour updated on alarm)
        border_item = s.addRect(bx, top_y, BOX_W, BOX_H,
                                QPen(QColor(80, 110, 155), 2),
                                QBrush(QColor(20, 30, 48)))
        self._status_borders[sid] = border_item

        # Name (top)
        n = s.addText(name)
        n.setDefaultTextColor(QColor(195, 215, 255))
        n.setFont(QFont("Arial", 7, QFont.Bold))
        n.setPos(bx + 4, top_y + 2)

        # T-in→T-out label
        tl = s.addText("—→—°C")
        tl.setDefaultTextColor(QColor(255, 220, 80))
        tl.setFont(QFont("Courier New", 7))
        tl.setPos(bx + 4, top_y + 28)
        self._box_temp_labels[sid] = tl

        # Heat duty
        hl = s.addText("— kW")
        hl.setDefaultTextColor(QColor(255, 165, 55))
        hl.setFont(QFont("Arial", 7))
        hl.setPos(bx + 4, top_y + 45)
        self._heat_labels[sid] = hl

        # Efficiency
        el = s.addText("eff —%")
        el.setDefaultTextColor(QColor(130, 195, 255))
        el.setFont(QFont("Arial", 6))
        el.setPos(bx + 4, top_y + 62)
        self._eff_labels[sid] = el

        # Status dot (lower-right corner)
        dot = s.addEllipse(bx + BOX_W - 16, top_y + BOX_H - 16, 12, 12,
                           QPen(QColor(160, 160, 160), 1),
                           QBrush(QColor(0, 200, 80)))
        self._sensor_dots[sid] = dot

        # Condensate line + drain steam trap below box
        s.addLine(cx, top_y + BOX_H, cx, top_y + BOX_H + 16,
                  QPen(QColor(55, 75, 105), 2))
        self._draw_steam_trap_sym(cx, top_y + BOX_H + 26)
        drain = s.addText("ST")
        drain.setDefaultTextColor(QColor(100, 120, 155))
        drain.setFont(QFont("Arial", 4))
        drain.setPos(cx - 6, top_y + BOX_H + 18)

    # ── view fit ───────────────────────────────────────────────────────────────

    def _fit_view(self):
        rect = self.scene.sceneRect().adjusted(-8, -8, 8, 8)
        self.view.fitInView(rect, Qt.KeepAspectRatio)

    # ── update API (called from main window) ───────────────────────────────────

    def update_valve_position(self, sid: str, position: float):
        if sid in self._valve_items:
            c = self._valve_color(position)
            it = self._valve_items[sid]
            it.setBrush(QBrush(c))
            it.setPen(QPen(c, 2))

    def update_sensor_status(self, sid: str, color_tuple):
        r, g, b = [int(v) for v in color_tuple]
        if sid in self._sensor_dots:
            self._sensor_dots[sid].setBrush(QBrush(QColor(r, g, b)))
        if sid in self._status_borders:
            self._status_borders[sid].setPen(QPen(QColor(r, g, b), 2))

    def update_stage_temps(self, sensor_data: dict):
        for sid, d in sensor_data.items():
            t_in  = d.get('inlet_temp', 0)
            t_out = d.get('outlet_temp', 0)
            heat  = d.get('heat_duty_kw', 0)
            eff   = d.get('efficiency', 0)

            if sid in self._ti_val_labels:
                self._ti_val_labels[sid].setPlainText(f"{t_in:.0f}°C")

            if sid in self._box_temp_labels:
                self._box_temp_labels[sid].setPlainText(f"{t_in:.0f}→{t_out:.0f}°C")
                self._box_temp_labels[sid].setDefaultTextColor(_temp_color(t_in))

            if sid in self._heat_labels:
                self._heat_labels[sid].setPlainText(f"{heat:.0f} kW")

            if sid in self._eff_labels:
                self._eff_labels[sid].setPlainText(f"eff {eff:.1f}%")

            if sid in self._branch_pipes:
                c   = _temp_color(t_in)
                pen = QPen(c, BRANCH_W, Qt.SolidLine, Qt.RoundCap)
                self._branch_pipes[sid].setPen(pen)

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _valve_color(pos: float) -> QColor:
        if pos < 20:
            return QColor(255, 70, 70)
        if pos < 50:
            return QColor(255, 195, 0)
        return QColor(0, 215, 110)

    def _tick(self):
        self._anim_phase = (self._anim_phase + 1) % 20

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_view()
