"""
SNMP OID Definitions for supported devices.
"""

SNMP_DEVICE_MODELS = {
    'network_equipment': [
        {
            'key': 'cisco_ios',
            'name': 'Cisco IOS Device',
            'manufacturer': 'Cisco',
            'description': 'Standard Cisco IOS switch or router',
            'available_metrics': [
                'health_status', 'system_name', 'system_uptime',
                'interface_traffic', 'cpu_usage', 'memory_usage'
            ]
        },
        {
            'key': 'juniper_junos',
            'name': 'Juniper Junos Device',
            'manufacturer': 'Juniper',
            'description': 'Juniper switch or router running Junos',
            'available_metrics': [
                'health_status', 'system_name', 'system_uptime',
                'interface_traffic', 'cpu_usage', 'memory_usage'
            ]
        }
    ],
    'servers': [
        {
            'key': 'linux_snmp',
            'name': 'Linux Server (Net-SNMP)',
            'manufacturer': 'Generic',
            'description': 'Linux server running net-snmp',
            'available_metrics': [
                'health_status', 'system_name', 'system_uptime',
                'cpu_usage', 'memory_usage', 'disk_usage', 'load_average'
            ]
        },
        {
            'key': 'windows_snmp',
            'name': 'Windows Server',
            'manufacturer': 'Microsoft',
            'description': 'Windows Server with SNMP Service',
            'available_metrics': [
                'health_status', 'system_name', 'system_uptime',
                'cpu_usage', 'memory_usage', 'disk_usage'
            ]
        }
    ],
    'printers': [
        {
            'key': 'hp_printer',
            'name': 'HP LaserJet',
            'manufacturer': 'HP',
            'description': 'HP LaserJet Network Printer',
            'available_metrics': [
                'health_status', 'system_name', 'system_uptime',
                'toner_level', 'page_count', 'status_message'
            ]
        }
    ]
}
