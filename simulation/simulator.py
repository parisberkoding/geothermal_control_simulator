"""
Main Simulator
Orchestrates steam source, valve controller, and endpoints
Provides unified interface for UI
"""
import time
from simulation.steam_source import SteamSource, SystemState
from simulation.valve_controller import ValveController
from simulation.endpoints import EndpointManager

class GeothermalSimulator:
    """
    Main simulator that orchestrates all components
    """
    
    def __init__(self):
        # Components
        self.steam_source = SteamSource()
        self.valve_controller = ValveController()
        self.endpoint_manager = EndpointManager()
        
        # Timing
        self.last_update = time.time()
        
        # State tracking
        self.is_running = True
    
    def update(self):
        """
        Update simulation (called every frame)
        """
        if not self.is_running:
            return
        
        # Calculate delta time
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        # Clamp dt to prevent huge jumps
        dt = min(dt, 0.5)
        
        # Update steam source
        self.steam_source.update(dt)
        
        # Get current conditions
        current_pressure = self.steam_source.pressure
        current_flow = self.steam_source.flow
        valve_positions = self.valve_controller.get_all_positions()
        
        # Update endpoints with current valve positions and flow
        self.endpoint_manager.update(dt, valve_positions, current_flow)
        
        # Update valve controller (global pressure control)
        self.valve_controller.update(dt, current_pressure)
        
        # Apply endpoint-specific adjustments (individual auto-tune)
        if self.valve_controller.auto_control_enabled:
            sensor_status = self.endpoint_manager.get_all_sensor_status()
            for endpoint_id, status in sensor_status.items():
                if status['needs_adjustment']:
                    adjustment = status['recommended_adjustment']
                    self.valve_controller.apply_endpoint_adjustment(endpoint_id, adjustment)
    
    def get_state(self):
        """
        Get current system state for UI
        
        Returns:
            dict: Current state data
        """
        steam_info = self.steam_source.get_state_info()
        
        return {
            'pressure': steam_info['pressure'],
            'temperature': steam_info['temperature'],
            'flow': steam_info['flow'],
            'state': steam_info['state'],
            'disturbance_active': steam_info['disturbance_active'],
            'valve_positions': self.valve_controller.get_all_positions(),
            'valve_auto_tune': self.valve_controller.get_all_auto_tune_status(),
            'auto_control_enabled': self.valve_controller.auto_control_enabled,
            'last_control_action': self.valve_controller.last_action,
            'endpoint_sensors': self.endpoint_manager.get_all_sensor_status()
        }
    
    def reset(self):
        """Reset simulator to normal operation"""
        self.steam_source.reset()
        self.valve_controller.reset_all_valves()
        self.is_running = True
    
    def emergency_shutdown(self):
        """Trigger emergency shutdown"""
        self.steam_source.trigger_emergency()
        self.valve_controller.emergency_close_all()
    
    def set_valve_position(self, valve_id, position):
        """
        Manually set valve position (when auto-control is off)
        
        Args:
            valve_id: Valve identifier
            position: Position 0-100%
        """
        self.valve_controller.set_valve_position(valve_id, position)
    
    def toggle_auto_control(self, enabled):
        """Enable/disable auto-control"""
        self.valve_controller.auto_control_enabled = enabled

# Test simulator standalone
if __name__ == '__main__':
    print("Testing Geothermal Simulator...")
    sim = GeothermalSimulator()
    
    print("\nInitial state:")
    state = sim.get_state()
    print(f"  Pressure: {state['pressure']:.2f} bar")
    print(f"  Temperature: {state['temperature']:.2f}°C")
    print(f"  Flow: {state['flow']:.0f} kg/h")
    print(f"  State: {state['state']}")
    
    print("\nSimulating 60 seconds...")
    import time as pytime
    start = pytime.time()
    
    while pytime.time() - start < 60:
        sim.update()
        pytime.sleep(0.1)
        
        # Print every 5 seconds
        elapsed = pytime.time() - start
        if int(elapsed) % 5 == 0 and int(elapsed * 10) % 50 == 0:
            state = sim.get_state()
            print(f"\n[{elapsed:.1f}s] State: {state['state']}")
            print(f"  P: {state['pressure']:.2f} bar")
            print(f"  T: {state['temperature']:.2f}°C")
            print(f"  F: {state['flow']:.0f} kg/h")
            if state['last_control_action']:
                print(f"  Action: {state['last_control_action']}")
    
    print("\n✅ Simulation test completed!")