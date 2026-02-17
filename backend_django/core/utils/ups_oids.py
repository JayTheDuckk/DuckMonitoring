"""
UPS Model Definitions with SNMP OID Mappings
Pre-configured OIDs for common UPS manufacturers and models
"""

# Standard SNMP UPS MIB (RFC 1628) - Common across most UPS devices
UPS_MIB_BASE = {
    'battery_voltage': '1.3.6.1.2.1.33.1.2.5.0',  # upsBatteryVoltage
    'battery_current': '1.3.6.1.2.1.33.1.2.6.0',  # upsBatteryCurrent
    'battery_temperature': '1.3.6.1.2.1.33.1.2.7.0',  # upsBatteryTemperature
    'battery_status': '1.3.6.1.2.1.33.1.2.1.0',  # upsBatteryStatus
    'input_voltage': '1.3.6.1.2.1.33.1.3.3.1.3.1',  # upsInputVoltage
    'input_frequency': '1.3.6.1.2.1.33.1.3.3.1.2.1',  # upsInputFrequency
    'output_voltage': '1.3.6.1.2.1.4.4.1.3.1',  # upsOutputVoltage
    'output_frequency': '1.3.6.1.2.1.4.4.1.2.1',  # upsOutputFrequency
    'output_current': '1.3.6.1.2.1.4.4.1.4.1',  # upsOutputCurrent
    'output_load': '1.3.6.1.2.1.4.4.1.5.1',  # upsOutputLoad
    'ups_status': '1.3.6.1.2.1.33.1.2.1.0',  # upsIdentUPSStatus
    'ups_model': '1.3.6.1.2.1.33.1.1.1.0',  # upsIdentModel
    'ups_name': '1.3.6.1.2.1.33.1.1.2.0',  # upsIdentName
    'ups_manufacturer': '1.3.6.1.2.1.33.1.1.1.0',  # upsIdentManufacturer
    'time_on_battery': '1.3.6.1.2.1.33.1.2.2.0',  # upsSecondsOnBattery
    'estimated_runtime': '1.3.6.1.2.1.33.1.2.3.0',  # upsEstimatedMinutesRemaining
    'battery_capacity': '1.3.6.1.2.1.33.1.2.4.0',  # upsEstimatedChargeRemaining
}

# APC (Schneider Electric) UPS Models
APC_OIDS = {
    **UPS_MIB_BASE,
    'battery_voltage': '1.3.6.1.4.1.318.1.1.1.2.2.1.0',  # APC Battery Voltage
    'battery_status': '1.3.6.1.4.1.318.1.1.1.2.2.2.0',  # APC Battery Status
    'input_voltage': '1.3.6.1.4.1.318.1.1.1.3.2.1.0',  # APC Input Voltage
    'output_voltage': '1.3.6.1.4.1.318.1.1.1.4.2.1.0',  # APC Output Voltage
    'output_load': '1.3.6.1.4.1.318.1.1.1.4.2.3.0',  # APC Output Load
    'ups_status': '1.3.6.1.4.1.318.1.1.1.4.1.1.0',  # APC UPS Status
    'battery_capacity': '1.3.6.1.4.1.318.1.1.1.2.2.4.0',  # APC Battery Capacity
    'estimated_runtime': '1.3.6.1.4.1.318.1.1.1.2.2.3.0',  # APC Estimated Runtime
    'temperature': '1.3.6.1.4.1.318.1.1.1.2.1.2.0',  # APC Temperature
}

# CyberPower UPS Models
CYBERPOWER_OIDS = {
    **UPS_MIB_BASE,
    'battery_voltage': '1.3.6.1.4.1.3808.1.1.1.2.2.1.0',  # CyberPower Battery Voltage
    'battery_status': '1.3.6.1.4.1.3808.1.1.1.2.2.2.0',  # CyberPower Battery Status
    'input_voltage': '1.3.6.1.4.1.3808.1.1.1.3.2.1.0',  # CyberPower Input Voltage
    'output_voltage': '1.3.6.1.4.1.3808.1.1.1.4.2.1.0',  # CyberPower Output Voltage
    'output_load': '1.3.6.1.4.1.3808.1.1.1.4.2.3.0',  # CyberPower Output Load
    'ups_status': '1.3.6.1.4.1.3808.1.1.1.4.1.1.0',  # CyberPower UPS Status
    'battery_capacity': '1.3.6.1.4.1.3808.1.1.1.2.2.4.0',  # CyberPower Battery Capacity
    'estimated_runtime': '1.3.6.1.4.1.3808.1.1.1.2.2.3.0',  # CyberPower Estimated Runtime
}

