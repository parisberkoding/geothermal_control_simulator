"""
Endpoints Simulation
Simulates steam demand for each direct use application
Provides sensor status based on supply vs demand
"""
import random

class SensorStatus:
    """Sensor status enum"""
    NORMAL = "Normal"
    WARNING_LOW = "Need Steam"
    WARNING_HIGH = "Excess Steam"
    CRITICAL_LOW = "Critical - Low Steam"
    CRITICAL_HIGH = "Critical - High Steam"

class Endpoint:
    """
    Individual endpoint (direct use application)
    """
    
    def __init__(self, name, base_demand, tolerance=0.15):
        """
        Initialize endpoint
        
        Args:
            name: Application name
            base_demand: Base steam demand (kg/h)
            tolerance: Acceptable deviation (15% default)
        """
        self.name = name
        self.base_demand = base_demand
        self.tolerance = tolerance
        
        # Current state
        self.current_demand = base_demand
        self.current_supply = 0
        self.sensor_status = SensorStatus.NORMAL
        
        # Demand variation (natural fluctuation)
        self.demand_timer = 0
        self.demand_hold_time = random.uniform(15, 30)
    
    def update(self, dt, valve_position, main_flow):
        """
        Update endpoint state
        
        Args:
            dt: Delta time
            valve_position: Valve position (0-100%)
            main_flow: Main steam flow rate (kg/h)
        """
        # Update demand (natural variation over time)
        self.demand_timer += dt
        if self.demand_timer >= self.demand_hold_time:
            # Change demand slightly
            variation = random.uniform(-0.1, 0.1)  # ±10%
            self.current_demand = self.base_demand * (1 + variation)
            self.demand_timer = 0
            self.demand_hold_time = random.uniform(15, 30)
        
        # Calculate supply based on valve position and main flow
        # Supply = (valve_position / 100) * (main_flow / 6)
        # Divide by 6 because there are 6 endpoints
        self.current_supply = (valve_position / 100.0) * (main_flow / 6.0)
        
        # Update sensor status
        self._update_sensor_status()
    
    def _update_sensor_status(self):
        """Update sensor status based on supply vs demand"""
        if self.current_supply == 0:
            self.sensor_status = SensorStatus.CRITICAL_LOW
            return
        
        # Calculate deviation
        deviation = (self.current_supply - self.current_demand) / self.current_demand
        
        if abs(deviation) <= self.tolerance:
            # Within tolerance - Normal
            self.sensor_status = SensorStatus.NORMAL
        elif deviation < -self.tolerance * 2:
            # Very low supply
            self.sensor_status = SensorStatus.CRITICAL_LOW
        elif deviation < -self.tolerance:
            # Low supply
            self.sensor_status = SensorStatus.WARNING_LOW
        elif deviation > self.tolerance * 2:
            # Very high supply
            self.sensor_status = SensorStatus.CRITICAL_HIGH
        elif deviation > self.tolerance:
            # High supply
            self.sensor_status = SensorStatus.WARNING_HIGH
        else:
            self.sensor_status = SensorStatus.NORMAL
    
    def get_sensor_color(self):
        """Get sensor color for visualization"""
        if self.sensor_status == SensorStatus.NORMAL:
            return (0, 255, 100)  # Green
        elif self.sensor_status in [SensorStatus.WARNING_LOW, SensorStatus.WARNING_HIGH]:
            return (255, 200, 0)  # Yellow
        else:
            return (255, 50, 50)  # Red
    
    def needs_adjustment(self):
        """Check if endpoint needs valve adjustment"""
        return self.sensor_status != SensorStatus.NORMAL
    
    def get_recommended_adjustment(self):
        """
        Get recommended valve adjustment
        
        Returns:
            float: Recommended change in valve position (%)
        """
        if self.sensor_status == SensorStatus.NORMAL:
            return 0
        
        # Calculate how much to adjust
        deviation = (self.current_supply - self.current_demand) / self.current_demand
        
        if self.sensor_status in [SensorStatus.CRITICAL_LOW, SensorStatus.WARNING_LOW]:
            # Need more steam - open valve
            if abs(deviation) > 0.3:
                return 20  # Open 20%
            else:
                return 10  # Open 10%
        else:
            # Too much steam - close valve
            if abs(deviation) > 0.3:
                return -20  # Close 20%
            else:
                return -10  # Close 10%

class EndpointManager:
    """
    Manages all endpoints
    """
    
    def __init__(self):
        # Create endpoints with base demands (kg/h)
        # These are rough estimates - can be tuned
        self.endpoints = {
            'food_dehydrator': Endpoint('Food Dehydrator', 600),
            'hot_pool': Endpoint('Hot Pool', 800),
            'tea_dryer': Endpoint('Tea Leaves Dryer', 500),
            'cabin': Endpoint('Cabin Heating', 400),
            'green_house': Endpoint('Green House', 700),
            'fishery': Endpoint('Fishery Pond', 374)  # Rest of flow
        }
    
    def update(self, dt, valve_positions, main_flow):
        """
        Update all endpoints
        
        Args:
            dt: Delta time
            valve_positions: Dict of valve positions
            main_flow: Main steam flow
        """
        for endpoint_id, endpoint in self.endpoints.items():
            valve_pos = valve_positions.get(endpoint_id, 0)
            endpoint.update(dt, valve_pos, main_flow)
    
    def get_endpoint(self, endpoint_id):
        """Get specific endpoint"""
        return self.endpoints.get(endpoint_id)
    
    def get_all_sensor_status(self):
        """Get sensor status for all endpoints"""
        return {
            endpoint_id: {
                'status': endpoint.sensor_status,
                'color': endpoint.get_sensor_color(),
                'demand': endpoint.current_demand,
                'supply': endpoint.current_supply,
                'needs_adjustment': endpoint.needs_adjustment(),
                'recommended_adjustment': endpoint.get_recommended_adjustment()
            }
            for endpoint_id, endpoint in self.endpoints.items()
        }

# Test
if __name__ == '__main__':
    print("Testing Endpoint Manager...")
    
    manager = EndpointManager()
    valve_positions = {
        'food_dehydrator': 65.0,
        'hot_pool': 80.0,
        'tea_dryer': 55.0,
        'cabin': 45.0,
        'green_house': 70.0,
        'fishery': 60.0
    }
    
    print("\nSimulating 5 seconds...")
    for i in range(50):
        manager.update(0.1, valve_positions, 3374)
    
    print("\nSensor Status:")
    status = manager.get_all_sensor_status()
    for endpoint_id, data in status.items():
        print(f"\n{endpoint_id}:")
        print(f"  Status: {data['status']}")
        print(f"  Demand: {data['demand']:.0f} kg/h")
        print(f"  Supply: {data['supply']:.0f} kg/h")
        if data['needs_adjustment']:
            print(f"  Recommended: {data['recommended_adjustment']:+.0f}%")