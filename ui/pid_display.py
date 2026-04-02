"""
Distribution P&ID HMI Display
Geothermal Direct Use Heat Distribution System - CDP Well DP-6 (PT Geo Dipa)

Layout (scene 1100 x 420):
  [CDP DP-6] --[PT][TT]-- 2" Header --+--+--+--+--+--+--+-- [RD]
                                       |  |  |  |  |  |  |
                                      [V][V][V][V][V][V][V]   (valve per branch)
                                       |  |  |  |  |  |  |
                                      [TI suhu inlet]
                                       |  |  |  |  |  |  |
                                      [HE][HE]...(heat exchanger)
                                       |  |  |  |  |  |  |
                                      [TI suhu outlet]
                                       |  |  |  |  |  |  |
                                     [Unit Direct Use]
"""
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _temp_color(temp: float) -> QColor:
    """170degC=merah ... 24degC=biru"""
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


# ---------------------------------------------------------------------------
# Layout constants  (scene 1100 x 420)
# ---------------------------------------------------------------------------
SCENE_W  = 1100
SCENE_H  = 440

HEADER_Y = 70          # y garis header utama 2"
PIPE_W   = 5
BRANCH_W = 3

# 7 branch — x positions, lebih lebar supaya tidak overlapping
_BRANCHES = [
    ('cabin',             'Cabin\nWarmer',    110),
    ('hot_pool',          'Hot\nPool',        252),
    ('tea_dryer',         'Tea\nDryer',       394),
    ('food_dehydrator_1', 'Food\nDehy 1',     536),
    ('fish_pond',         'Fish\nPond',       678),
    ('food_dehydrator_2', 'Food\nDehy 2',     820),
    ('green_house',       'Green\nHouse',     962),
]

VALVE_Y      = HEADER_Y + 38    # valve di branch
TI_IN_Y      = VALVE_Y + 40    # TI inlet
HE_TOP       = TI_IN_Y + 28    # top HE box
HE_H         = 38
HE_W         = 100
TI_OUT_Y     = HE_TOP + HE_H + 28   # TI outlet
BOX_TOP      = TI_OUT_Y + 28        # unit box
BOX_H        = 72
BOX_W        = 104


