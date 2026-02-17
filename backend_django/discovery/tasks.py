from celery import shared_task
from django.utils import timezone
from .models import DiscoveryScan, DiscoveredHost
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
import logging

# Try ping3, fallback to socket connect if needed
try:
    from ping3 import ping
    PING_AVAILABLE = True
except ImportError:
    PING_AVAILABLE = False

logger = logging.getLogger(__name__)

def check_host(ip):
    """
    Check if a host is alive using ping3 (ICMP) or socket (TCP port 80).
    Returns tuple (ip, is_alive, hostname, latency)
    """
    is_alive = False
    hostname = None
    latency = None

    if PING_AVAILABLE:
        try:
            # privilege issues might occur with ping3
            result = ping(str(ip), timeout=1)
            if result is not None and result is not False:
                is_alive = True
                latency = result * 1000 # convert to ms
        except Exception:
            pass
    
    # Fallback to TCP connect if ping failed or not available (common in non-root containers)
    if not is_alive:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            # Try connecting to common ports like 80, 443, 22
            for port in [80, 443, 22]:
                result = sock.connect_ex((str(ip), port))
                if result == 0:
                    is_alive = True
                    latency = 0 # Can't measure accurately this way easily
                    break
            sock.close()
        except:
            pass

    if is_alive:
        try:
            hostname = socket.gethostbyaddr(str(ip))[0]
        except:
            hostname = None

    return (str(ip), is_alive, hostname, latency)

@shared_task
def scan_network_task(scan_id):
    """
    Scans a subnet for active hosts.
    """
    try:
        scan = DiscoveryScan.objects.get(id=scan_id)
        scan.status = 'running'
        scan.started_at = timezone.now()
        scan.save()
        
        subnet = scan.subnet
        try:
            network = ipaddress.ip_network(subnet, strict=False)
        except ValueError:
            scan.status = 'failed'
            scan.error_message = f"Invalid subnet: {subnet}"
            scan.save()
            return

        # Limit scan size to prevent abuse
        if network.num_addresses > 512:
             scan.status = 'failed'
             scan.error_message = "Subnet too large (max 512 addresses)"
             scan.save()
             return

        scan.total_hosts = network.num_addresses - 2 # Exclude network and broadcast
        scan.save()

        active_hosts = []
        
        # Determine strict mode for gathering hosts
        # hosts() returns usable hosts, excluding network/broadcast
        hosts_list = list(network.hosts())
        
        # Use ThreadPool to scan concurrently
        with ThreadPoolExecutor(max_workers=50) as executor:
            results = list(executor.map(check_host, hosts_list))
            
        for ip, is_alive, hostname, latency in results:
            scan.scanned_hosts += 1
            if is_alive:
                active_hosts.append((ip, hostname))
                # Update progress periodically
                if scan.scanned_hosts % 10 == 0:
                    scan.save()

        # Save results
        for ip, hostname in active_hosts:
            DiscoveredHost.objects.create(
                scan=scan,
                ip_address=ip,
                hostname=hostname,
                status='new'
            )
            scan.found_hosts += 1

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
