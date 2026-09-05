"""
Network Discovery Utility
"""

import socket
import subprocess
import ipaddress
import concurrent.futures
from datetime import datetime
import platform
import re
from typing import List, Dict, Optional, Tuple

from core.utils.mac_vendor import research_mac
from core.utils.device_fingerprint import fingerprint_device, FINGERPRINT_PORTS
from core.utils.mdns_resolver import discover_mdns_hosts, lookup_mdns_for_ip

COMMON_PORTS = {
    **FINGERPRINT_PORTS,
}

def ping_host(ip: str, timeout: int = 1) -> Tuple[bool, Optional[float], Optional[int]]:
    try:
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        if platform.system().lower() == 'darwin':
             timeout_arg = str(timeout * 1000) # ms
        else:
             timeout_arg = str(timeout) # seconds

        timeout_flag = '-W' if platform.system().lower() != 'windows' else '-w'
        
        args = ['ping', param, '1', timeout_flag, timeout_arg, str(ip)]
        
        start = datetime.now()
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout + 1
        )
        elapsed = (datetime.now() - start).total_seconds() * 1000
        combined_output = (result.stdout or '') + (result.stderr or '')
        ttl = None
        ttl_match = re.search(r'\bttl=(\d+)', combined_output, re.IGNORECASE)
        if ttl_match:
            ttl = int(ttl_match.group(1))
        
        if result.returncode == 0:
            return True, round(elapsed, 2), ttl
        return False, None, ttl
    except Exception:
        return False, None, None

def check_port(ip: str, port: int, timeout: float = 0.5) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def scan_host_ports(ip: str, ports: List[int] = None, timeout: float = 0.5) -> List[Dict]:
    if ports is None:
        ports = list(COMMON_PORTS.keys())
    
    open_ports = []
    for port in ports:
        if check_port(ip, port, timeout):
            service = COMMON_PORTS.get(port, 'Unknown')
            open_ports.append({
                'port': port,
                'service': service,
                'state': 'open'
            })
    return open_ports

def get_hostname(ip: str) -> Optional[str]:
    try:
        return socket.gethostbyaddr(ip)[0]
    except:
        return None

def guess_host_type(services: List[Dict]) -> str:
    ports = {s['port'] for s in services}
    if 161 in ports: return 'network_device' # SNMP
    if 80 in ports or 443 in ports: return 'web_server'
    if 3306 in ports or 5432 in ports: return 'database'
    if 3389 in ports: return 'windows_server'
    if 22 in ports: return 'linux_server'
    return 'unknown'

def check_tcp_liveness(ip: str) -> bool:
    """
    Check if host is alive by connecting to common TCP ports.
    Useful if ICMP is blocked.
    """
    # Ports: SSH, HTTP, HTTPS, SMB, RPC
    ports = [22, 80, 443, 445, 135]
    for port in ports:
        if check_port(ip, port, timeout=0.2):
            return True
    return False

def get_active_hosts_from_arp() -> Dict[str, str]:
    """
    Parse local ARP table to find active hosts.
    Returns dict: {ip: mac}
    """
    active_hosts = {}
    try:
        if platform.system().lower() == 'windows':
            cmd = ['arp', '-a']
        else:
            cmd = ['arp', '-a'] # Mac/Linux usually supports -a too
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        
        # Parse output
        # Mac/Linux: ? (192.168.1.1) at 00:11:22:33:44:55 on en0 ...
        # Windows: 192.168.1.1       00-11-22-33-44-55     dynamic
        
        import re
        # Regex for IP
        ip_regex = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        # Regex for MAC
        mac_regex = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')
        
        for line in result.stdout.splitlines():
            ip_match = ip_regex.search(line)
            mac_match = mac_regex.search(line)
            if ip_match and mac_match:
                ip = ip_match.group(0)
                mac = mac_match.group(0).replace('-', ':').upper()
                # Exclude broadcast/multicast if needed, but usually fine
                if ip != '0.0.0.0' and not ip.endswith('.255'):
                    active_hosts[ip] = mac
    except:
        pass
    return active_hosts