class PIDDisplay(QWidget):
    """
    Distribution P&ID diagram (SCADA HMI style).
    Urutan vertikal per branch:
      Header -> Valve -> TI-in -> HE -> TI-out -> Unit Box
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor(10, 14, 22)))

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background:#0a0e16; border:none;")

        # Dynamic items
        self._valve_items      = {}
        self._sensor_dots      = {}
        self._ti_in_labels     = {}   # TI inlet value
        self._ti_out_labels    = {}   # TI outlet value
        self._box_labels       = {}   # heat / flow / dp dalam box unit
        self._status_borders   = {}
        self._branch_pipes_in  = {}   # pipa header->HE (warna inlet)
        self._branch_pipes_out = {}   # pipa HE->box (warna outlet)
        self._he_items         = {}   # HE box item

        self._build_diagram()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

        _timer = QTimer(self)
        _timer.timeout.connect(lambda: None)
        _timer.start(200)

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------

    def _build_diagram(self):
        # Judul
        t = self.scene.addText(
            "P&ID — Geothermal Direct Use Distribution  |  CDP Well DP-6  |  PT Geo Dipa Energy (Persero)")
        t.setDefaultTextColor(QColor(80, 120, 170))
        t.setFont(QFont("Arial", 7, QFont.Bold))
        t.setPos(6, 4)

        self._draw_source()
        self._draw_main_header()
        self._draw_header_instruments()
        self._draw_rupture_disc()
        self._draw_all_branches()
        self._draw_legend()
        self._fit_view()

    def _draw_source(self):
        s = self.scene
        cx, cy = 52, HEADER_Y

        # CDP box
        s.addRect(cx - 44, cy - 24, 76, 48,
                  QPen(QColor(180, 130, 40), 2), QBrush(QColor(40, 30, 10)))
        lbl = s.addText("CDP DP-6")
        lbl.setDefaultTextColor(QColor(240, 180, 60))
        lbl.setFont(QFont("Arial", 6, QFont.Bold))
        lbl.setPos(cx - 40, cy - 22)
        sub = s.addText("170 degC / 8 bar")
        sub.setDefaultTextColor(QColor(200, 160, 80))
        sub.setFont(QFont("Arial", 5))
        sub.setPos(cx - 40, cy - 6)
        sub2 = s.addText("3374 kg/h")
        sub2.setDefaultTextColor(QColor(180, 150, 70))
        sub2.setFont(QFont("Arial", 5))
        sub2.setPos(cx - 40, cy + 6)

        # Pipe ke header
        s.addLine(cx + 32, cy, 88, cy,
                  QPen(QColor(200, 120, 30), PIPE_W, Qt.SolidLine, Qt.RoundCap))

    def _draw_main_header(self):
        x_start = 88
        x_end   = SCENE_W - 60
        s = self.scene
        pen = QPen(QColor(100, 130, 175), PIPE_W, Qt.SolidLine, Qt.RoundCap)
        s.addLine(x_start, HEADER_Y, x_end, HEADER_Y, pen)
        lbl = s.addText('2" Steam Header')
        lbl.setDefaultTextColor(QColor(80, 110, 155))
        lbl.setFont(QFont("Arial", 6))
        lbl.setPos(x_start + 4, HEADER_Y - 18)

    def _draw_header_instruments(self):
        # PT-01
        self._isa_bubble(140, HEADER_Y - 32, "PT", "01", QColor(80, 150, 230))
        self.scene.addLine(140, HEADER_Y - 16, 140, HEADER_Y,
                           QPen(QColor(80, 150, 230), 1.5))
        # TT-01
        self._isa_bubble(190, HEADER_Y - 32, "TT", "01", QColor(80, 210, 140))
        self.scene.addLine(190, HEADER_Y - 16, 190, HEADER_Y,
                           QPen(QColor(80, 210, 140), 1.5))

    def _isa_bubble(self, x, y, tag, num, color):
        r = 14
        self.scene.addEllipse(x - r, y - r, r * 2, r * 2,
                              QPen(color, 1.5), QBrush(QColor(14, 20, 36)))
        self.scene.addLine(x - r, y, x + r, y, QPen(color, 1))
        t1 = self.scene.addText(tag)
        t1.setDefaultTextColor(color)
        t1.setFont(QFont("Arial", 5, QFont.Bold))
        t1.setPos(x - 9, y - 13)
        t2 = self.scene.addText(num)
        t2.setDefaultTextColor(color.lighter(140))
        t2.setFont(QFont("Arial", 4))
        t2.setPos(x - 5, y)

    def _draw_rupture_disc(self):
        s  = self.scene
        rx = SCENE_W - 58
        ry = HEADER_Y
        # Simbol rupture disc (dua garis vertikal)
        s.addLine(rx - 4, ry - 12, rx - 4, ry + 12, QPen(QColor(255, 80, 80), 2.5))
        s.addLine(rx + 4, ry - 12, rx + 4, ry + 12, QPen(QColor(255, 80, 80), 2.5))
        s.addLine(rx - 4, ry, rx + 4, ry,             QPen(QColor(255, 80, 80), 1))
        # Vent ke bawah
        s.addLine(rx, ry + 12, rx, ry + 36, QPen(QColor(200, 70, 70), 3))
        s.addLine(rx - 14, ry + 36, rx + 14, ry + 36, QPen(QColor(200, 70, 70), 3))
        lbl = s.addText("RD")
        lbl.setDefaultTextColor(QColor(255, 120, 120))
        lbl.setFont(QFont("Arial", 5, QFont.Bold))
        lbl.setPos(rx + 6, ry - 10)

    def _draw_all_branches(self):
        for sid, name, bx in _BRANCHES:
            self._draw_branch(sid, name, bx)

    def _draw_branch(self, sid, name, bx):
        s = self.scene

        # --- Pipa vertikal dari header ke valve ---
        pen_in = QPen(QColor(75, 100, 140), BRANCH_W, Qt.SolidLine, Qt.RoundCap)
        pipe_in = s.addLine(bx, HEADER_Y + PIPE_W, bx, VALVE_Y - 10, pen_in)
        self._branch_pipes_in[sid] = pipe_in

        # --- Valve ---
        self._draw_valve_symbol(bx, VALVE_Y, sid)

        # --- Pipa valve ke TI-in ---
        s.addLine(bx, VALVE_Y + 12, bx, TI_IN_Y - 14,
                  QPen(QColor(75, 100, 140), BRANCH_W, Qt.SolidLine, Qt.RoundCap))

        # --- TI inlet ---
        self._draw_ti(bx, TI_IN_Y, "TI", "in", sid, inlet=True)

        # --- Pipa TI-in ke HE ---
        s.addLine(bx, TI_IN_Y + 14, bx, HE_TOP,
                  QPen(QColor(75, 100, 140), BRANCH_W, Qt.SolidLine, Qt.RoundCap))

        # --- Heat Exchanger box ---
        hx = bx - HE_W // 2
        he_rect = s.addRect(hx, HE_TOP, HE_W, HE_H,
                            QPen(QColor(100, 140, 190), 2),
                            QBrush(QColor(18, 28, 48)))
        self._he_items[sid] = he_rect
        # Tanda X di dalam HE
        s.addLine(hx + 4, HE_TOP + 4, hx + HE_W - 4, HE_TOP + HE_H - 4,
                  QPen(QColor(80, 120, 175), 1.5))
        s.addLine(hx + HE_W - 4, HE_TOP + 4, hx + 4, HE_TOP + HE_H - 4,
                  QPen(QColor(80, 120, 175), 1.5))
        # Label HE
        hx_lbl_map = {
            'cabin': 'HX-01', 'hot_pool': 'HX-02', 'tea_dryer': 'HX-03',
            'food_dehydrator_1': 'HX-04', 'fish_pond': 'HX-05',
            'food_dehydrator_2': 'HX-06', 'green_house': 'HX-07',
        }
        he_tag = s.addText(hx_lbl_map.get(sid, 'HE'))
        he_tag.setDefaultTextColor(QColor(140, 170, 210))
        he_tag.setFont(QFont("Arial", 6, QFont.Bold))
        he_tag.setPos(bx - 14, HE_TOP + HE_H // 2 - 8)

        # --- Pipa HE ke TI-out ---
        pipe_out = s.addLine(bx, HE_TOP + HE_H, bx, TI_OUT_Y - 14,
                             QPen(QColor(55, 85, 120), BRANCH_W, Qt.SolidLine, Qt.RoundCap))
        self._branch_pipes_out[sid] = pipe_out

        # --- TI outlet ---
        self._draw_ti(bx, TI_OUT_Y, "TI", "out", sid, inlet=False)

        # --- Pipa TI-out ke unit box ---
        s.addLine(bx, TI_OUT_Y + 14, bx, BOX_TOP,
                  QPen(QColor(55, 85, 120), BRANCH_W, Qt.SolidLine, Qt.RoundCap))

        # --- Unit box ---
        self._draw_unit_box(bx, BOX_TOP, sid, name)

    def _draw_valve_symbol(self, x, y, sid):
        """Gate valve: segitiga tunggal menunjuk kanan."""
        r = 9
        path = QPainterPath()
        path.moveTo(x - r, y - r)
        path.lineTo(x + r, y)
        path.lineTo(x - r, y + r)
        path.closeSubpath()
        color = QColor(0, 200, 120)
        item  = self.scene.addPath(path, QPen(color, 1.5), QBrush(color))
        self._valve_items[sid] = item
        # Aktuator
        self.scene.addLine(x, y - r, x, y - r - 8, QPen(QColor(150, 150, 160), 1.5))
        self.scene.addEllipse(x - 5, y - r - 14, 10, 6,
                              QPen(QColor(130, 130, 145), 1.5),
                              QBrush(QColor(50, 50, 55)))

    def _draw_ti(self, x, y, tag, suffix, sid, inlet=True):
        """ISA temperature indicator circle."""
        r   = 13
        col = QColor(75, 200, 140) if inlet else QColor(200, 150, 75)
        self.scene.addEllipse(x - r, y - r, r * 2, r * 2,
                              QPen(col, 1.5), QBrush(QColor(14, 28, 22)))
        tg = self.scene.addText(tag)
        tg.setDefaultTextColor(col)
        tg.setFont(QFont("Arial", 4, QFont.Bold))
        tg.setPos(x - 8, y - 12)
        val = self.scene.addText("--")
        val.setDefaultTextColor(QColor(200, 240, 210) if inlet else QColor(240, 210, 160))
        val.setFont(QFont("Arial", 4))
        val.setPos(x - 10, y - 1)
        if inlet:
            self._ti_in_labels[sid]  = val
        else:
            self._ti_out_labels[sid] = val

    def _draw_unit_box(self, cx, top_y, sid, name):
        s   = self.scene
        bx  = cx - BOX_W // 2

        # Border (warna status)
        border = s.addRect(bx, top_y, BOX_W, BOX_H,
                           QPen(QColor(70, 100, 145), 2),
                           QBrush(QColor(16, 24, 40)))
        self._status_borders[sid] = border

        # Nama unit
        nl = s.addText(name)
        nl.setDefaultTextColor(QColor(190, 210, 250))
        nl.setFont(QFont("Arial", 6, QFont.Bold))
        nl.setPos(bx + 3, top_y + 2)

        # Label data (heat, flow, dp) — akan diupdate
        hl = s.addText("Q: -- kW")
        hl.setDefaultTextColor(QColor(255, 165, 50))
        hl.setFont(QFont("Arial", 5))
        hl.setPos(bx + 3, top_y + 22)

        fl = s.addText("F: -- kg/h")
        fl.setDefaultTextColor(QColor(100, 190, 255))
        fl.setFont(QFont("Arial", 5))
        fl.setPos(bx + 3, top_y + 34)

        dp_l = s.addText("dP: -- bar")
        dp_l.setDefaultTextColor(QColor(180, 180, 200))
        dp_l.setFont(QFont("Arial", 5))
        dp_l.setPos(bx + 3, top_y + 46)

        eff_l = s.addText("n: --%")
        eff_l.setDefaultTextColor(QColor(130, 200, 255))
        eff_l.setFont(QFont("Arial", 5))
        eff_l.setPos(bx + 3, top_y + 57)

        self._box_labels[sid] = {
            'heat': hl, 'flow': fl, 'dp': dp_l, 'eff': eff_l
        }

        # Status dot (pojok kanan bawah)
        dot = s.addEllipse(bx + BOX_W - 14, top_y + BOX_H - 14, 10, 10,
                           QPen(QColor(0, 0, 0, 30), 1),
                           QBrush(QColor(0, 200, 80)))
        self._sensor_dots[sid] = dot

    def _draw_legend(self):
        s = self.scene
        lx = 6
        ly = SCENE_H - 26
        items = [
            (QColor(220, 60, 30),  "Hot (>130 C)"),
            (QColor(200, 150, 30), "Warm (60-130 C)"),
            (QColor(30, 160, 200), "Cool (<60 C)"),
            (QColor(0, 200, 120),  "Valve open"),
            (QColor(255, 195, 0),  "Valve partial"),
            (QColor(255, 70, 70),  "Valve closed"),
        ]
        for i, (col, lbl) in enumerate(items):
            xo = lx + i * 140
            self.scene.addRect(xo, ly, 10, 10, QPen(col, 1), QBrush(col))
            lt = s.addText(lbl)
            lt.setDefaultTextColor(QColor(90, 110, 140))
            lt.setFont(QFont("Arial", 5))
            lt.setPos(xo + 14, ly - 1)

    def _fit_view(self):
        rect = self.scene.sceneRect().adjusted(-6, -6, 6, 6)
        self.view.fitInView(rect, Qt.KeepAspectRatio)

    # -----------------------------------------------------------------------
    # Update API
    # -----------------------------------------------------------------------

    def update_valve_position(self, sid: str, position: float):
        if sid in self._valve_items:
            c  = _valve_color(position)
            it = self._valve_items[sid]
            it.setBrush(QBrush(c))
            it.setPen(QPen(c, 1.5))

    def update_sensor_status(self, sid: str, color_tuple):
        r, g, b = [int(v) for v in color_tuple]
        qc = QColor(r, g, b)
        if sid in self._sensor_dots:
            self._sensor_dots[sid].setBrush(QBrush(qc))
        if sid in self._status_borders:
            self._status_borders[sid].setPen(QPen(qc, 2))

    def update_stage_temps(self, sensor_data: dict):
        for sid, d in sensor_data.items():
            t_in   = d.get('inlet_temp',    0.0)
            t_out  = d.get('outlet_temp',   0.0)
            heat   = d.get('heat_duty_kw',  0.0)
            flow   = d.get('flow_rate_kg_h',0.0)
            dp     = d.get('pressure_drop', 0.0)
            eff    = d.get('efficiency',    0.0)

            if sid in self._ti_in_labels:
                self._ti_in_labels[sid].setPlainText(f"{t_in:.0f}C")
                self._ti_in_labels[sid].setDefaultTextColor(_temp_color(t_in))

            if sid in self._ti_out_labels:
                self._ti_out_labels[sid].setPlainText(f"{t_out:.0f}C")
                self._ti_out_labels[sid].setDefaultTextColor(_temp_color(t_out))

            if sid in self._branch_pipes_in:
                c_in  = _temp_color(t_in)
                self._branch_pipes_in[sid].setPen(
                    QPen(c_in, BRANCH_W, Qt.SolidLine, Qt.RoundCap))

            if sid in self._branch_pipes_out:
                c_out = _temp_color(t_out)
                self._branch_pipes_out[sid].setPen(
                    QPen(c_out, BRANCH_W, Qt.SolidLine, Qt.RoundCap))

            if sid in self._box_labels:
                bl = self._box_labels[sid]
                bl['heat'].setPlainText(f"Q: {heat:.0f} kW")
                bl['flow'].setPlainText(f"F: {flow:.0f} kg/h")
                bl['dp'].setPlainText(f"dP: {dp:.4f} bar")
                bl['eff'].setPlainText(f"n: {eff:.1f}%")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_view()