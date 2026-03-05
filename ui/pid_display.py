"""
Cascade P&ID Display
Serpentine layout showing the 7-stage serial geothermal cascade:

  Row 0 (→):  [Source] → [Cabin] → [Kolam Rendam] → [Pengering Teh] → [Food Dehy 1]
                                                                              ↓  U-bend
  Row 1 (←):  [Discharge] ← [Green House] ← [Food Dehy 2] ← [Fish Pond] ←──┘

Each stage shows: inlet→outlet temperature, valve indicator, sensor status.
Pipe segments are colored by fluid temperature (hot=red … cold=blue).
"""
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath


# ── helpers ───────────────────────────────────────────────────────────────────

def _temp_color(temp: float) -> QColor:
    """Map fluid temperature to a colour (170 °C=red … 24 °C=blue)."""
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


# ── stage layout (row, col) for each cascade ID ───────────────────────────────
#   Row 0 goes →  (col 1..4)   Row 1 goes ←  (col 4..2)
_STAGE_LAYOUT = [
    ('cabin',              'Cabin\nWarmer',      0, 1),
    ('hot_pool',           'Kolam\nRendam',       0, 2),
    ('tea_dryer',          'Pengering\nTeh',      0, 3),
    ('food_dehydrator_1',  'Food\nDehy 1',        0, 4),
    ('fish_pond',          'Fish\nPond',           1, 4),
    ('food_dehydrator_2',  'Food\nDehy 2',        1, 3),
    ('green_house',        'Green\nHouse',         1, 2),
]

# geometry constants
_COL_X     = {0: 65, 1: 210, 2: 360, 3: 510, 4: 660}  # x-center per column
_ROW_Y     = {0: 95, 1: 275}                             # y-center per row
_BOX_W, _BOX_H = 110, 58
_VALVE_R   = 9      # valve triangle half-size
_PIPE_W    = 5
_BEND_X    = 720    # x of U-bend vertical pipe


