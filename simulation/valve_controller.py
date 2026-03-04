"""
Valve Controller
Auto-control logic for managing valve positions based on system conditions
"""
from typing import Dict
import random

class Valve:
    """Individual valve representation"""
    
    def __init__(self, name: str, initial_position: float = 50.0):
        """
        Initialize valve
        
        Args:
            name: Valve name/identifier
            initial_position: Initial position (0-100%)
        """
        self.name = name
        self.position = max(0.0, min(100.0, initial_position))  # Clamp 0-100
        self.target_position = self.position
        self.is_open = self.position > 5  # Consider closed if < 5%
        self.auto_tune_enabled = True  # NEW: Individual auto-tune control
    
    def set_position(self, position: float):
        """Set valve position (0-100%)"""
        self.position = max(0.0, min(100.0, position))
        self.is_open = self.position > 5
    
    def set_target(self, target: float):
        """Set target position for smooth movement"""
        self.target_position = max(0.0, min(100.0, target))
    
    def update(self, dt: float, speed: float = 10.0):
        """
        Smooth valve movement towards target
        
        Args:
            dt: Delta time in seconds
            speed: Movement speed (%/second)
        """
        if abs(self.position - self.target_position) > 0.5:
            # Move towards target
            direction = 1 if self.target_position > self.position else -1
            delta = speed * dt * direction
            self.position += delta
            
            # Clamp to target if close enough
            if abs(self.position - self.target_position) < 1.0:
                self.position = self.target_position
            
            # Ensure bounds
            self.position = max(0.0, min(100.0, self.position))
            self.is_open = self.position > 5

