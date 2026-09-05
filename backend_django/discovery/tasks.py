from celery import shared_task
from django.utils import timezone
from .models import DiscoveryScan, DiscoveredHost
from inventory.discovery import discover_host, get_active_hosts_from_arp, parse_network_range
from core.utils.mac_vendor import research_mac
from core.utils.mdns_resolver import discover_mdns_hosts
import logging

logger = logging.getLogger(__name__)

HOST_TYPE_TO_OS = {
    'web_server': 'Web Server',
    'database': 'Database Server',
    'linux_server': 'Linux',
    'windows_server': 'Windows',
    'network_device': 'Network Device',
    'unknown': 'Unknown',
}


@shared_task
def scan_network_task(scan_id):
    """
    Scans a subnet for active hosts with IP, MAC, hostname, ports, and vendor info.
    """
    try:
        scan = DiscoveryScan.objects.get(id=scan_id)
        scan.status = 'running'
        scan.started_at = timezone.now()
        scan.save()

        try:
            ips_list = parse_network_range(scan.subnet)
        except ValueError as e:
            scan.status = 'failed'
            scan.error_message = str(e)
            scan.save()
            return

        if len(ips_list) > 512:
            scan.status = 'failed'
            scan.error_message = 'Subnet too large (max 512 addresses)'
            scan.save()
            return

        scan.total_hosts = len(ips_list)
        scan.save()

        arp_hosts = get_active_hosts_from_arp()
        mdns_result = discover_mdns_hosts(timeout=8.0)

        for ip in ips_list:
            scan.scanned_hosts += 1
            host_info = discover_host(ip, scan_ports=True, known_mac=arp_hosts.get(ip), mdns_result=mdns_result)

            if host_info:
                research = research_mac(
                    host_info.get('mac_address', ''),
                    hostname=host_info.get('hostname'),
                    suggested_type=host_info.get('suggested_type'),
                    services=host_info.get('services'),
                ) if host_info.get('mac_address') else {}
                DiscoveredHost.objects.create(
                    scan=scan,
                    ip_address=host_info['ip_address'],
                    hostname=host_info.get('hostname'),
                    mac_address=host_info.get('mac_address'),
                    manufacturer=research.get('vendor') or host_info.get('vendor'),
                    os_guess=host_info.get('os_guess') or HOST_TYPE_TO_OS.get(host_info.get('suggested_type'), 'Unknown'),
                    open_ports={
                        'services': host_info.get('services', []),
                        'mac_type': research.get('mac_type'),
                        'device_hint': host_info.get('device_hint'),
                        'device_class': host_info.get('device_class'),
                        'confidence': host_info.get('confidence'),
                        'identification_clues': host_info.get('identification_clues', []),
                        'mdns_name': host_info.get('mdns_name'),
                        'apple_model': host_info.get('apple_model'),
                    },
                    status='new',
                )
                scan.found_hosts += 1

            if scan.scanned_hosts % 10 == 0:
                scan.save()

        scan.status = 'completed'
        scan.completed_at = timezone.now()
        scan.save()

    except DiscoveryScan.DoesNotExist:
        logger.error(f"Scan {scan_id} not found")
    except Exception as e:
        if 'scan' in locals():
            scan.status = 'failed'
            scan.error_message = str(e)
            scan.save()
        logger.error(f"Error in scan {scan_id}: {e}")
