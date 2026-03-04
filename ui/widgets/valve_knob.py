"""
Valve Knob Widget
Rotary knob control for valve position (0-100%)
"""
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush
import math

class ValveKnob(QWidget):
    """
    Rotary knob widget for valve control
    User can click and drag to rotate
    """
    
    # Signal emitted when value changes
    valueChanged = pyqtSignal(float)
    
    def __init__(self, parent=None, label="Valve", initial_value=50.0):
        """
        Initialize valve knob
        
        Args:
            parent: Parent widget
            label: Label text
            initial_value: Initial position (0-100%)
        """
        super().__init__(parent)
        
        self.label_text = label
        self.value = initial_value
        self.min_value = 0.0
        self.max_value = 100.0
        
        # Mouse tracking
        self.is_dragging = False
        self.last_angle = 0
        
        # Visual settings
        self.setMinimumSize(120, 150)
        self.knob_color = QColor(80, 80, 80)
        self.indicator_color = QColor(0, 255, 150)
        
        # Create layout with label
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.value_label = QLabel(f"{self.value:.0f}%")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;")
        
        self.name_label = QLabel(self.label_text)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("color: #aaa; font-size: 9pt;")
        
        layout.addWidget(self.value_label)
        layout.addStretch()
        layout.addWidget(self.name_label)
        
        self.setLayout(layout)
    
    def set_value(self, value):
        """Set knob value (0-100%)"""
        old_value = self.value
        self.value = max(self.min_value, min(self.max_value, value))
        self.value_label.setText(f"{self.value:.0f}%")
        
        if abs(old_value - self.value) > 0.1:
            self.update()
    
    def get_value(self):
        """Get current value"""
        return self.value
    
    def mousePressEvent(self, event):
        """Start dragging"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.last_angle = self._calculate_angle(event.pos())
    
    def mouseMoveEvent(self, event):
        """Handle dragging"""
        if self.is_dragging:
            current_angle = self._calculate_angle(event.pos())
            angle_delta = current_angle - self.last_angle
            
            # Prevent wrap-around
            if abs(angle_delta) < 180:
                # Convert angle delta to value delta
                value_delta = (angle_delta / 270) * (self.max_value - self.min_value)
                new_value = self.value + value_delta
                
                if self.min_value <= new_value <= self.max_value:
                    self.set_value(new_value)
                    self.valueChanged.emit(self.value)
            
            self.last_angle = current_angle
    
    def mouseReleaseEvent(self, event):
        """Stop dragging"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
    
    def wheelEvent(self, event):
        """Handle mouse wheel"""
        delta = event.angleDelta().y() / 120  # Wheel clicks
        value_delta = delta * 5  # 5% per click
        new_value = self.value + value_delta
        
        if self.min_value <= new_value <= self.max_value:
            self.set_value(new_value)
            self.valueChanged.emit(self.value)
    
    def _calculate_angle(self, pos):
        """Calculate angle from center to mouse position"""
        center = QPointF(self.width() / 2, self.height() / 2)
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        angle = math.degrees(math.atan2(dy, dx))
        return angle
    
    def paintEvent(self, event):
        """Draw the knob"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get dimensions
        width = self.width()
        height = self.height()
        side = min(width, height - 40)  # Leave space for labels
        
        # Center point
        center = QPointF(width / 2, (height - 40) / 2)
        
        # Draw outer ring (track)
        painter.setPen(QPen(QColor(60, 60, 60), 6))
        painter.setBrush(Qt.NoBrush)
        radius = side / 2 - 10
        painter.drawEllipse(center, radius, radius)
        
        # Draw value arc
        value_ratio = (self.value - self.min_value) / (self.max_value - self.min_value)
        start_angle = 135 * 16  # Start at bottom-left
        span_angle = int(-270 * 16 * value_ratio)  # 270 degrees total range
        
        painter.setPen(QPen(self.indicator_color, 6))
        from PyQt5.QtCore import QRectF
        rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        painter.drawArc(rect, start_angle, span_angle)
        
        # Draw knob body
        knob_radius = radius - 15
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(self.knob_color)
        painter.drawEllipse(center, knob_radius, knob_radius)
        
        # Draw indicator line on knob
        angle = 135 - (270 * value_ratio)  # Position of indicator
        angle_rad = math.radians(angle)
        
        indicator_start = knob_radius * 0.3
        indicator_end = knob_radius * 0.8
        
        start_x = center.x() + indicator_start * math.cos(angle_rad)
        start_y = center.y() - indicator_start * math.sin(angle_rad)
        end_x = center.x() + indicator_end * math.cos(angle_rad)
        end_y = center.y() - indicator_end * math.sin(angle_rad)
        
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))
        
        # Draw center dot
        painter.setBrush(QColor(200, 200, 200))
        painter.drawEllipse(center, 5, 5)
        
        # Draw tick marks
        self._draw_ticks(painter, center, radius)
    
    def _draw_ticks(self, painter, center, radius):
        """Draw position tick marks"""
        painter.setPen(QPen(QColor(120, 120, 120), 2))
        
        # Draw ticks at 0%, 25%, 50%, 75%, 100%
        positions = [0, 0.25, 0.5, 0.75, 1.0]
        
        for pos in positions:
            angle = 135 - (270 * pos)
            angle_rad = math.radians(angle)
            
            outer_x = center.x() + (radius + 5) * math.cos(angle_rad)
            outer_y = center.y() - (radius + 5) * math.sin(angle_rad)
            inner_x = center.x() + (radius - 2) * math.cos(angle_rad)
            inner_y = center.y() - (radius - 2) * math.sin(angle_rad)
            
            painter.drawLine(int(outer_x), int(outer_y), int(inner_x), int(inner_y))

# Test widget
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QHBoxLayout
    import sys
    
    app = QApplication(sys.argv)
    
    window = QWidget()
    layout = QHBoxLayout()
    
    # Create multiple knobs
    knob1 = ValveKnob(label="Food Dryer", initial_value=65)
    knob2 = ValveKnob(label="Hot Pool", initial_value=80)
    knob3 = ValveKnob(label="Tea Dryer", initial_value=55)
    
    knob1.valueChanged.connect(lambda v: print(f"Food Dryer: {v:.1f}%"))
    
    layout.addWidget(knob1)
    layout.addWidget(knob2)
    layout.addWidget(knob3)
    
    window.setLayout(layout)
    window.setStyleSheet("background-color: #2b2b2b;")
    window.resize(400, 200)
    window.show()
    
    sys.exit(app.exec_())