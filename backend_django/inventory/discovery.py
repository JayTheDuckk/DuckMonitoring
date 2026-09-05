"""
Network Discovery Utility
"""

import socket
import subprocess
import ipaddress
import concurrent.futures
import time
from datetime import datetime
import platform
import re
from typing import List, Dict, Optional, Tuple

from core.utils.mac_vendor import parse_mac_from_text, research_mac
from core.utils.device_fingerprint import fingerprint_device, FINGERPRINT_PORTS
from core.utils.quiet_host_probe import (
    deep_probe_quiet_host,
    describe_quiet_host,
    is_sparse_host,
    stamp_privacy_device,
)
from core.utils.ssdp_resolver import discover_ssdp_hosts, guess_vendor_from_ssdp
from core.utils.mdns_resolver import (
    MdnsDiscoveryResult,
    MdnsRecord,
    _hostname_from_friendly,
    _pick_better_friendly_name,
    discover_mdns_hosts,
    enrich_vendor_from_mdns,
    lookup_mdns_for_ip,
    mac_from_mdns_record,
)

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
        ip_regex = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        
        for line in result.stdout.splitlines():
            if '(incomplete)' in line.lower():
                continue
            ip_match = ip_regex.search(line)
            if not ip_match:
                continue
            mac = parse_mac_from_text(line)
            if ip_match and mac:
                ip = ip_match.group(0)
                if ip != '0.0.0.0' and not ip.endswith('.255'):
                    active_hosts[ip] = mac
    except:
        pass
    return active_hosts

