"""
UPS OID Definitions for supported devices.
"""

UPS_MODELS = {
    'apc': {
        'name': 'APC Smart-UPS',
        'manufacturer': 'APC',
        'description': 'APC Smart-UPS Family',
        'oid_base': '1.3.6.1.4.1.318.1.1.1',
        'metrics': {
            'battery_capacity': '1.3.6.1.4.1.318.1.1.1.2.2.1.0',
            'battery_temperature': '1.3.6.1.4.1.318.1.1.1.2.2.2.0',
            'battery_runtime': '1.3.6.1.4.1.318.1.1.1.2.2.3.0',
            'battery_status': '1.3.6.1.4.1.318.1.1.1.2.2.4.0',
            'input_voltage': '1.3.6.1.4.1.318.1.1.1.3.2.1.0',
            'output_voltage': '1.3.6.1.4.1.318.1.1.1.4.2.1.0',
            'output_load': '1.3.6.1.4.1.318.1.1.1.4.2.3.0',
        }
    },
    'cyberpower': {
        'name': 'CyberPower UPS',
        'manufacturer': 'CyberPower',
        'description': 'CyberPower UPS Systems',
        'oid_base': '1.3.6.1.4.1.3808.1.1.1',
        'metrics': {
            'battery_capacity': '1.3.6.1.4.1.3808.1.1.1.2.2.1.0',
            'battery_temperature': '1.3.6.1.4.1.3808.1.1.1.2.2.2.0', # Placeholder if unknown
            'battery_runtime': '1.3.6.1.4.1.3808.1.1.1.2.2.4.0',
            'input_voltage': '1.3.6.1.4.1.3808.1.1.1.3.2.1.0',
            'output_voltage': '1.3.6.1.4.1.3808.1.1.1.4.2.1.0',
            'output_load': '1.3.6.1.4.1.3808.1.1.1.4.2.3.0',
        }
    },
    'eaton': {
        'name': 'Eaton UPS',
        'manufacturer': 'Eaton',
        'description': 'Eaton Powerware UPS',
        'oid_base': '1.3.6.1.4.1.534.1',
        'metrics': {
            'battery_capacity': '1.3.6.1.4.1.534.1.2.4.0',
            'battery_runtime': '1.3.6.1.4.1.534.1.2.1.0',
            'input_voltage': '1.3.6.1.4.1.534.1.3.4.0',
            'output_voltage': '1.3.6.1.4.1.534.1.4.2.0',
            'output_load': '1.3.6.1.4.1.534.1.4.1.0',
        }
    }
}