class ValveController:
    """
    Controls all valves with auto-control logic
    6 valves for 6 applications based on P&ID
    """
    
    def __init__(self):
        # Create valves for each application
        self.valves = {
            'food_dehydrator': Valve('Food Dehydrator', 65.0),
            'hot_pool': Valve('Hot Pool', 80.0),
            'tea_dryer': Valve('Tea Leaves Dryer', 55.0),
            'cabin': Valve('Cabin Heating', 45.0),
            'green_house': Valve('Green House', 70.0),
            'fishery': Valve('Fishery Pond', 60.0)
        }
        
        # Control parameters
        self.auto_control_enabled = True
        
        # Pressure thresholds (bar)
        self.pressure_normal_low = 7.0
        self.pressure_normal_high = 9.0
        self.pressure_warning_low = 6.0
        self.pressure_warning_high = 10.0
        self.pressure_critical_low = 5.0
        self.pressure_critical_high = 12.0
        
        # Control state
        self.last_action = None
        self.action_cooldown = 0
    
    def update(self, dt: float, current_pressure: float):
        """
        Update all valves and apply auto-control
        
        Args:
            dt: Delta time in seconds
            current_pressure: Current system pressure in bar
        """
        # Update valve positions (smooth movement)
        for valve in self.valves.values():
            valve.update(dt)
        
        # Apply auto-control if enabled
        if self.auto_control_enabled:
            self._apply_auto_control(current_pressure, dt)
        
        # Update cooldown
        if self.action_cooldown > 0:
            self.action_cooldown -= dt
    
    def _apply_auto_control(self, pressure: float, dt: float):
        """
        Auto-control logic based on pressure
        
        Args:
            pressure: Current pressure in bar
            dt: Delta time
        """
        # Don't take action if in cooldown
        if self.action_cooldown > 0:
            return
        
        action_taken = False
        
        # CRITICAL HIGH PRESSURE - Emergency throttle
        if pressure > self.pressure_critical_high:
            self._throttle_all_valves(30)  # Close 30%
            self.last_action = f"CRITICAL: Throttled all valves (P={pressure:.2f} bar)"
            self.action_cooldown = 2.0
            action_taken = True
        
        # CRITICAL LOW PRESSURE - Open valves
        elif pressure < self.pressure_critical_low:
            self._open_all_valves(20)  # Open 20%
            self.last_action = f"CRITICAL: Opened all valves (P={pressure:.2f} bar)"
            self.action_cooldown = 2.0
            action_taken = True
        
        # WARNING HIGH PRESSURE - Throttle gradually
        elif pressure > self.pressure_warning_high:
            self._throttle_random_valve(15)  # Close one valve 15%
            self.last_action = f"WARNING: Throttled valve (P={pressure:.2f} bar)"
            self.action_cooldown = 3.0
            action_taken = True
        
        # WARNING LOW PRESSURE - Open gradually
        elif pressure < self.pressure_warning_low:
            self._open_random_valve(10)  # Open one valve 10%
            self.last_action = f"WARNING: Opened valve (P={pressure:.2f} bar)"
            self.action_cooldown = 3.0
            action_taken = True
        
        return action_taken
    
    def _throttle_all_valves(self, percentage: float):
        """Close all valves by percentage"""
        for valve in self.valves.values():
            new_position = max(10, valve.position - percentage)  # Min 10%
            valve.set_target(new_position)
    
    def _open_all_valves(self, percentage: float):
        """Open all valves by percentage"""
        for valve in self.valves.values():
            new_position = min(100, valve.position + percentage)
            valve.set_target(new_position)
    
    def _throttle_random_valve(self, percentage: float):
        """Close one random valve"""
        # Pick valve that's most open
        open_valves = [(k, v) for k, v in self.valves.items() if v.position > 30]
        if open_valves:
            key, valve = max(open_valves, key=lambda x: x[1].position)
            new_position = max(20, valve.position - percentage)
            valve.set_target(new_position)
    
    def _open_random_valve(self, percentage: float):
        """Open one random valve"""
        # Pick valve that's most closed
        closed_valves = [(k, v) for k, v in self.valves.items() if v.position < 80]
        if closed_valves:
            key, valve = min(closed_valves, key=lambda x: x[1].position)
            new_position = min(90, valve.position + percentage)
            valve.set_target(new_position)
    
    def set_valve_position(self, valve_name: str, position: float):
        """
        Manually set valve position
        
        Args:
            valve_name: Name of valve
            position: Target position (0-100%)
        """
        if valve_name in self.valves:
            self.valves[valve_name].set_target(position)
    
    def get_valve_position(self, valve_name: str) -> float:
        """Get current valve position"""
        if valve_name in self.valves:
            return self.valves[valve_name].position
        return 0.0
    
    def get_all_positions(self) -> Dict[str, float]:
        """Get all valve positions"""
        return {name: valve.position for name, valve in self.valves.items()}
    
    def emergency_close_all(self):
        """Emergency close all valves"""
        for valve in self.valves.values():
            valve.set_target(0)
    
    def reset_all_valves(self):
        """Reset all valves to default positions"""
        defaults = {
            'food_dehydrator': 65.0,
            'hot_pool': 80.0,
            'tea_dryer': 55.0,
            'cabin': 45.0,
            'green_house': 70.0,
            'fishery': 60.0
        }
        for name, position in defaults.items():
            self.valves[name].set_target(position)
    
    def set_valve_auto_tune(self, valve_name: str, enabled: bool):
        """
        Enable/disable auto-tune for specific valve
        
        Args:
            valve_name: Name of valve
            enabled: True to enable auto-tune, False to disable
        """
        if valve_name in self.valves:
            self.valves[valve_name].auto_tune_enabled = enabled
    
    def get_valve_auto_tune(self, valve_name: str) -> bool:
        """Get auto-tune status for valve"""
        if valve_name in self.valves:
            return self.valves[valve_name].auto_tune_enabled
        return False
    
    def get_all_auto_tune_status(self) -> Dict[str, bool]:
        """Get auto-tune status for all valves"""
        return {name: valve.auto_tune_enabled for name, valve in self.valves.items()}
    
    def apply_endpoint_adjustment(self, valve_name: str, adjustment: float):
        """
        Apply adjustment from endpoint sensor (only if auto-tune enabled)
        
        Args:
            valve_name: Name of valve
            adjustment: Position adjustment (%)
        """
        if valve_name in self.valves:
            valve = self.valves[valve_name]
            if valve.auto_tune_enabled and self.auto_control_enabled:
                new_position = max(10, min(100, valve.position + adjustment))
                valve.set_target(new_position)

# Test
if __name__ == '__main__':
    print("Testing Valve Controller...")
    controller = ValveController()
    
    print("\nInitial valve positions:")
    for name, pos in controller.get_all_positions().items():
        print(f"  {name}: {pos:.1f}%")
    
    print("\nSimulating high pressure (11 bar)...")
    controller.update(0.1, 11.0)
    print(f"Action: {controller.last_action}")
    
    # Let valves move
    for _ in range(20):
        controller.update(0.1, 11.0)
    
    print("\nValve positions after auto-control:")
    for name, pos in controller.get_all_positions().items():
        print(f"  {name}: {pos:.1f}%")