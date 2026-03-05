"""
Gauge Widget
Custom circular gauge for displaying pressure, temperature, etc.
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient, QRadialGradient
import math

class Gauge(QWidget):
    """
    Circular gauge widget with customizable range and colors
    """
    
    def __init__(self, parent=None, min_value=0, max_value=100, 
                 unit="", label="", warning_threshold=None, critical_threshold=None):
        """
        Initialize gauge
        
        Args:
            parent: Parent widget
            min_value: Minimum value
            max_value: Maximum value
            unit: Unit string (e.g., "bar", "°C")
            label: Label text
            warning_threshold: Warning level (yellow)
            critical_threshold: Critical level (red)
        """
        super().__init__(parent)
        
        self.min_value = min_value
        self.max_value = max_value
        self.value = min_value
        self.unit = unit
        self.label = label
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        
        # Visual settings – no fixed minimum so parent layout controls sizing
        self.setMinimumSize(60, 60)
        self.needle_color = QColor(255, 255, 255)
        
    def set_value(self, value):
        """Update gauge value"""
        self.value = max(self.min_value, min(self.max_value, value))
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        """Draw the gauge"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get dimensions
        width = self.width()
        height = self.height()
        side = min(width, height)
        
        # Center point
        center = QPointF(width / 2, height / 2)
        
        # Draw outer circle (frame)
        painter.setPen(QPen(QColor(100, 100, 100), 3))
        painter.setBrush(QColor(40, 40, 40))
        radius = side / 2 - 10
        painter.drawEllipse(center, radius, radius)
        
        # Draw gauge arc background
        painter.setPen(QPen(QColor(60, 60, 60), 8))
        rect = QRectF(center.x() - radius + 10, center.y() - radius + 10,
                      (radius - 10) * 2, (radius - 10) * 2)
        start_angle = 225 * 16  # Start at bottom-left
        span_angle = -270 * 16  # 270 degrees clockwise
        painter.drawArc(rect, start_angle, span_angle)
        
        # Draw colored arc based on value
        value_color = self._get_value_color()
        painter.setPen(QPen(value_color, 8))
        
        # Calculate angle for current value
        value_ratio = (self.value - self.min_value) / (self.max_value - self.min_value)
        value_span = -270 * 16 * value_ratio
        painter.drawArc(rect, start_angle, int(value_span))
        
        # Draw warning zones if defined
        if self.warning_threshold or self.critical_threshold:
            self._draw_warning_zones(painter, center, radius, rect, start_angle)
        
        # Draw tick marks
        self._draw_ticks(painter, center, radius)
        
        # Draw needle
        self._draw_needle(painter, center, radius - 20)
        
        # Draw center circle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(80, 80, 80))
        painter.drawEllipse(center, 8, 8)
        
        # Draw value text
        self._draw_value_text(painter, center)
        
        # Draw label
        self._draw_label(painter, width, height)
    
    def _get_value_color(self):
        """Get color based on value and thresholds"""
        if self.critical_threshold and self.value >= self.critical_threshold:
            return QColor(255, 50, 50)  # Red
        elif self.warning_threshold and self.value >= self.warning_threshold:
            return QColor(255, 200, 0)  # Yellow
        else:
            return QColor(0, 255, 150)  # Green
    
    def _draw_warning_zones(self, painter, center, radius, rect, start_angle):
        """Draw warning and critical zones on arc"""
        if self.warning_threshold:
            warn_ratio = (self.warning_threshold - self.min_value) / (self.max_value - self.min_value)
            warn_angle = start_angle + int(-270 * 16 * warn_ratio)
            
            painter.setPen(QPen(QColor(255, 200, 0, 100), 6))
            warn_span = int(-270 * 16 * (1 - warn_ratio))
            if self.critical_threshold:
                crit_ratio = (self.critical_threshold - self.min_value) / (self.max_value - self.min_value)
                warn_span = int(-270 * 16 * (crit_ratio - warn_ratio))
            
            painter.drawArc(rect, warn_angle, warn_span)
        
        if self.critical_threshold:
            crit_ratio = (self.critical_threshold - self.min_value) / (self.max_value - self.min_value)
            crit_angle = start_angle + int(-270 * 16 * crit_ratio)
            crit_span = int(-270 * 16 * (1 - crit_ratio))
            
            painter.setPen(QPen(QColor(255, 50, 50, 100), 6))
            painter.drawArc(rect, crit_angle, crit_span)
    
    def _draw_ticks(self, painter, center, radius):
        """Draw tick marks"""
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        
        num_ticks = 11  # 0, 10, 20, ..., 100%
        for i in range(num_ticks):
            ratio = i / (num_ticks - 1)
            angle = 225 - (270 * ratio)  # Start at 225°, go to -45°
            angle_rad = math.radians(angle)
            
            # Outer point
            outer_x = center.x() + (radius - 15) * math.cos(angle_rad)
            outer_y = center.y() - (radius - 15) * math.sin(angle_rad)
            
            # Inner point (shorter for minor ticks)
            tick_length = 10 if i % 2 == 0 else 5
            inner_x = center.x() + (radius - 15 - tick_length) * math.cos(angle_rad)
            inner_y = center.y() - (radius - 15 - tick_length) * math.sin(angle_rad)
            
            painter.drawLine(int(outer_x), int(outer_y), int(inner_x), int(inner_y))
    
    def _draw_needle(self, painter, center, length):
        """Draw needle pointing to current value"""
        value_ratio = (self.value - self.min_value) / (self.max_value - self.min_value)
        angle = 225 - (270 * value_ratio)
        angle_rad = math.radians(angle)
        
        # Needle end point
        end_x = center.x() + length * math.cos(angle_rad)
        end_y = center.y() - length * math.sin(angle_rad)
        
        # Draw needle
        painter.setPen(QPen(self.needle_color, 3))
        painter.drawLine(center, QPointF(end_x, end_y))
        
        # Draw needle tip
        painter.setBrush(self.needle_color)
        painter.drawEllipse(QPointF(end_x, end_y), 4, 4)
    
    def _draw_value_text(self, painter, center):
        """Draw value text in center"""
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 18, QFont.Bold)
        painter.setFont(font)
        
        text = f"{self.value:.1f}"
        text_rect = QRectF(center.x() - 50, center.y() - 10, 100, 30)
        painter.drawText(text_rect, Qt.AlignCenter, text)
        
        # Draw unit
        font = QFont("Arial", 10)
        painter.setFont(font)
        unit_rect = QRectF(center.x() - 50, center.y() + 15, 100, 20)
        painter.drawText(unit_rect, Qt.AlignCenter, self.unit)
    
    def _draw_label(self, painter, width, height):
        """Draw label at bottom"""
        painter.setPen(QColor(200, 200, 200))
        font = QFont("Arial", 10)
        painter.setFont(font)
        
        label_rect = QRectF(0, height - 25, width, 20)
        painter.drawText(label_rect, Qt.AlignCenter, self.label)

# Test widget
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QVBoxLayout, QSlider
    import sys
    
    app = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout()
    
    # Create gauge
    gauge = Gauge(min_value=0, max_value=15, unit="bar", label="Pressure",
                  warning_threshold=10, critical_threshold=12)
    gauge.set_value(8.2)
    
    # Create slider to test
    slider = QSlider(Qt.Horizontal)
    slider.setMinimum(0)
    slider.setMaximum(150)
    slider.setValue(82)
    slider.valueChanged.connect(lambda v: gauge.set_value(v / 10))
    
    layout.addWidget(gauge)
    layout.addWidget(slider)
    
    window.setLayout(layout)
    window.setStyleSheet("background-color: #2b2b2b;")
    window.resize(300, 400)
    window.show()
    
    sys.exit(app.exec_())