def discover_host(
    ip: str,
    scan_ports: bool = True,
    known_mac: str = None,
    mdns_map: Optional[Dict] = None,
) -> Optional[Dict]:
    ping_ttl = None
    if known_mac:
        is_alive = True
        latency = 0
    else:
        is_alive, latency, ping_ttl = ping_host(ip)
        
        if not is_alive:
            if check_tcp_liveness(ip):
                is_alive = True
                latency = 0
            else:
                return None

    host_info = {
        'ip_address': ip,
        'status': 'up',
        'latency_ms': latency,
        'hostname': get_hostname(ip),
        'services': [],
        'suggested_type': 'unknown',
        'mac_address': known_mac,
    }

    mdns_record = lookup_mdns_for_ip(ip, mdns_map)
    if mdns_record:
        host_info['mdns_name'] = mdns_record.friendly_name
        host_info['mdns_hostname'] = mdns_record.hostname
        host_info['mdns_services'] = mdns_record.services
        host_info['apple_model'] = mdns_record.apple_model
        if not host_info.get('hostname'):
            host_info['hostname'] = mdns_record.hostname
        elif mdns_record.friendly_name and host_info['hostname'] == ip:
            host_info['hostname'] = mdns_record.hostname
    
    if scan_ports:
        host_info['services'] = scan_host_ports(ip)
    
    if not host_info.get('mac_address'):
        mac = get_mac_address(ip)
        if mac:
            host_info['mac_address'] = mac

    vendor = None
    mac_type = None
    if host_info.get('mac_address'):
        research = research_mac(
            host_info['mac_address'],
            hostname=host_info.get('hostname'),
            suggested_type=host_info.get('suggested_type'),
            services=host_info.get('services'),
        )
        host_info['vendor'] = research['vendor']
        host_info['mac_type'] = research['mac_type']
        host_info['vendor_source'] = research['vendor_source']
        host_info['device_hint'] = research['device_hint']
        vendor = research['vendor']
        mac_type = research['mac_type']

    fingerprint = fingerprint_device(
        ip,
        hostname=host_info.get('mdns_name') or host_info.get('hostname'),
        services=host_info.get('services'),
        mac_type=mac_type,
        vendor=vendor,
        ping_ttl=ping_ttl,
        mdns=mdns_record.to_dict() if mdns_record else None,
        deep_probe=scan_ports,
    )
    host_info.update(fingerprint.to_dict())

    # Enrich device hint with OS guess when we have private/unknown MACs
    if mac_type in ('private', 'unknown') and fingerprint.os_guess != 'Unknown':
        clue = f"Likely {fingerprint.os_guess} ({fingerprint.confidence} confidence)"
        if host_info.get('device_hint'):
            host_info['device_hint'] = f"{host_info['device_hint']} · {clue}"
        else:
            host_info['device_hint'] = clue

    return host_info

def perform_discovery(network: str, scan_ports: bool = True, max_workers: int = 50) -> Dict:
    try:
        ips_list = parse_network_range(network)
    except ValueError as e:
        return {'error': str(e)}
        
    arp_hosts = get_active_hosts_from_arp()
    mdns_map = discover_mdns_hosts(timeout=5.0 if scan_ports else 3.0)
    
    discovered = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ip = {
            executor.submit(discover_host, ip, scan_ports, arp_hosts.get(ip), mdns_map): ip 
            for ip in ips_list
        }
        for future in concurrent.futures.as_completed(future_to_ip):
            try:
                result = future.result()
                if result:
                    discovered.append(result)
            except:
                pass
                
    return {'hosts': discovered, 'mdns_devices_found': len(mdns_map)}

def get_mac_address(ip: str) -> Optional[str]:
    """
    Get MAC address for an IP using system arp command.
    Pings the host first to populate the ARP table if needed.
    """
    try:
        # Populate ARP cache
        ping_host(ip, timeout=1)

        if platform.system().lower() == 'windows':
            cmd = ['arp', '-a', ip]
        else:
            cmd = ['arp', '-n', ip]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        output = result.stdout

        import re
        mac_regex = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')
        match = mac_regex.search(output)
        if match:
            return match.group(0).replace('-', ':').upper()
    except Exception:
        pass
    return None

def get_default_gateway() -> Optional[str]:
    """
    Try to find default gateway IP using system commands.
    """
    try:
        if platform.system().lower() == 'windows':
            # route print 0.0.0.0
            cmd = ['route', 'print', '0.0.0.0']
        elif platform.system().lower() == 'darwin':
            # netstat -rn | grep default
            cmd = ['netstat', '-rn']
        else:
            # ip route show | grep default
            cmd = ['ip', 'route', 'show']
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        for line in result.stdout.splitlines():
            if 'default' in line or '0.0.0.0' in line:
                import re
                # Extract first IP
                ip_regex = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
                match = ip_regex.search(line)
                if match:
                     # On Linux 'default via 192.168.1.1' -> IP is 2nd word usually?
                     # Regex finds first IP. 
                     # On Mac 'default 192.168.1.1 ...' -> IP is 2nd word.
                     matches = ip_regex.findall(line)
                     for ip in matches:
                         if ip != '0.0.0.0':
                             return ip
    except:
        pass
    return None

def parse_network_range(network: str) -> List[str]:
    ips = []
    try:
        # Check for hyphenated range (e.g., 192.168.1.1-254)
        if '-' in network:
            # Check if simple range like 192.168.1.1-50
            if '-' in network.split('.')[-1] and network.count('-') == 1:
                parts = network.rsplit('.', 1)
                base = parts[0]
                last_octet_range = parts[1]
                start, end = map(int, last_octet_range.split('-'))
                if end < start:
                    raise ValueError("Invalid range: end < start")
                if end - start > 255:
                     raise ValueError("Range too large")
                for i in range(start, end + 1):
                    ips.append(f"{base}.{i}")
            else:
                # Could be complex range, for now only support last octet range or failing
                # Try validation as single IP if hyphen is part of hostname (unlikely for usage here)
                pass
        elif '/' in network:
            net = ipaddress.ip_network(network, strict=False)
            if net.num_addresses > 1024: # Limit scan size for safety
                raise ValueError("Network too large. Limit 1024 hosts.")
            for ip in net.hosts():
                ips.append(str(ip))
        else:
            ipaddress.ip_address(network)
            ips.append(network)
            
    except Exception as e:
        raise ValueError(f"Invalid network: {e}")
    
    if not ips and '-' in network:
          raise ValueError("Invalid range format. Use CIDR or 1.2.3.1-50")

    return ips


