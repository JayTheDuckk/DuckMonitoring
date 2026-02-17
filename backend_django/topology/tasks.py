from celery import shared_task
from django.utils import timezone
from .models import NetworkLink
from inventory.models import Host, SNMPDevice
from core.utils.service_checker import walk_snmp
import logging
import re

logger = logging.getLogger(__name__)

# Base OIDs for LLDP
LLDP_REM_SYS_NAME = '1.0.8802.1.1.2.1.4.1.1.9'
LLDP_REM_PORT_ID = '1.0.8802.1.1.2.1.4.1.1.7'
LLDP_REM_SYS_DESC = '1.0.8802.1.1.2.1.4.1.1.10'

# Base OIDs for CDP
CDP_CACHE_DEVICE_ID = '1.3.6.1.4.1.9.9.23.1.2.1.1.6'
CDP_CACHE_DEVICE_PORT = '1.3.6.1.4.1.9.9.23.1.2.1.1.7'
CDP_CACHE_PLATFORM = '1.3.6.1.4.1.9.9.23.1.2.1.1.8'

@shared_task
def discover_topology():
    """
    Scans all SNMP-enabled devices for neighbor information (LLDP/CDP)
    and updates the NetworkLink table.
    """
    logger.info("Starting topology discovery...")
    
    snmp_devices = SNMPDevice.objects.filter(enabled=True)
    links_created = 0
    links_updated = 0
    
    for device in snmp_devices:
        source_host, _ = Host.objects.get_or_create(
            ip_address=device.ip_address,
            defaults={'hostname': device.name, 'status': 'up'}
        )
        
        v3_auth = None
        if device.snmp_version == 3:
            v3_auth = {
                'username': device.snmp_username,
                'security_level': device.snmp_security_level,
                'auth_protocol': device.snmp_auth_protocol,
                'auth_key': device.snmp_auth_key,
                'priv_protocol': device.snmp_priv_protocol,
                'priv_key': device.snmp_priv_key
            }

        # --- LLDP Discovery ---
        try:
            lldp_names = walk_snmp(device.ip_address, LLDP_REM_SYS_NAME, 
                                  community=device.snmp_community, 
                                  snmp_version=device.snmp_version, 
                                  port=device.snmp_port,
                                  v3_auth=v3_auth)
            
            for oid, value in lldp_names:
                neighbor_name = value
                if not neighbor_name: continue
                
                # Match neighbor to existing host or create link to raw info
                # LLDP OID structure: base.time_mark.interface_num.index
                # We won't parse strict indices here for simplicity, just assume existence
                
                # Try to find neighbor host by hostname
                target_host = Host.objects.filter(hostname__iexact=neighbor_name).first()
                if not target_host and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', neighbor_name):
                     target_host = Host.objects.filter(ip_address=neighbor_name).first()

                NetworkLink.objects.update_or_create(
                    source=source_host,
                    target=target_host,
                    defaults={
                        'target_ip': neighbor_name if not target_host else None,
                        'protocol': 'lldp',
                        'link_type': 'physical'
                    }
                )
                links_created += 1

        except Exception as e:
            logger.error(f"Error checking LLDP on {device.name}: {e}")

        # --- CDP Discovery ---
        try:
            cdp_ids = walk_snmp(device.ip_address, CDP_CACHE_DEVICE_ID, 
                                community=device.snmp_community, 
                                snmp_version=device.snmp_version, 
                                port=device.snmp_port,
                                v3_auth=v3_auth)
                                
            for oid, value in cdp_ids:
                neighbor_id = value
                if not neighbor_id: continue
                
                target_host = Host.objects.filter(hostname__iexact=neighbor_id).first()
                if not target_host and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', neighbor_id):
                     target_host = Host.objects.filter(ip_address=neighbor_id).first()

                NetworkLink.objects.update_or_create(
                    source=source_host,
                    target=target_host,
                    defaults={
                        'target_ip': neighbor_id if not target_host else None,
                        'protocol': 'cdp',
                        'link_type': 'physical'
                    }
                )
                links_created += 1
                
        except Exception as e:
            logger.error(f"Error checking CDP on {device.name}: {e}")

    return f"Topology scan completed. processed {links_created} links."
