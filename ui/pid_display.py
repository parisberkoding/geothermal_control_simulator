"""
P&ID Display Widget
Simplified P&ID diagram showing steam flow from Well DP-6 to applications
"""
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QGraphicsItem
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

class PIDDisplay(QWidget):
    """
    P&ID Diagram Display
    Shows simplified process flow diagram
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create graphics scene
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        
        # Create graphics view
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Valve indicators (will be updated)
        self.valve_indicators = {}
        
        # Sensor indicators (NEW)
        self.sensor_indicators = {}
        
        # Flow animation
        self.flow_offset = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_flow)
        self.animation_timer.start(50)  # 20 FPS
        
        # Build diagram
        self._build_diagram()
        
        # Layout
        from PyQt5.QtWidgets import QVBoxLayout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)
    
    def _build_diagram(self):
        """Build the P&ID diagram"""
        # Define positions (relative coordinates)
        well_x, well_y = 50, 150
        separator_x, separator_y = 200, 150
        junction_x, junction_y = 350, 150
        
        # Application endpoints (right side)
        apps_x = 500
        apps = [
            ("Food Dehydrator", 50),
            ("Hot Pool", 100),
            ("Tea Dryer", 150),
            ("Cabin", 200),
            ("Green House", 250),
            ("Fishery Pond", 300)
        ]
        
        # 1. Draw Well DP-6
        self._draw_well(well_x, well_y)
        
        # 2. Draw pipe from well to separator
        self._draw_pipe(well_x + 40, well_y, separator_x - 40, separator_y, "main")
        
        # 3. Draw Separator (ADL-1)
        self._draw_separator(separator_x, separator_y)
        
        # 4. Draw pipe from separator to junction
        self._draw_pipe(separator_x + 40, separator_y, junction_x - 20, junction_y, "main")
        
        # 5. Draw junction/distribution point
        self._draw_junction(junction_x, junction_y)
        
        # 6. Draw pipes to each application
        for i, (app_name, y_offset) in enumerate(apps):
            app_y = junction_y - 125 + y_offset
            
            # Horizontal pipe from junction to valve
            valve_x = junction_x + 60
            self._draw_pipe(junction_x + 10, junction_y, valve_x, app_y, f"branch_{i}")
            
            # Valve
            valve_id = app_name.lower().replace(" ", "_")
            self._draw_valve(valve_x, app_y, valve_id, 50.0)
            
            # Pipe from valve to application
            self._draw_pipe(valve_x + 20, app_y, apps_x - 40, app_y, f"app_{i}")
            
            # Application endpoint
            self._draw_application(apps_x, app_y, app_name)
        
        # Fit view
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    
    def _draw_well(self, x, y):
        """Draw well symbol"""
        # Rectangle for well
        rect = self.scene.addRect(x - 30, y - 20, 60, 40,
                                   QPen(QColor(150, 150, 150), 2),
                                   QBrush(QColor(60, 60, 80)))
        
        # Text label
        text = self.scene.addText("Well\nDP-6")
        text.setDefaultTextColor(QColor(255, 255, 255))
        text.setFont(QFont("Arial", 9, QFont.Bold))
        text.setPos(x - 20, y - 15)
    
    def _draw_separator(self, x, y):
        """Draw separator symbol"""
        # Circle for separator
        circle = self.scene.addEllipse(x - 30, y - 30, 60, 60,
                                        QPen(QColor(150, 150, 150), 2),
                                        QBrush(QColor(70, 70, 90)))
        
        # Text label
        text = self.scene.addText("ADL-1")
        text.setDefaultTextColor(QColor(255, 255, 255))
        text.setFont(QFont("Arial", 9, QFont.Bold))
        text.setPos(x - 20, y - 10)
    
    def _draw_junction(self, x, y):
        """Draw distribution junction"""
        # Small circle
        circle = self.scene.addEllipse(x - 10, y - 10, 20, 20,
                                        QPen(QColor(0, 255, 150), 2),
                                        QBrush(QColor(0, 150, 80)))
    
    def _draw_valve(self, x, y, valve_id, position):
        """Draw valve symbol with position indicator"""
        # Valve symbol (triangle)
        path = QPainterPath()
        path.moveTo(x - 10, y - 10)
        path.lineTo(x + 10, y)
        path.lineTo(x - 10, y + 10)
        path.closeSubpath()
        
        # Color based on position
        color = self._get_valve_color(position)
        valve_item = self.scene.addPath(path, QPen(color, 2), QBrush(color))
        
        # Store reference
        self.valve_indicators[valve_id] = valve_item
    
    def _draw_pipe(self, x1, y1, x2, y2, pipe_id):
        """Draw pipe with flow animation"""
        # Main pipe line
        pen = QPen(QColor(100, 100, 100), 3)
        self.scene.addLine(x1, y1, x2, y2, pen)
        
        # Flow direction indicator (dashed line on top)
        flow_pen = QPen(QColor(0, 200, 255), 2)
        flow_pen.setStyle(Qt.DashLine)
        flow_line = self.scene.addLine(x1, y1, x2, y2, flow_pen)
        flow_line.setZValue(1)  # On top
    
    def _draw_application(self, x, y, name):
        """Draw application endpoint with sensor"""
        # Rectangle for application
        rect = self.scene.addRect(x - 50, y - 15, 100, 30,
                                   QPen(QColor(150, 150, 150), 2),
                                   QBrush(QColor(50, 70, 90)))
        
        # Text label
        text = self.scene.addText(name)
        text.setDefaultTextColor(QColor(255, 255, 255))
        text.setFont(QFont("Arial", 8))
        text.setPos(x - 45, y - 10)
        
        # Sensor circle (NEW) - positioned to the right of application box
        sensor_x = x + 55
        sensor_y = y
        sensor = self.scene.addEllipse(sensor_x - 8, sensor_y - 8, 16, 16,
                                        QPen(QColor(200, 200, 200), 2),
                                        QBrush(QColor(0, 255, 100)))  # Default green
        
        # Store sensor reference (extract valve_id from name)
        valve_id = name.lower().replace(" ", "_").replace("leaves_", "")
        self.sensor_indicators[valve_id] = sensor
    
    def _get_valve_color(self, position):
        """Get valve color based on position"""
        if position < 20:
            return QColor(255, 100, 100)  # Red (mostly closed)
        elif position < 40:
            return QColor(255, 200, 0)     # Yellow
        else:
            return QColor(0, 255, 150)     # Green (open)
    
    def update_valve_position(self, valve_id, position):
        """
        Update valve indicator color based on position
        
        Args:
            valve_id: Valve identifier
            position: Valve position (0-100%)
        """
        if valve_id in self.valve_indicators:
            color = self._get_valve_color(position)
            item = self.valve_indicators[valve_id]
            item.setBrush(QBrush(color))
            item.setPen(QPen(color, 2))
    
    def update_sensor_status(self, valve_id, color_tuple):
        """
        Update sensor indicator color
        
        Args:
            valve_id: Valve/endpoint identifier
            color_tuple: RGB color tuple (r, g, b)
        """
        if valve_id in self.sensor_indicators:
            r, g, b = color_tuple
            color = QColor(int(r), int(g), int(b))
            item = self.sensor_indicators[valve_id]
            item.setBrush(QBrush(color))
            item.setPen(QPen(QColor(200, 200, 200), 2))
    
    def _animate_flow(self):
        """Animate flow in pipes (visual effect)"""
        self.flow_offset += 2
        if self.flow_offset > 20:
            self.flow_offset = 0
        # Could implement actual dash animation here
    
    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

# Test widget
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    window = PIDDisplay()
    window.resize(800, 600)
    window.show()
    
    # Test valve update
    import random
    def test_update():
        for valve in window.valve_indicators.keys():
            pos = random.uniform(0, 100)
            window.update_valve_position(valve, pos)
    
    timer = QTimer()
    timer.timeout.connect(test_update)
    timer.start(1000)
    
    sys.exit(app.exec_())