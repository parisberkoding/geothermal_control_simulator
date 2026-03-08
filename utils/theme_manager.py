"""
Theme Manager
Three visual themes for the SCADA simulator:
  - 'scada'  : Full Traditional SCADA  (industrial grey/blue)
  - 'iot'    : Full IoT                (green/tech modern)
  - 'hybrid' : Hybrid                  (mixed industrial + IoT)

All text is in English.
"""

# ── Colour palette per scheme ──────────────────────────────────────────────────

THEMES: dict = {
    'scada': {
        'name':        'Full SCADA',
        'scheme_id':   'scada',
        'description': 'All components use industrial PLC/RTU via hardwired fieldbus',
        'scheme_icon': '🏭',
        'comm_type':   'Hardwired Fieldbus / Profibus-DP',

        # Background layers
        'bg_window':   '#0d1628',
        'bg_panel':    '#1a2035',
        'bg_widget':   '#0a1220',
        'bg_header':   '#0d1628',

        # Accent
        'accent_primary':   '#2a5080',
        'accent_secondary': '#1e3a5f',
        'accent_highlight': '#3a6090',

        # Text
        'text_primary':  '#7ab0e0',
        'text_value':    '#00e8ff',
        'text_label':    '#5577aa',
        'text_unit':     '#445566',
        'text_title':    '#c0d8f0',

        # Borders
        'border_main':   '#1e3a5f',
        'border_group':  '#2a4060',
        'border_widget': '#15304a',

        # Status indicators
        'indicator_normal':  '#00ff96',
        'indicator_warning': '#ffcc00',
        'indicator_alarm':   '#ff3333',
        'indicator_info':    '#40aaff',

        # Gauge
        'gauge_arc_bg':  '#1a3050',
        'gauge_arc_val': '#00a8e0',
        'gauge_needle':  '#00e8ff',

        # Valve colours (knob arc)
        'valve_open':    '#00c878',
        'valve_partial': '#ffc000',
        'valve_closed':  '#ff4040',

        # Tab widget
        'tab_selected': '#2e4055',
        'tab_default':  '#131e30',
        'tab_hover':    '#253545',

        # Scheme-type badge
        'badge_bg':     '#0a2048',
        'badge_border': '#1e5aaa',
        'badge_text':   '#80b8ff',

        # IoT extras (hidden in SCADA mode)
        'iot_online':   '#00cc44',
        'iot_offline':  '#cc4400',
        'signal_bars':  ['#00cc66', '#00aa55', '#008844', '#006633'],
        'battery_full': '#00cc44',
        'battery_low':  '#cc4400',

        # Unit card colours (match physical unit theme)
        'unit_tea':      '#4a2808',   # brown/wood
        'unit_green':    '#083818',   # deep green
        'unit_food':     '#3a1e00',   # orange-brown
        'unit_cabin':    '#1e1800',   # warm dark
        'unit_pool':     '#001830',   # dark blue
        'unit_fish':     '#001428',   # deep blue
    },

    'iot': {
        'name':        'Full IoT',
        'scheme_id':   'iot',
        'description': 'All units use ESP32 + IoT sensors with wireless communication',
        'scheme_icon': '📡',
        'comm_type':   'ESP32 + LoRa WAN / WiFi / MQTT',

        'bg_window':   '#0a1a0d',
        'bg_panel':    '#0d2010',
        'bg_widget':   '#081410',
        'bg_header':   '#081208',

        'accent_primary':   '#1a5025',
        'accent_secondary': '#1e4a28',
        'accent_highlight': '#256030',

        'text_primary':  '#7ae07a',
        'text_value':    '#00ff88',
        'text_label':    '#44884a',
        'text_unit':     '#336640',
        'text_title':    '#b0e8b0',

        'border_main':   '#1e5f2e',
        'border_group':  '#2a6040',
        'border_widget': '#154520',

        'indicator_normal':  '#00ff66',
        'indicator_warning': '#aaff00',
        'indicator_alarm':   '#ff4444',
        'indicator_info':    '#44ffaa',

        'gauge_arc_bg':  '#1a3a1e',
        'gauge_arc_val': '#00aa55',
        'gauge_needle':  '#00ff88',

        'valve_open':    '#00e060',
        'valve_partial': '#aaff00',
        'valve_closed':  '#ff4444',

        'tab_selected': '#1a3520',
        'tab_default':  '#0a1a0d',
        'tab_hover':    '#152a18',

        'badge_bg':     '#0a2810',
        'badge_border': '#1e6630',
        'badge_text':   '#80ff90',

        'iot_online':   '#00ff44',
        'iot_offline':  '#ff4400',
        'signal_bars':  ['#00ff66', '#00cc55', '#009944', '#006633'],
        'battery_full': '#00ff44',
        'battery_low':  '#ff4400',

        'unit_tea':      '#1a1200',
        'unit_green':    '#0a2000',
        'unit_food':     '#1a0e00',
        'unit_cabin':    '#150e00',
        'unit_pool':     '#001020',
        'unit_fish':     '#000e1a',
    },

    'hybrid': {
        'name':        'Hybrid',
        'scheme_id':   'hybrid',
        'description': 'Industrial SCADA for steam source; IoT ESP32 for direct use units',
        'scheme_icon': '⚙',
        'comm_type':   'SCADA + LoRa/WiFi  |  Hardwired Source, Wireless Units',

        'bg_window':   '#0f1520',
        'bg_panel':    '#141c28',
        'bg_widget':   '#0c1318',
        'bg_header':   '#0c1018',

        'accent_primary':   '#2a4060',
        'accent_secondary': '#1a3545',
        'accent_highlight': '#354e70',

        'text_primary':  '#80c0d0',
        'text_value':    '#40d8f8',
        'text_label':    '#506880',
        'text_unit':     '#405060',
        'text_title':    '#b0d0e0',

        'border_main':   '#253545',
        'border_group':  '#304055',
        'border_widget': '#1e2e40',

        'indicator_normal':  '#00e888',
        'indicator_warning': '#ffcc00',
        'indicator_alarm':   '#ff4040',
        'indicator_info':    '#40c8ff',

        'gauge_arc_bg':  '#1a2c40',
        'gauge_arc_val': '#2090a8',
        'gauge_needle':  '#40d8f8',

        'valve_open':    '#00c878',
        'valve_partial': '#ffc000',
        'valve_closed':  '#ff4040',

        'tab_selected': '#253545',
        'tab_default':  '#0f1520',
        'tab_hover':    '#1e2c3c',

        'badge_bg':     '#0a1e30',
        'badge_border': '#1e4870',
        'badge_text':   '#60b0e0',

        'iot_online':   '#00cc88',
        'iot_offline':  '#cc4400',
        'signal_bars':  ['#00cc88', '#00aa70', '#008858', '#006640'],
        'battery_full': '#00cc88',
        'battery_low':  '#cc4400',

        'unit_tea':      '#1a1205',
        'unit_green':    '#0a1808',
        'unit_food':     '#1a1000',
        'unit_cabin':    '#181205',
        'unit_pool':     '#001525',
        'unit_fish':     '#00101e',
    },
}


