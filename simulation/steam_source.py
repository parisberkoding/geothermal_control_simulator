"""
Steam Source Simulator
Simulates Well DP-6 with realistic behavior:
- Hold stable values for 10-20 seconds
- Random disturbances (spike/drop)
- Auto-recovery logic
"""
import random
import time
from enum import Enum
from utils.steam_props import SteamProperties

class SystemState(Enum):
    """System operating states"""
    NORMAL = "NORMAL"
    DISTURBANCE_SPIKE = "PRESSURE_SPIKE"
    DISTURBANCE_DROP = "PRESSURE_DROP"
    DISTURBANCE_FLOW = "FLOW_SURGE"
    STABILIZING = "STABILIZING"
    EMERGENCY = "EMERGENCY"

class SteamSource:
    """
    Simulates geothermal well DP-6 steam source
    Implements the random hold + disturbance logic
    """
    
    def __init__(self):
        # Base values from P&ID
        self.base_pressure = 8.0      # bar
        self.base_temperature = 174.0  # °C
        self.base_flow = 3374.0        # kg/h
        
        # Current values
        self.pressure = self.base_pressure
        self.temperature = self.base_temperature
        self.flow = self.base_flow
        
        # State management
        self.state = SystemState.NORMAL
        self.state_timer = 0
        self.hold_duration = random.uniform(10, 20)  # seconds
        self.last_update = time.time()
        
        # Disturbance parameters
        self.disturbance_active = False
        self.disturbance_timer = 0
        self.disturbance_duration = 0
        self.recovery_timer = 0
        
        # Variation (natural fluctuation even in normal state)
        self.pressure_noise = 0
        self.temp_noise = 0
        self.flow_noise = 0
    
    def update(self, dt: float):
        """
        Update steam source state
        
        Args:
            dt: Delta time in seconds since last update
        """
        self.state_timer += dt
        
        if self.state == SystemState.NORMAL:
            self._update_normal(dt)
        elif self.state == SystemState.DISTURBANCE_SPIKE:
            self._update_spike(dt)
        elif self.state == SystemState.DISTURBANCE_DROP:
            self._update_drop(dt)
        elif self.state == SystemState.DISTURBANCE_FLOW:
            self._update_flow_surge(dt)
        elif self.state == SystemState.STABILIZING:
            self._update_stabilizing(dt)
        elif self.state == SystemState.EMERGENCY:
            self._update_emergency(dt)
        
        # Update temperature based on pressure (saturation relationship)
        self._update_temperature()
        
        self.last_update = time.time()
    
    def _update_normal(self, dt):
        """Normal operation with small random variations"""
        # Small random noise (±2%)
        self.pressure_noise = random.uniform(-0.16, 0.16)  # ±2% of 8 bar
        self.temp_noise = random.uniform(-3, 3)
        self.flow_noise = random.uniform(-67, 67)  # ±2% of 3374
        
        self.pressure = self.base_pressure + self.pressure_noise
        self.flow = self.base_flow + self.flow_noise
        
        # Check if hold duration expired
        if self.state_timer >= self.hold_duration:
            # Roll for disturbance (10% chance total)
            roll = random.random()
            
            if roll < 0.05:  # 5% chance - Pressure spike
                self._trigger_spike()
            elif roll < 0.10:  # 5% chance - Pressure drop
                self._trigger_drop()
            elif roll < 0.13:  # 3% chance - Flow surge
                self._trigger_flow_surge()
            else:
                # No disturbance, reset timer
                self.state_timer = 0
                self.hold_duration = random.uniform(10, 20)
    
    def _trigger_spike(self):
        """Trigger pressure spike event"""
        self.state = SystemState.DISTURBANCE_SPIKE
        self.disturbance_active = True
        self.disturbance_duration = random.uniform(5, 15)  # 5-15 seconds
        self.disturbance_timer = 0
        self.state_timer = 0
        
        # Spike magnitude: +40-60%
        spike_factor = random.uniform(1.4, 1.6)
        self.pressure = self.base_pressure * spike_factor
    
    def _trigger_drop(self):
        """Trigger pressure drop event"""
        self.state = SystemState.DISTURBANCE_DROP
        self.disturbance_active = True
        self.disturbance_duration = random.uniform(10, 20)  # 10-20 seconds
        self.disturbance_timer = 0
        self.state_timer = 0
        
        # Drop magnitude: -30-40%
        drop_factor = random.uniform(0.6, 0.7)
        self.pressure = self.base_pressure * drop_factor
        self.flow = self.base_flow * 0.8  # Flow also drops
    
    def _trigger_flow_surge(self):
        """Trigger flow surge event"""
        self.state = SystemState.DISTURBANCE_FLOW
        self.disturbance_active = True
        self.disturbance_duration = random.uniform(8, 12)  # 8-12 seconds
        self.disturbance_timer = 0
        self.state_timer = 0
        
        # Surge magnitude: +50-80%
        surge_factor = random.uniform(1.5, 1.8)
        self.flow = self.base_flow * surge_factor
        self.pressure = self.base_pressure * 1.2  # Slight pressure increase
    
    def _update_spike(self, dt):
        """Update during pressure spike"""
        self.disturbance_timer += dt
        
        if self.disturbance_timer >= self.disturbance_duration:
            # Start recovery
            self._start_stabilizing()
        else:
            # Maintain spike with small variation
            progress = self.disturbance_timer / self.disturbance_duration
            spike_factor = random.uniform(1.4, 1.6)
            noise = random.uniform(-0.1, 0.1)
            self.pressure = self.base_pressure * spike_factor + noise
    
    def _update_drop(self, dt):
        """Update during pressure drop"""
        self.disturbance_timer += dt
        
        if self.disturbance_timer >= self.disturbance_duration:
            self._start_stabilizing()
        else:
            # Maintain drop with small variation
            drop_factor = random.uniform(0.6, 0.7)
            noise = random.uniform(-0.1, 0.1)
            self.pressure = self.base_pressure * drop_factor + noise
            self.flow = self.base_flow * 0.8
    
    def _update_flow_surge(self, dt):
        """Update during flow surge"""
        self.disturbance_timer += dt
        
        if self.disturbance_timer >= self.disturbance_duration:
            self._start_stabilizing()
        else:
            surge_factor = random.uniform(1.5, 1.8)
            self.flow = self.base_flow * surge_factor
            self.pressure = self.base_pressure * 1.2
    
    def _start_stabilizing(self):
        """Begin stabilization/recovery phase"""
        self.state = SystemState.STABILIZING
        self.recovery_timer = 0
        self.disturbance_active = False
        # Recovery takes 5-10 seconds
        self.disturbance_duration = random.uniform(5, 10)
    
    def _update_stabilizing(self, dt):
        """Gradual return to normal"""
        self.recovery_timer += dt
        progress = min(self.recovery_timer / self.disturbance_duration, 1.0)
        
        # Smooth interpolation back to base values
        self.pressure = self._lerp(self.pressure, self.base_pressure, progress * 0.1)
        self.flow = self._lerp(self.flow, self.base_flow, progress * 0.1)
        
        # Check if stabilized
        if abs(self.pressure - self.base_pressure) < 0.2 and \
           abs(self.flow - self.base_flow) < 50:
            # Back to normal
            self.state = SystemState.NORMAL
            self.state_timer = 0
            self.hold_duration = random.uniform(10, 20)
            self.recovery_timer = 0
    
    def _update_emergency(self, dt):
        """Emergency shutdown state"""
        # Ramp down quickly
        self.pressure = max(0, self.pressure - dt * 2)
        self.flow = max(0, self.flow - dt * 500)
        self.temperature = max(25, self.temperature - dt * 10)
    
    def _update_temperature(self):
        """Update temperature based on pressure (steam table)"""
        if self.state != SystemState.EMERGENCY:
            # Use saturation temperature + superheat
            sat_temp = SteamProperties.get_saturation_temperature(self.pressure)
            self.temperature = sat_temp + self.temp_noise
    
    def _lerp(self, a, b, t):
        """Linear interpolation"""
        return a + (b - a) * t
    
    def trigger_emergency(self):
        """Manually trigger emergency shutdown"""
        self.state = SystemState.EMERGENCY
        self.state_timer = 0
    
    def reset(self):
        """Reset to normal operation"""
        self.state = SystemState.NORMAL
        self.pressure = self.base_pressure
        self.temperature = self.base_temperature
        self.flow = self.base_flow
        self.state_timer = 0
        self.hold_duration = random.uniform(10, 20)
        self.disturbance_active = False
    
    def get_state_info(self):
        """Get current state information"""
        return {
            'state': self.state.value,
            'pressure': self.pressure,
            'temperature': self.temperature,
            'flow': self.flow,
            'disturbance_active': self.disturbance_active,
            'time_in_state': self.state_timer
        }

# Test
if __name__ == '__main__':
    print("Testing Steam Source Simulator...")
    source = SteamSource()
    
    print(f"Initial state: {source.state.value}")
    print(f"Pressure: {source.pressure:.2f} bar")
    print(f"Temperature: {source.temperature:.2f}°C")
    print(f"Flow: {source.flow:.0f} kg/h")
    print("\nSimulating 30 seconds...")
    
    for i in range(300):  # 30 seconds at 0.1s intervals
        source.update(0.1)
        if i % 50 == 0:  # Print every 5 seconds
            print(f"\nTime: {i*0.1:.1f}s - State: {source.state.value}")
            print(f"  P: {source.pressure:.2f} bar, T: {source.temperature:.2f}°C, F: {source.flow:.0f} kg/h")