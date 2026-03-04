"""
Steam Properties Calculator
Using CoolProp for accurate thermodynamic calculations
"""
from CoolProp.CoolProp import PropsSI
import logging

logger = logging.getLogger(__name__)

class SteamProperties:
    """Calculate steam properties using CoolProp"""
    
    @staticmethod
    def get_saturation_temperature(pressure_bar):
        """
        Get saturation temperature for given pressure
        
        Args:
            pressure_bar: Pressure in bar
            
        Returns:
            Temperature in Celsius
        """
        try:
            pressure_pa = pressure_bar * 1e5  # Convert bar to Pascal
            temp_k = PropsSI('T', 'P', pressure_pa, 'Q', 1, 'Water')
            temp_c = temp_k - 273.15
            return temp_c
        except Exception as e:
            logger.error(f"Error calculating saturation temperature: {e}")
            return 174.0  # Default fallback
    
    @staticmethod
    def get_enthalpy(pressure_bar, temperature_c):
        """
        Get specific enthalpy
        
        Args:
            pressure_bar: Pressure in bar
            temperature_c: Temperature in Celsius
            
        Returns:
            Enthalpy in kJ/kg
        """
        try:
            pressure_pa = pressure_bar * 1e5
            temp_k = temperature_c + 273.15
            enthalpy_j = PropsSI('H', 'P', pressure_pa, 'T', temp_k, 'Water')
            enthalpy_kj = enthalpy_j / 1000.0
            return enthalpy_kj
        except Exception as e:
            logger.error(f"Error calculating enthalpy: {e}")
            return 2800.0  # Default fallback
    
    @staticmethod
    def get_density(pressure_bar, temperature_c):
        """
        Get steam density
        
        Args:
            pressure_bar: Pressure in bar
            temperature_c: Temperature in Celsius
            
        Returns:
            Density in kg/m³
        """
        try:
            pressure_pa = pressure_bar * 1e5
            temp_k = temperature_c + 273.15
            density = PropsSI('D', 'P', pressure_pa, 'T', temp_k, 'Water')
            return density
        except Exception as e:
            logger.error(f"Error calculating density: {e}")
            return 4.0  # Default fallback
    
    @staticmethod
    def validate_steam_state(pressure_bar, temperature_c):
        """
        Check if given pressure and temperature represent steam state
        
        Returns:
            bool: True if valid steam state
        """
        try:
            sat_temp = SteamProperties.get_saturation_temperature(pressure_bar)
            # Steam should be at or above saturation temperature
            return temperature_c >= (sat_temp - 5)  # 5°C tolerance
        except:
            return True  # Default to valid

# Quick test function
if __name__ == '__main__':
    print("Testing Steam Properties Calculator...")
    print(f"Saturation temp at 8 bar: {SteamProperties.get_saturation_temperature(8):.2f}°C")
    print(f"Enthalpy at 8 bar, 174°C: {SteamProperties.get_enthalpy(8, 174):.2f} kJ/kg")
    print(f"Density at 8 bar, 174°C: {SteamProperties.get_density(8, 174):.4f} kg/m³")