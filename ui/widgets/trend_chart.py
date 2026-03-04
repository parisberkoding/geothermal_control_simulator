"""
Trend Chart Widget
Real-time scrolling chart for monitoring parameters
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from collections import deque
import time

class TrendChart(QWidget):
    """
    Real-time scrolling chart widget
    """
    
    def __init__(self, parent=None, title="Parameter", unit="", 
                 y_min=0, y_max=100, window_size=60, color=(0, 255, 150)):
        """
        Initialize trend chart
        
        Args:
            parent: Parent widget
            title: Chart title
            unit: Y-axis unit
            y_min: Minimum Y value
            y_max: Maximum Y value
            window_size: Time window in seconds
            color: Line color (R, G, B)
        """
        super().__init__(parent)
        
        self.title = title
        self.unit = unit
        self.y_min = y_min
        self.y_max = y_max
        self.window_size = window_size
        self.color = color
        
        # Data storage
        self.timestamps = deque(maxlen=1000)
        self.values = deque(maxlen=1000)
        self.start_time = time.time()
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup chart UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title label
        title_label = QLabel(f"{self.title} ({self.unit})")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white; font-size: 10pt; font-weight: bold;")
        
        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1a1a1a')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Configure axes
        self.plot_widget.setLabel('left', self.unit)
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.setYRange(self.y_min, self.y_max)
        self.plot_widget.setXRange(0, self.window_size)
        
        # Style
        styles = {'color': '#888', 'font-size': '10pt'}
        self.plot_widget.setLabel('left', self.unit, **styles)
        self.plot_widget.setLabel('bottom', 'Time (s)', **styles)
        
        # Create plot curve
        pen = pg.mkPen(color=self.color, width=2)
        self.curve = self.plot_widget.plot([], [], pen=pen)
        
        # Add warning/critical zones if needed
        self._add_threshold_regions()
        
        layout.addWidget(title_label)
        layout.addWidget(self.plot_widget)
        
        self.setLayout(layout)
    
    def _add_threshold_regions(self):
        """Add colored regions for warning/critical zones"""
        # This can be customized per chart type
        pass
    
    def add_data_point(self, value):
        """
        Add new data point
        
        Args:
            value: Value to add
        """
        current_time = time.time() - self.start_time
        self.timestamps.append(current_time)
        self.values.append(value)
        
        # Update plot
        self._update_plot()
    
    def _update_plot(self):
        """Update the plot with current data"""
        if len(self.timestamps) > 0:
            # Convert to lists
            times = list(self.timestamps)
            values = list(self.values)
            
            # Update curve
            self.curve.setData(times, values)
            
            # Auto-scroll X axis
            if times[-1] > self.window_size:
                self.plot_widget.setXRange(times[-1] - self.window_size, times[-1])
    
    def clear_data(self):
        """Clear all data"""
        self.timestamps.clear()
        self.values.clear()
        self.start_time = time.time()
        self.curve.setData([], [])
    
    def set_y_range(self, y_min, y_max):
        """Update Y axis range"""
        self.y_min = y_min
        self.y_max = y_max
        self.plot_widget.setYRange(y_min, y_max)

class PressureChart(TrendChart):
    """Specialized chart for pressure with warning zones"""
    
    def __init__(self, parent=None):
        super().__init__(
            parent=parent,
            title="Pressure",
            unit="bar",
            y_min=0,
            y_max=15,
            window_size=60,
            color=(0, 255, 150)
        )
    
    def _add_threshold_regions(self):
        """Add pressure warning zones"""
        # Warning zone (10-12 bar) - Yellow
        warning_region = pg.LinearRegionItem(
            values=[10, 12],
            orientation='horizontal',
            brush=pg.mkBrush(255, 200, 0, 50),
            movable=False
        )
        self.plot_widget.addItem(warning_region)
        
        # Critical zone (12-15 bar) - Red
        critical_region = pg.LinearRegionItem(
            values=[12, 15],
            orientation='horizontal',
            brush=pg.mkBrush(255, 50, 50, 50),
            movable=False
        )
        self.plot_widget.addItem(critical_region)
        
        # Low pressure zone (0-6 bar) - Blue
        low_region = pg.LinearRegionItem(
            values=[0, 6],
            orientation='horizontal',
            brush=pg.mkBrush(50, 150, 255, 50),
            movable=False
        )
        self.plot_widget.addItem(low_region)

class TemperatureChart(TrendChart):
    """Specialized chart for temperature"""
    
    def __init__(self, parent=None):
        super().__init__(
            parent=parent,
            title="Temperature",
            unit="°C",
            y_min=150,
            y_max=200,
            window_size=60,
            color=(255, 150, 0)
        )

class FlowChart(TrendChart):
    """Specialized chart for flow rate"""
    
    def __init__(self, parent=None):
        super().__init__(
            parent=parent,
            title="Flow Rate",
            unit="kg/h",
            y_min=0,
            y_max=5000,
            window_size=60,
            color=(100, 200, 255)
        )

# Test widget
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QHBoxLayout
    from PyQt5.QtCore import QTimer
    import sys
    import random
    
    app = QApplication(sys.argv)
    
    window = QWidget()
    layout = QHBoxLayout()
    
    # Create charts
    pressure_chart = PressureChart()
    temp_chart = TemperatureChart()
    flow_chart = FlowChart()
    
    layout.addWidget(pressure_chart)
    layout.addWidget(temp_chart)
    layout.addWidget(flow_chart)
    
    window.setLayout(layout)
    window.setStyleSheet("background-color: #2b2b2b;")
    window.resize(1200, 300)
    
    # Simulate data updates
    def update_data():
        pressure_chart.add_data_point(8 + random.uniform(-1, 1))
        temp_chart.add_data_point(174 + random.uniform(-3, 3))
        flow_chart.add_data_point(3374 + random.uniform(-200, 200))
    
    timer = QTimer()
    timer.timeout.connect(update_data)
    timer.start(100)  # Update every 100ms
    
    window.show()
    sys.exit(app.exec_())