def discover_host(
    ip: str,
    scan_ports: bool = True,
    known_mac: str = None,
    mdns_result: Optional[MdnsDiscoveryResult] = None,
) -> Optional[Dict]:
    ping_alive, latency, ping_ttl = ping_host(ip, timeout=2 if scan_ports else 1)
    if known_mac:
        is_alive = True
        if not ping_alive:
            latency = 0
    else:
        is_alive = ping_alive
        if not is_alive:
            if check_tcp_liveness(ip):
                is_alive = True
                latency = 0
            else:
                return None

    host_info = {
        'ip_address': ip,
        'status': 'up',
        'latency_ms': latency if latency else None,
        'latency': latency if latency else None,
        'ping_ttl': ping_ttl,
        'hostname': get_hostname(ip),
        'services': [],
        'suggested_type': 'unknown',
        'mac_address': known_mac,
    }

    if scan_ports:
        host_info['services'] = scan_host_ports(ip)
    
    if not host_info.get('mac_address'):
        probe_ports = [s['port'] for s in host_info.get('services', []) if s.get('port')]
        mac = get_mac_address(ip, probe_ports=probe_ports)
        if mac:
            host_info['mac_address'] = mac

    mdns_record = lookup_mdns_for_ip(
        ip,
        mdns_result,
        known_mac=host_info.get('mac_address'),
    )
    if mdns_record:
        host_info['mdns_name'] = mdns_record.friendly_name
        host_info['mdns_hostname'] = mdns_record.hostname
        host_info['mdns_services'] = mdns_record.services
        host_info['apple_model'] = mdns_record.apple_model
        if not host_info.get('hostname'):
            host_info['hostname'] = mdns_record.hostname
        elif mdns_record.friendly_name and host_info['hostname'] == ip:
            host_info['hostname'] = mdns_record.hostname
        if not host_info.get('mac_address'):
            mdns_mac = mac_from_mdns_record(mdns_record)
            if mdns_mac:
                host_info['mac_address'] = mdns_mac
                host_info['mac_source'] = 'mdns'

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

    enrich_vendor_from_mdns(host_info, mdns_record)
    vendor = host_info.get('vendor')

    fingerprint = fingerprint_device(
        ip,
        hostname=host_info.get('mdns_name') or host_info.get('hostname'),
        services=host_info.get('services'),
        mac_type=mac_type,
        vendor=vendor,
        ping_ttl=host_info.get('ping_ttl'),
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


def _apply_ssdp_record(host_info: Dict, ssdp_record) -> None:
    host_info['ssdp_name'] = ssdp_record.friendly_name
    host_info['ssdp_server'] = ssdp_record.server
    if not host_info.get('hostname'):
        host_info['hostname'] = ssdp_record.friendly_name

    vendor = guess_vendor_from_ssdp(ssdp_record)
    if vendor and host_info.get('mac_type') in ('private', 'unknown', None):
        host_info['vendor'] = vendor
        host_info['vendor_source'] = 'ssdp_guess'
        hint = f"Vendor inferred from UPnP/SSDP ({ssdp_record.server or ssdp_record.friendly_name})"
        if host_info.get('device_hint'):
            host_info['device_hint'] = f"{hint} · {host_info['device_hint']}"
        else:
            host_info['device_hint'] = hint


def _enrich_sparse_host(host_info: Dict, ssdp_map: Dict, scan_ports: bool) -> None:
    if not is_sparse_host(host_info) and host_info.get('services'):
        return

    ssdp_record = ssdp_map.get(host_info['ip_address'])
    if ssdp_record:
        _apply_ssdp_record(host_info, ssdp_record)

    if scan_ports and not host_info.get('services'):
        probe = deep_probe_quiet_host(host_info['ip_address'], check_port)
        if probe['services']:
            host_info['services'] = probe['services']
        host_info['discovery_signals'] = probe.get('discovery_signals', [])
    elif not host_info.get('discovery_signals'):
        host_info['discovery_signals'] = ['no_inbound_services']

    quiet_hint = describe_quiet_host(host_info)
    if quiet_hint:
        if host_info.get('device_hint'):
            host_info['device_hint'] = f"{host_info['device_hint']} · {quiet_hint}"
        else:
            host_info['device_hint'] = quiet_hint

    fingerprint = fingerprint_device(
        host_info['ip_address'],
        hostname=host_info.get('mdns_name') or host_info.get('hostname'),
        services=host_info.get('services'),
        mac_type=host_info.get('mac_type'),
        vendor=host_info.get('vendor'),
        ping_ttl=host_info.get('ping_ttl'),
        mdns=None,
        deep_probe=scan_ports,
    )
    host_info.update(fingerprint.to_dict())


def _host_has_service(host_info: Dict, port: int) -> bool:
    return any(s.get('port') == port for s in host_info.get('services', []))


def _apply_mdns_record(host_info: Dict, mdns_record: MdnsRecord) -> None:
    host_info['mdns_name'] = mdns_record.friendly_name
    host_info['mdns_hostname'] = mdns_record.hostname
    host_info['mdns_services'] = mdns_record.services
    host_info['apple_model'] = mdns_record.apple_model
    if not host_info.get('hostname') or host_info.get('hostname') == host_info['ip_address']:
        host_info['hostname'] = mdns_record.hostname

    enrich_vendor_from_mdns(host_info, mdns_record)

    fingerprint = fingerprint_device(
        host_info['ip_address'],
        hostname=host_info.get('mdns_name') or host_info.get('hostname'),
        services=host_info.get('services'),
        mac_type=host_info.get('mac_type'),
        vendor=host_info.get('vendor'),
        mdns=mdns_record.to_dict(),
        deep_probe=bool(host_info.get('services')),
    )
    host_info.update(fingerprint.to_dict())


def _assign_unmatched_mdns(discovered: List[Dict], mdns_result: MdnsDiscoveryResult) -> None:
    """Attach loopback-only Apple mDNS records to hosts with private MACs."""
    assigned_names = {h.get('mdns_name') for h in discovered if h.get('mdns_name')}
    apple_markers = ('_companion-link', '_airplay', '_raop', '_device-info', '_apple-mobdev', '_ssh')

    unmatched = [
        record for record in mdns_result.by_mac.values()
        if record.friendly_name
        and record.friendly_name not in assigned_names
        and any(marker in svc for svc in record.services for marker in apple_markers)
    ]
    if not unmatched:
        return

    candidates = [
        host for host in discovered
        if not host.get('mdns_name')
        and host.get('mac_type') == 'private'
        and _host_has_service(host, 22)
    ]
    if len(candidates) != 1:
        return

    friendly_name = unmatched[0].friendly_name
    for record in unmatched[1:]:
        friendly_name = _pick_better_friendly_name(friendly_name, record.friendly_name)

    donor = max(unmatched, key=lambda record: (bool(record.apple_model), len(record.services)))
    merged = MdnsRecord(
        ip_address=candidates[0]['ip_address'],
        friendly_name=friendly_name,
        hostname=_hostname_from_friendly(friendly_name) or friendly_name,
        services=list({svc for record in unmatched for svc in record.services}),
        properties={k: v for record in unmatched for k, v in record.properties.items()},
        apple_model=next((record.apple_model for record in unmatched if record.apple_model), None),
        mac_address=donor.mac_address,
    )
    _apply_mdns_record(candidates[0], merged)


def perform_discovery(network: str, scan_ports: bool = True, max_workers: int = 50) -> Dict:
    try:
        ips_list = parse_network_range(network)
    except ValueError as e:
        return {'error': str(e)}
        
    arp_hosts = get_active_hosts_from_arp()
    mdns_result = discover_mdns_hosts(timeout=8.0 if scan_ports else 5.0)
    ssdp_map = discover_ssdp_hosts(timeout=4.0 if scan_ports else 2.0)
    
    discovered = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ip = {
            executor.submit(discover_host, ip, scan_ports, arp_hosts.get(ip), mdns_result): ip 
            for ip in ips_list
        }
        for future in concurrent.futures.as_completed(future_to_ip):
            try:
                result = future.result()
                if result:
                    discovered.append(result)
            except:
                pass

    _assign_unmatched_mdns(discovered, mdns_result)

    if scan_ports:
        for host_info in discovered:
            if is_sparse_host(host_info) or (
                host_info.get('mac_type') == 'private' and not host_info.get('mdns_name')
            ):
                _enrich_sparse_host(host_info, ssdp_map, scan_ports=True)
            elif host_info['ip_address'] in ssdp_map:
                _apply_ssdp_record(host_info, ssdp_map[host_info['ip_address']])

    for host_info in discovered:
        stamp_privacy_device(host_info)

    return {'hosts': discovered, 'mdns_devices_found': mdns_result.device_count()}

def get_mac_address(ip: str, probe_ports: Optional[List[int]] = None) -> Optional[str]:
    """
    Get MAC address for an IP using system arp command.
    Pings the host first to populate the ARP table if needed.
    """
    try:
        ping_host(ip, timeout=1)
        mac = _read_mac_from_arp(ip)
        if mac:
            return mac

        for port in probe_ports or [8009, 8008, 443, 80, 22]:
            if check_port(ip, port, timeout=0.3):
                time.sleep(0.15)
                mac = _read_mac_from_arp(ip)
                if mac:
                    return mac
    except Exception:
        pass
    return None


def _read_mac_from_arp(ip: str) -> Optional[str]:
    try:
        if platform.system().lower() == 'windows':
            cmd = ['arp', '-a', ip]
        else:
            cmd = ['arp', '-n', ip]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        return parse_mac_from_text(result.stdout)
    except Exception:
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