# Eaton (Powerware) UPS Models
EATON_OIDS = {
    **UPS_MIB_BASE,
    'battery_voltage': '1.3.6.1.4.1.534.1.2.2.0',  # Eaton Battery Voltage
    'battery_status': '1.3.6.1.4.1.534.1.2.1.0',  # Eaton Battery Status
    'input_voltage': '1.3.6.1.4.1.534.1.3.4.1.3.1',  # Eaton Input Voltage
    'output_voltage': '1.3.6.1.4.1.534.1.4.4.1.3.1',  # Eaton Output Voltage
    'output_load': '1.3.6.1.4.1.534.1.4.4.1.4.1',  # Eaton Output Load
    'ups_status': '1.3.6.1.4.1.534.1.6.1.0',  # Eaton UPS Status
    'battery_capacity': '1.3.6.1.4.1.534.1.2.3.0',  # Eaton Battery Capacity
    'estimated_runtime': '1.3.6.1.4.1.534.1.2.4.0',  # Eaton Estimated Runtime
}

# Tripp Lite UPS Models
TRIPPLITE_OIDS = {
    **UPS_MIB_BASE,
    'battery_voltage': '1.3.6.1.4.1.850.1.1.1.2.2.1.0',  # Tripp Lite Battery Voltage
    'battery_status': '1.3.6.1.4.1.850.1.1.1.2.2.2.0',  # Tripp Lite Battery Status
    'input_voltage': '1.3.6.1.4.1.850.1.1.1.3.2.1.0',  # Tripp Lite Input Voltage
    'output_voltage': '1.3.6.1.4.1.850.1.1.1.4.2.1.0',  # Tripp Lite Output Voltage
    'output_load': '1.3.6.1.4.1.850.1.1.1.4.2.3.0',  # Tripp Lite Output Load
    'ups_status': '1.3.6.1.4.1.850.1.1.1.4.1.1.0',  # Tripp Lite UPS Status
    'battery_capacity': '1.3.6.1.4.1.850.1.1.1.2.2.4.0',  # Tripp Lite Battery Capacity
    'estimated_runtime': '1.3.6.1.4.1.850.1.1.1.2.2.3.0',  # Tripp Lite Estimated Runtime
}

# Liebert (Vertiv) UPS Models
LIEBERT_OIDS = {
    **UPS_MIB_BASE,
    'battery_voltage': '1.3.6.1.4.1.476.1.42.2.2.2.1.0',  # Liebert Battery Voltage
    'battery_status': '1.3.6.1.4.1.476.1.42.2.2.2.2.0',  # Liebert Battery Status
    'input_voltage': '1.3.6.1.4.1.476.1.42.2.3.2.1.0',  # Liebert Input Voltage
    'output_voltage': '1.3.6.1.4.1.476.1.42.2.4.2.1.0',  # Liebert Output Voltage
    'output_load': '1.3.6.1.4.1.476.1.42.2.4.2.3.0',  # Liebert Output Load
    'ups_status': '1.3.6.1.4.1.476.1.42.2.1.1.0',  # Liebert UPS Status
    'battery_capacity': '1.3.6.1.4.1.476.1.42.2.2.2.4.0',  # Liebert Battery Capacity
    'estimated_runtime': '1.3.6.1.4.1.476.1.42.2.2.2.3.0',  # Liebert Estimated Runtime
}

# UPS Model Definitions
UPS_MODELS = {
    'apc_smart_ups': {
        'name': 'APC Smart-UPS',
        'manufacturer': 'APC (Schneider Electric)',
        'oids': APC_OIDS,
        'description': 'APC Smart-UPS series'
    },
    'apc_back_ups': {
        'name': 'APC Back-UPS',
        'manufacturer': 'APC (Schneider Electric)',
        'oids': APC_OIDS,
        'description': 'APC Back-UPS series'
    },
    'cyberpower_ups': {
        'name': 'CyberPower UPS',
        'manufacturer': 'CyberPower',
        'oids': CYBERPOWER_OIDS,
        'description': 'CyberPower UPS series'
    },
    'eaton_powerware': {
        'name': 'Eaton Powerware',
        'manufacturer': 'Eaton',
        'oids': EATON_OIDS,
        'description': 'Eaton Powerware UPS series'
    },
    'eaton_5px': {
        'name': 'Eaton 5PX',
        'manufacturer': 'Eaton',
        'oids': EATON_OIDS,
        'description': 'Eaton 5PX UPS series'
    },
    'tripp_lite_smart': {
        'name': 'Tripp Lite Smart UPS',
        'manufacturer': 'Tripp Lite',
        'oids': TRIPPLITE_OIDS,
        'description': 'Tripp Lite Smart UPS series'
    },
    'liebert_gxt': {
        'name': 'Liebert GXT',
        'manufacturer': 'Vertiv (Liebert)',
        'oids': LIEBERT_OIDS,
        'description': 'Liebert GXT UPS series'
    },
    'generic_ups': {
        'name': 'Generic UPS (RFC 1628)',
        'manufacturer': 'Generic',
        'oids': UPS_MIB_BASE,
        'description': 'Generic UPS using standard RFC 1628 MIB'
    }
}

def get_ups_model(model_key):
    """Get UPS model definition by key"""
    return UPS_MODELS.get(model_key)

def get_all_ups_models():
    """Get all available UPS models"""
    return UPS_MODELS

def get_ups_oids(model_key):
    """Get OID mappings for a specific UPS model"""
    model = get_ups_model(model_key)
    if model:
        return model['oids']
    return UPS_MIB_BASE  # Default to standard MIB