class PIDDisplay(QWidget):
    """Cascade P&ID diagram with serpentine layout."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor(18, 20, 30)))

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background:#12141e; border:none;")

        # Dynamic item references
        self._valve_items   = {}   # sid  → path item
        self._sensor_items  = {}   # sid  → ellipse item
        self._temp_labels   = {}   # sid  → text item
        self._pipe_items    = {}   # key  → line item (for colour updates)

        self._build_diagram()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self._anim_phase = 0
        _timer = QTimer(self)
        _timer.timeout.connect(self._tick)
        _timer.start(100)

    # ── diagram construction ──────────────────────────────────────────────────

    def _build_diagram(self):
        s = self.scene
        row0_stages = [(sid, nm, r, c) for sid, nm, r, c in _STAGE_LAYOUT if r == 0]
        row1_stages = [(sid, nm, r, c) for sid, nm, r, c in _STAGE_LAYOUT if r == 1]

        # ── Source (Well DP-6 + Separator) ───
        sx, sy = _COL_X[0], _ROW_Y[0]
        self._draw_source(sx, sy)

        # ── Stage boxes ──────────────────────
        for sid, nm, row, col in _STAGE_LAYOUT:
            cx = _COL_X[col]
            cy = _ROW_Y[row]
            self._draw_stage_box(cx, cy, sid, nm)

        # ── Discharge ────────────────────────
        dx, dy = _COL_X[1], _ROW_Y[1]
        self._draw_discharge(dx, dy)

        # ── Pipes & valves ───────────────────
        self._draw_row0_pipes(row0_stages)
        self._draw_ubend()
        self._draw_row1_pipes(row1_stages)

        self._fit_view()

    # ── drawing primitives ────────────────────────────────────────────────────

    def _draw_source(self, cx, cy):
        s = self.scene
        # Well box
        s.addRect(cx - 34, cy - 22, 68, 44,
                  QPen(QColor(180, 130, 60), 2), QBrush(QColor(55, 45, 25)))
        t = s.addText("Well\nDP-6")
        t.setDefaultTextColor(QColor(255, 200, 100))
        t.setFont(QFont("Arial", 7, QFont.Bold))
        t.setPos(cx - 25, cy - 18)
        # Separator bubble
        s.addEllipse(cx + 8, cy - 16, 32, 32,
                     QPen(QColor(140, 140, 160), 2), QBrush(QColor(45, 45, 70)))
        t2 = s.addText("Sep")
        t2.setDefaultTextColor(QColor(200, 210, 240))
        t2.setFont(QFont("Arial", 7, QFont.Bold))
        t2.setPos(cx + 14, cy - 8)

    def _draw_discharge(self, cx, cy):
        s = self.scene
        s.addRect(cx - 38, cy - 22, 76, 44,
                  QPen(QColor(90, 90, 110), 2), QBrush(QColor(28, 28, 45)))
        t = s.addText("Discharge\n(Brine)")
        t.setDefaultTextColor(QColor(130, 150, 190))
        t.setFont(QFont("Arial", 7))
        t.setPos(cx - 33, cy - 18)

    def _draw_stage_box(self, cx, cy, sid, name):
        s = self.scene
        bw, bh = _BOX_W, _BOX_H
        # Box
        s.addRect(cx - bw / 2, cy - bh / 2, bw, bh,
                  QPen(QColor(80, 110, 150), 2), QBrush(QColor(28, 38, 55)))
        # Stage name
        t = s.addText(name)
        t.setDefaultTextColor(QColor(210, 225, 255))
        t.setFont(QFont("Arial", 7, QFont.Bold))
        t.setPos(cx - bw / 2 + 4, cy - bh / 2 + 2)
        # Temperature label (bottom of box)
        tl = s.addText("—→—°C")
        tl.setDefaultTextColor(QColor(255, 220, 80))
        tl.setFont(QFont("Courier New", 7))
        tl.setPos(cx - bw / 2 + 4, cy + 8)
        self._temp_labels[sid] = tl
        # Sensor dot (right edge)
        dot = s.addEllipse(cx + bw / 2 - 14, cy - 7, 13, 13,
                           QPen(QColor(180, 180, 180), 1),
                           QBrush(QColor(0, 200, 80)))
        self._sensor_items[sid] = dot

    def _draw_valve(self, x, y, sid, facing_right=True):
        """Draw a triangle valve symbol.  facing_right = flow left→right."""
        path = QPainterPath()
        if facing_right:
            path.moveTo(x - _VALVE_R, y - _VALVE_R)
            path.lineTo(x + _VALVE_R, y)
            path.lineTo(x - _VALVE_R, y + _VALVE_R)
        else:
            path.moveTo(x + _VALVE_R, y - _VALVE_R)
            path.lineTo(x - _VALVE_R, y)
            path.lineTo(x + _VALVE_R, y + _VALVE_R)
        path.closeSubpath()
        color = QColor(0, 200, 120)
        item = self.scene.addPath(path, QPen(color, 2), QBrush(color))
        self._valve_items[sid] = item

    def _draw_pipe(self, x1, y1, x2, y2, key, color=None):
        c   = color or QColor(70, 90, 115)
        pen = QPen(c, _PIPE_W, Qt.SolidLine, Qt.RoundCap)
        item = self.scene.addLine(x1, y1, x2, y2, pen)
        self._pipe_items[key] = item
        return item

    def _draw_row0_pipes(self, stages):
        """Pipes for row 0: Source → stage1 → … → stage4."""
        # Start from source right edge
        src_right = _COL_X[0] + 40
        prev_x    = src_right
        prev_y    = _ROW_Y[0]

        for sid, nm, row, col in stages:
            cx      = _COL_X[col]
            cy      = _ROW_Y[row]
            box_left = cx - _BOX_W / 2
            valve_x  = box_left - 24

            # Pipe from previous element to valve
            self._draw_pipe(prev_x, prev_y, valve_x, cy, f'pre_{sid}')
            # Valve
            self._draw_valve(valve_x, cy, sid, facing_right=True)
            # Pipe from valve to box left
            self._draw_pipe(valve_x + _VALVE_R + 3, cy, box_left, cy, f'post_{sid}')

            prev_x = cx + _BOX_W / 2
            prev_y = cy

        # Pipe from last stage right → U-bend top
        self._draw_pipe(prev_x, prev_y, _BEND_X, _ROW_Y[0], 'to_bend_h')

    def _draw_ubend(self):
        # Vertical bend
        corner_top = (_BEND_X, _ROW_Y[0])
        corner_bot = (_BEND_X, _ROW_Y[1])
        self._draw_pipe(_BEND_X, _ROW_Y[0], _BEND_X, _ROW_Y[1], 'bend_v',
                        color=QColor(50, 80, 110))
        # Corner indicator
        self.scene.addEllipse(_BEND_X - 6, _ROW_Y[0] - 6, 12, 12,
                               QPen(QColor(0, 200, 140), 2),
                               QBrush(QColor(0, 160, 100)))
        self.scene.addEllipse(_BEND_X - 6, _ROW_Y[1] - 6, 12, 12,
                               QPen(QColor(0, 200, 140), 2),
                               QBrush(QColor(0, 160, 100)))

    def _draw_row1_pipes(self, stages):
        """Pipes for row 1: right→left  (Fish Pond → … → Green House → Discharge)."""
        # Row 1 stages sorted descending by col (highest col first = rightmost first)
        ordered = sorted(stages, key=lambda x: -x[3])

        prev_x = _BEND_X
        prev_y = _ROW_Y[1]

        for sid, nm, row, col in ordered:
            cx       = _COL_X[col]
            cy       = _ROW_Y[row]
            box_right = cx + _BOX_W / 2
            valve_x   = box_right + 22

            # Pipe from previous to valve
            self._draw_pipe(prev_x, prev_y, valve_x, cy, f'pre_{sid}')
            # Valve (facing left = flow going left)
            self._draw_valve(valve_x, cy, sid, facing_right=False)
            # Pipe from valve to box right
            self._draw_pipe(valve_x - _VALVE_R - 3, cy, box_right, cy, f'post_{sid}')

            prev_x = cx - _BOX_W / 2
            prev_y = cy

        # Final pipe to Discharge right edge
        disch_right = _COL_X[1] + 38
        self._draw_pipe(prev_x, prev_y, disch_right, _ROW_Y[1], 'to_discharge')

    def _fit_view(self):
        rect = self.scene.sceneRect().adjusted(-15, -15, 15, 15)
        self.view.fitInView(rect, Qt.KeepAspectRatio)

    # ── update API ────────────────────────────────────────────────────────────

    def update_valve_position(self, sid: str, position: float):
        if sid in self._valve_items:
            c = self._valve_color(position)
            it = self._valve_items[sid]
            it.setBrush(QBrush(c))
            it.setPen(QPen(c, 2))

    def update_sensor_status(self, sid: str, color_tuple):
        if sid in self._sensor_items:
            r, g, b = color_tuple
            self._sensor_items[sid].setBrush(QBrush(QColor(int(r), int(g), int(b))))

    def update_stage_temps(self, sensor_data: dict):
        """Update temperature labels and pipe colour from sensor data."""
        # Map stage_id → inlet temp for pipe colouring
        stage_order = ['cabin', 'hot_pool', 'tea_dryer', 'food_dehydrator_1',
                       'fish_pond', 'food_dehydrator_2', 'green_house']
        for sid in stage_order:
            if sid not in sensor_data:
                continue
            d     = sensor_data[sid]
            t_in  = d.get('inlet_temp', 0)
            t_out = d.get('outlet_temp', 0)
            # Label
            if sid in self._temp_labels:
                self._temp_labels[sid].setPlainText(f"{t_in:.0f}→{t_out:.0f}°C")
                self._temp_labels[sid].setDefaultTextColor(_temp_color(t_in))
            # Colour the incoming pipe
            key = f'pre_{sid}'
            if key in self._pipe_items:
                c   = _temp_color(t_in)
                pen = QPen(c, _PIPE_W, Qt.SolidLine, Qt.RoundCap)
                self._pipe_items[key].setPen(pen)

    # ── helpers ───────────────────────────────────────────────────────────────

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
