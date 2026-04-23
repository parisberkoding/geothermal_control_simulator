"""
Scenario Configurations
Three architectural scenarios for the GeoDipa Patuha direct-use simulator.

Scheme 1 – Full Traditional SCADA
    All components: industrial PLC / RTU, hardwired fieldbus

Scheme 2 – Full IoT
    All units: ESP32 + sensors, wireless LoRa / WiFi / MQTT

Scheme 3 – Hybrid (as-planned)
    Steam source (DP-6, main pipeline) → industrial SCADA
    Direct-use units (6 units)         → IoT ESP32

All labels are in English.
"""

# ── Unit registry ──────────────────────────────────────────────────────────────
# Each direct-use unit with its English name, operating range, and colour theme.

DIRECT_USE_UNITS = {
    'cabin': {
        'display_name':  'Cabin Heating',
        'short_name':    'Cabin',
        'hx_tag':        'HX-01',
        'temp_min':       24.0,
        'temp_max':       28.0,
        'temp_setpoint':  26.0,
        'unit_type':     'room_heating',
        'color_theme':   'warm_yellow',
        'description':   'Space heating for accommodation cabin (24-28°C)',
    },
    'hot_pool': {
        'display_name':  'Hot Pool',
        'short_name':    'Hot Pool',
        'hx_tag':        'HX-02',
        'temp_min':       37.0,
        'temp_max':       40.0,
        'temp_setpoint':  38.0,
        'unit_type':     'hot_pool',
        'color_theme':   'light_blue',
        'description':   'Therapeutic warm-water soaking pool (38-42°C)',
    },
    'tea_dryer': {
        'display_name':  'Tea Drying',
        'short_name':    'Tea Dry',
        'hx_tag':        'HX-03',
        'temp_min':       95.0,
        'temp_max':       98.0,
        'temp_setpoint':  96.0,
        'unit_type':     'tea_drying',
        'color_theme':   'brown_wood',
        'description':   'Hot-air tea leaf drying oven (50-70°C)',
    },
    'food_dehydrator_1': {
        'display_name':  'Food Dehydrator',
        'short_name':    'Food Dehy',
        'hx_tag':        'HX-04',
        'temp_min':       53.0,
        'temp_max':       56.0,
        'temp_setpoint':  54.0,
        'unit_type':     'food_dehydrator',
        'color_theme':   'orange',
        'description':   'Multi-tray food dehydration unit (40-60°C)',
    },
    'fish_pond': {
        'display_name':  'Fish Pond',
        'short_name':    'Fish Pond',
        'hx_tag':        'HX-05',
        'temp_min':       24.0,
        'temp_max':       30.0,
        'temp_setpoint':  27.0,
        'unit_type':     'fish_pond',
        'color_theme':   'blue',
        'description':   'Tilapia / carp aquaculture pond (28-30°C)',
    },
    'food_dehydrator_2': {
        'display_name':  'Food Dehydrator 2',
        'short_name':    'Food Dhy 2',
        'hx_tag':        'HX-06',
        'temp_min':       53.0,
        'temp_max':       56.0,
        'temp_setpoint':  54.0,
        'unit_type':     'food_dehydrator',
        'color_theme':   'orange',
        'description':   'Secondary food dehydration unit (40-60°C)',
    },
    'green_house': {
        'display_name':  'Greenhouse',
        'short_name':    'Greenhouse',
        'hx_tag':        'HX-07',
        'temp_min':       23.0,
        'temp_max':       26.0,
        'temp_setpoint':  24.5,
        'unit_type':     'greenhouse',
        'color_theme':   'light_green',
        'description':   'Hydroponic greenhouse (23-26 degC, RH 70-80%)',
    },
}

# ── Scenario definitions ──────────────────────────────────────────────────────