def get_theme(scheme_id: str) -> dict:
    """Return the colour palette dict for the given scheme."""
    return THEMES.get(scheme_id, THEMES['scada'])


def get_stylesheet(scheme_id: str) -> str:
    """Return a complete Qt stylesheet string for the given scheme."""
    t = get_theme(scheme_id)
    return f"""
        QMainWindow {{
            background-color: {t['bg_window']};
        }}
        QWidget {{
            background-color: {t['bg_window']};
            color: {t['text_primary']};
        }}
        QGroupBox {{
            color: {t['text_primary']};
            font-size: 9pt;
            font-weight: bold;
            border: 2px solid {t['border_group']};
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }}
        QPushButton {{
            background: {t['accent_primary']};
            color: {t['text_primary']};
            border: 1px solid {t['border_main']};
            border-radius: 3px;
            padding: 5px 8px;
            font-size: 9pt;
            font-weight: bold;
        }}
        QPushButton:hover  {{ background: {t['accent_highlight']}; border-color: {t['badge_border']}; }}
        QPushButton:pressed {{ background: {t['bg_widget']}; }}
        QTabWidget::pane {{
            border: 2px solid {t['border_group']};
            border-radius: 3px;
        }}
        QTabBar::tab {{
            background: {t['tab_default']};
            color: {t['text_label']};
            padding: 6px 12px;
            font-size: 9pt;
            font-weight: bold;
            border-radius: 3px 3px 0 0;
            min-width: 80px;
        }}
        QTabBar::tab:selected {{ background: {t['tab_selected']}; color: white; }}
        QTabBar::tab:hover    {{ background: {t['tab_hover']}; }}
        QScrollArea {{
            background: {t['bg_widget']};
            border: none;
        }}
        QScrollBar:vertical {{
            background: {t['bg_panel']};
            width: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background: {t['border_group']};
            border-radius: 5px;
            min-height: 20px;
        }}
        QTextEdit {{
            background: {t['bg_widget']};
            color: {t['indicator_normal']};
            border: 1px solid {t['border_main']};
            font-family: 'Courier New';
            font-size: 8pt;
        }}
        QLabel {{
            color: {t['text_primary']};
            background: transparent;
        }}
        QCheckBox {{
            color: {t['text_primary']};
            background: transparent;
        }}
        QFrame[frameShape="4"] {{
            background: {t['border_group']};
            max-height: 1px;
        }}
        QFrame[frameShape="5"] {{
            background: {t['border_group']};
            max-width: 1px;
        }}
        QSplitter::handle {{
            background: {t['border_group']};
        }}
    """


def get_scheme_button_style(scheme_id: str, is_active: bool) -> str:
    """Style for a scheme selector button (active or inactive)."""
    t = get_theme(scheme_id)
    if is_active:
        return f"""
            QPushButton {{
                background: {t['badge_bg']};
                color: {t['badge_text']};
                border: 2px solid {t['badge_border']};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 9pt;
                font-weight: bold;
            }}
        """
    else:
        return """
            QPushButton {
                background: #1e1e1e;
                color: #666;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background: #2a2a2a;
                color: #aaa;
                border-color: #555;
            }
        """
