"""
SNMP Device Model Definitions with OID Mappings
Pre-configured OIDs for Out Of Band (OOB) server management systems
"""

# HPE iLO (Integrated Lights-Out) OIDs
ILO_OIDS = {
    'system_name': '1.3.6.1.2.1.1.5.0',  # sysName
    'system_uptime': '1.3.6.1.2.1.1.3.0',  # sysUpTime
    'system_description': '1.3.6.1.2.1.1.1.0',  # sysDescr
    'health_status': '1.3.6.1.4.1.232.6.1.3.0',  # iLO Health Status
    'temperature': '1.3.6.1.4.1.232.6.2.6.8.1.4.1',  # iLO Temperature
    'power_status': '1.3.6.1.4.1.232.6.2.9.3.0',  # iLO Power Status
    'fan_status': '1.3.6.1.4.1.232.6.2.6.7.1.4.1',  # iLO Fan Status
    'cpu_temperature': '1.3.6.1.4.1.232.6.2.6.8.1.4.1',  # CPU Temperature
    'memory_status': '1.3.6.1.4.1.232.6.2.14.1.1.1.0',  # Memory Status
    'network_status': '1.3.6.1.4.1.232.6.2.17.1.1.0',  # Network Status
    'firmware_version': '1.3.6.1.4.1.232.9.2.2.0',  # Firmware Version
    'server_power_state': '1.3.6.1.4.1.232.6.2.9.3.0',  # Server Power State
}

# Dell iDRAC (Integrated Dell Remote Access Controller) OIDs
IDRAC_OIDS = {
    'system_name': '1.3.6.1.2.1.1.5.0',  # sysName
    'system_uptime': '1.3.6.1.2.1.1.3.0',  # sysUpTime
    'system_description': '1.3.6.1.2.1.1.1.0',  # sysDescr
    'health_status': '1.3.6.1.4.1.674.10892.5.4.300.50.1.11.1',  # iDRAC Health Status
    'temperature': '1.3.6.1.4.1.674.10892.5.4.700.20.1.8.1',  # iDRAC Temperature
    'power_status': '1.3.6.1.4.1.674.10892.5.4.600.12.1.4.1',  # iDRAC Power Status
    'fan_status': '1.3.6.1.4.1.674.10892.5.4.700.20.1.6.1',  # iDRAC Fan Status
    'cpu_temperature': '1.3.6.1.4.1.674.10892.5.4.700.20.1.8.1',  # CPU Temperature
    'memory_status': '1.3.6.1.4.1.674.10892.5.4.300.50.1.5.1',  # Memory Status
    'system_state': '1.3.6.1.4.1.674.10892.5.4.300.50.1.8.1',  # System State
    'firmware_version': '1.3.6.1.4.1.674.10892.5.1.1.11.0',  # Firmware Version
    'server_power_state': '1.3.6.1.4.1.674.10892.5.4.600.12.1.4.1',  # Server Power State
    'voltage': '1.3.6.1.4.1.674.10892.5.4.600.20.1.7.1',  # Voltage
}

# Supermicro IPMI OIDs
SUPERMICRO_IPMI_OIDS = {
    'system_name': '1.3.6.1.2.1.1.5.0',  # sysName
    'system_uptime': '1.3.6.1.2.1.1.3.0',  # sysUpTime
    'system_description': '1.3.6.1.2.1.1.1.0',  # sysDescr
    'temperature': '1.3.6.1.4.1.10876.2.1.1.1.1.4.1',  # Temperature
    'fan_speed': '1.3.6.1.4.1.10876.2.1.1.1.1.3.1',  # Fan Speed
    'power_status': '1.3.6.1.4.1.10876.2.1.1.1.1.2.1',  # Power Status
    'voltage': '1.3.6.1.4.1.10876.2.1.1.1.1.5.1',  # Voltage
    'cpu_temperature': '1.3.6.1.4.1.10876.2.1.1.1.1.4.2',  # CPU Temperature
    'system_health': '1.3.6.1.4.1.10876.2.1.1.1.1.1.1',  # System Health
}

# Device Model Definitions
SNMP_DEVICE_MODELS = {
    'hp_ilo': {
        'name': 'HPE iLO',
        'manufacturer': 'HPE',
        'oids': ILO_OIDS,
        'description': 'HPE Integrated Lights-Out (iLO)'
    },
    'dell_idrac': {
        'name': 'Dell iDRAC',
        'manufacturer': 'Dell',
        'oids': IDRAC_OIDS,
        'description': 'Dell Integrated Remote Access Controller (iDRAC)'
    },
    'supermicro_ipmi': {
        'name': 'Supermicro IPMI',
        'manufacturer': 'Supermicro',
        'oids': SUPERMICRO_IPMI_OIDS,
        'description': 'Supermicro IPMI'
    }
}

def get_snmp_device_model(model_key):
    """Get SNMP device model definition by key"""
    return SNMP_DEVICE_MODELS.get(model_key)

def get_all_snmp_device_models():
    """Get all available SNMP device models"""
    return SNMP_DEVICE_MODELS

def get_snmp_device_oids(model_key):
    """Get OID mappings for a specific SNMP device model"""
    model = get_snmp_device_model(model_key)
    if model:
        return model['oids']
    return {}
