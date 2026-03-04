"""
Geothermal Direct Use Simulator
PT Geo Dipa Energi (Persero) - Unit Patuha

Main entry point for the application
Run with: python main.py
"""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt, QTimer

from ui.main_window import MainWindow
from simulation.simulator import GeothermalSimulator

def setup_dark_theme(app):
    """Setup dark theme for the application"""
    app.setStyle('Fusion')
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(40, 40, 40))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(40, 40, 40))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    
    app.setPalette(palette)

def main():
    """Main application entry point"""
    print("=" * 60)
    print("Geothermal Direct Use Simulator")
    print("PT Geo Dipa Energi (Persero) - Unit Patuha")
    print("=" * 60)
    print("\nStarting application...")
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Geothermal Direct Use Simulator")
    
    # Setup dark theme
    setup_dark_theme(app)
    
    # Create simulator
    print("Initializing simulator...")
    simulator = GeothermalSimulator()
    
    # Create main window
    print("Creating main window...")
    window = MainWindow()
    window.set_simulator(simulator)
    
    # Connect simulator update to window
    # This will be called by window's internal timer
    def update_simulator():
        simulator.update()
    
    # Create timer for simulator updates (independent from UI updates)
    sim_timer = QTimer()
    sim_timer.timeout.connect(update_simulator)
    sim_timer.start(100)  # 100ms = 10Hz
    
    # Show window
    print("Launching UI...")
    window.show()
    
    print("\n[OK] Application started successfully!")
    print("=" * 60)
    print("\nControls:")
    print("  - Use valve knobs to manually control valves (when auto-control is OFF)")
    print("  - Click scenario buttons to trigger events")
    print("  - Toggle 'Auto Control' to enable/disable automatic valve adjustment")
    print("  - Press 'Emergency Stop' for immediate shutdown")
    print("  - Press 'Reset All' to return to normal operation")
    print("\n" + "=" * 60)
    
    # Run application
    exit_code = app.exec_()
    
    print("\nApplication closed. Exit code:", exit_code)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()