SCENARIOS: dict = {
    'scada': {
        'name':          'Full SCADA',
        'scheme_id':     'scada',
        'description':   'All components use industrial PLC/RTU connected via hardwired fieldbus. '
                         'Field devices report directly to the SCADA server over Profibus/Modbus.',
        'source_tech':   'Industrial PLC (Siemens S7-300)',
        'unit_tech':     'Remote Terminal Unit (RTU)',
        'comm_protocol': 'Profibus-DP / Modbus RTU',
        'source_comm':   'Hardwired 4-20 mA / HART',
        'unit_comm':     'Hardwired Fieldbus',
        'scan_rate_ms':  100,

        # Device tags shown on P&ID
        'source_device':  'PLC-SRC-001',
        'unit_devices': {
            'cabin':             'RTU-CAB-01',
            'hot_pool':          'RTU-HP-01',
            'tea_dryer':         'RTU-TD-01',
            'food_dehydrator_1': 'RTU-FD-01',
            'fish_pond':         'RTU-FP-01',
            'food_dehydrator_2': 'RTU-FD-02',
            'green_house':       'RTU-GH-01',
        },

        # What to show in IoT-specific panels
        'show_signal_strength': False,
        'show_battery_level':   False,
        'show_online_status':   False,
        'show_iot_badge':       False,
        'show_plc_tags':        True,
    },

    'iot': {
        'name':          'Full IoT',
        'scheme_id':     'iot',
        'description':   'All units use ESP32 microcontrollers with IoT sensors. '
                         'Wireless communication via LoRa (long-range) and WiFi (nearby units), '
                         'with MQTT broker for data aggregation.',
        'source_tech':   'ESP32 + Pressure/Temp Sensors',
        'unit_tech':     'ESP32 + IoT Sensor Suite',
        'comm_protocol': 'LoRa WAN + WiFi / MQTT',
        'source_comm':   'LoRa Gateway',
        'unit_comm':     'WiFi (< 200 m) / LoRa (> 200 m)',
        'scan_rate_ms':  500,

        'source_device':  'ESP32-SRC-001',
        'unit_devices': {
            'cabin':             'ESP32-CAB-001',
            'hot_pool':          'ESP32-HP-001',
            'tea_dryer':         'ESP32-TD-001',
            'food_dehydrator_1': 'ESP32-FD-001',
            'fish_pond':         'ESP32-FP-001',
            'food_dehydrator_2': 'ESP32-FD-002',
            'green_house':       'ESP32-GH-001',
        },

        'show_signal_strength': True,
        'show_battery_level':   True,
        'show_online_status':   True,
        'show_iot_badge':       True,
        'show_plc_tags':        False,

        # Simulated IoT status per unit (signal -dBm, battery %)
        'iot_status': {
            'cabin':             {'signal': -68, 'battery': 87, 'online': True,  'comm': 'WiFi'},
            'hot_pool':          {'signal': -72, 'battery': 92, 'online': True,  'comm': 'WiFi'},
            'tea_dryer':         {'signal': -85, 'battery': 75, 'online': True,  'comm': 'LoRa'},
            'food_dehydrator_1': {'signal': -90, 'battery': 63, 'online': True,  'comm': 'LoRa'},
            'fish_pond':         {'signal': -95, 'battery': 55, 'online': True,  'comm': 'LoRa'},
            'food_dehydrator_2': {'signal': -88, 'battery': 68, 'online': True,  'comm': 'LoRa'},
            'green_house':       {'signal': -78, 'battery': 81, 'online': True,  'comm': 'WiFi'},
        },
    },

    'hybrid': {
        'name':          'Hybrid',
        'scheme_id':     'hybrid',
        'description':   'Steam source and main pipeline: industrial SCADA (PLC/RTU, hardwired). '
                         'Direct-use units: ESP32 IoT with LoRa for distant units, '
                         'WiFi for units within 200 m of the distribution header.',
        'source_tech':   'Industrial SCADA  (PLC / RTU hardwired)',
        'unit_tech':     'ESP32 IoT  (LoRa / WiFi)',
        'comm_protocol': 'Fieldbus for Source  +  LoRa / WiFi for Units',
        'source_comm':   'Hardwired 4-20 mA / Profibus',
        'unit_comm':     'LoRa WAN (distant) / WiFi (nearby)',
        'scan_rate_ms':  250,

        'source_device':  'SCADA-PLC-001',
        'unit_devices': {
            'cabin':             'ESP32-CAB-001',
            'hot_pool':          'ESP32-HP-001',
            'tea_dryer':         'ESP32-TD-001',
            'food_dehydrator_1': 'ESP32-FD-001',
            'fish_pond':         'ESP32-FP-001',
            'food_dehydrator_2': 'ESP32-FD-002',
            'green_house':       'ESP32-GH-001',
        },

        'show_signal_strength': True,
        'show_battery_level':   True,
        'show_online_status':   True,
        'show_iot_badge':       True,
        'show_plc_tags':        True,   # Source side still shows PLC tags

        'iot_status': {
            'cabin':             {'signal': -68, 'battery': 87, 'online': True,  'comm': 'WiFi'},
            'hot_pool':          {'signal': -72, 'battery': 92, 'online': True,  'comm': 'WiFi'},
            'tea_dryer':         {'signal': -85, 'battery': 75, 'online': True,  'comm': 'LoRa'},
            'food_dehydrator_1': {'signal': -90, 'battery': 63, 'online': True,  'comm': 'LoRa'},
            'fish_pond':         {'signal': -95, 'battery': 55, 'online': True,  'comm': 'LoRa'},
            'food_dehydrator_2': {'signal': -88, 'battery': 68, 'online': True,  'comm': 'LoRa'},
            'green_house':       {'signal': -78, 'battery': 81, 'online': True,  'comm': 'WiFi'},
        },
    },
}


def get_scenario(scheme_id: str) -> dict:
    """Return scenario configuration for the given scheme ID."""
    return SCENARIOS.get(scheme_id, SCENARIOS['scada'])


def get_unit_info(unit_id: str) -> dict:
    """Return unit configuration for the given unit ID."""
    return DIRECT_USE_UNITS.get(unit_id, {})
