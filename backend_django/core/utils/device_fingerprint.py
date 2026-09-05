"""
Passive device fingerprinting for network discovery.

Combines hostname patterns, open ports, service banners, MAC context,
and ping TTL to estimate OS and device class.
"""

from __future__ import annotations

import re
import socket
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.utils.quiet_host_probe import stamp_privacy_device


FINGERPRINT_PORTS = {
    22: 'SSH',
    80: 'HTTP',
    443: 'HTTPS',
    445: 'SMB',
    135: 'RPC',
    161: 'SNMP',
    548: 'AFP',
    5353: 'MDNS',
    62078: 'APPLE_SYNC',
    8008: 'HTTP_ALT',
    8009: 'CAST',
    8080: 'HTTP_PROXY',
    8443: 'HTTPS_ALT',
    3389: 'RDP',
    3306: 'MYSQL',
    5432: 'POSTGRES',
    6379: 'REDIS',
}


@dataclass
class FingerprintScore:
    os_name: str
    device_class: str
    points: int
    reason: str


@dataclass
class DeviceFingerprint:
    os_guess: str = 'Unknown'
    device_class: str = 'unknown'
    confidence: str = 'low'
    suggested_type: str = 'unknown'
    identification_clues: List[str] = field(default_factory=list)
    privacy_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        data = {
            'os_guess': self.os_guess,
            'device_class': self.device_class,
            'confidence': self.confidence,
            'suggested_type': self.suggested_type,
            'identification_clues': self.identification_clues,
        }
        if self.privacy_reason:
            data['privacy_reason'] = self.privacy_reason
        return data


def _read_banner(ip: str, port: int, timeout: float = 1.0, probe: bytes = b'') -> Optional[str]:
    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            if probe:
                sock.sendall(probe)
            data = sock.recv(512)
            if data:
                return data.decode('utf-8', errors='ignore').strip()
    except Exception:
        return None
    return None


def _read_http_server(ip: str, port: int, use_tls: bool = False, timeout: float = 1.0) -> Optional[str]:
    try:
        if use_tls:
            import ssl
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with socket.create_connection((ip, port), timeout=timeout) as raw:
                with context.wrap_socket(raw, server_hostname=ip) as sock:
                    sock.sendall(b'HEAD / HTTP/1.0\r\nHost: localhost\r\n\r\n')
                    data = sock.recv(1024).decode('utf-8', errors='ignore')
        else:
            with socket.create_connection((ip, port), timeout=timeout) as sock:
                sock.sendall(b'HEAD / HTTP/1.0\r\nHost: localhost\r\n\r\n')
                data = sock.recv(1024).decode('utf-8', errors='ignore')
        match = re.search(r'(?i)^Server:\s*(.+)$', data, re.MULTILINE)
        return match.group(1).strip() if match else None
    except Exception:
        return None


def _parse_ping_ttl(ping_output: str) -> Optional[int]:
    match = re.search(r'\bttl=(\d+)', ping_output, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r'\btiempo=(\d+)', ping_output, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def collect_probe_data(ip: str, open_ports: List[int]) -> Dict:
    """Gather banners and headers from open ports."""
    probes: Dict[str, str] = {}
    port_set = set(open_ports)

    if 22 in port_set:
        banner = _read_banner(ip, 22)
        if banner:
            probes['ssh_banner'] = banner.split('\n')[0][:200]

    for port, use_tls in ((80, False), (8080, False), (443, True), (8443, True)):
        if port in port_set:
            server = _read_http_server(ip, port, use_tls=use_tls)
            if server:
                probes[f'http_server_{port}'] = server[:200]

    return probes


def _score_from_mdns(mdns: Optional[Dict]) -> List[FingerprintScore]:
    if not mdns:
        return []

    scores: List[FingerprintScore] = []
    friendly = (mdns.get('friendly_name') or '').lower()
    apple_model = (mdns.get('apple_model') or '').lower()
    services = mdns.get('mdns_services') or []

    if apple_model.startswith('mac') or 'macbook' in friendly or 'imac' in friendly:
        label = mdns.get('apple_model') or 'Mac'
        scores.append(FingerprintScore('macOS', 'laptop', 10, f'mDNS: {mdns.get("friendly_name")} ({label})'))
    elif apple_model.startswith('iphone') or 'iphone' in friendly:
        scores.append(FingerprintScore('iOS', 'phone', 10, f'mDNS: {mdns.get("friendly_name")} ({mdns.get("apple_model") or "iPhone"})'))
    elif apple_model.startswith('ipad') or 'ipad' in friendly:
        scores.append(FingerprintScore('iOS', 'tablet', 10, f'mDNS: {mdns.get("friendly_name")}'))
    elif any('_googlecast._tcp' in s for s in services):
        model = mdns.get('mdns_properties', {}).get('md') or mdns.get('friendly_name')
        scores.append(FingerprintScore('Embedded Linux', 'iot', 9, f'mDNS Cast device: {model}'))
    elif any('_airplay._tcp' in s for s in services):
        scores.append(FingerprintScore('Embedded Linux', 'iot', 7, f'mDNS AirPlay device: {mdns.get("friendly_name")}'))
    elif any('_companion-link._tcp' in s for s in services):
        scores.append(FingerprintScore('macOS/iOS', 'mobile', 9, f'mDNS Apple companion device: {mdns.get("friendly_name")}'))
    elif any('_workstation._tcp' in s for s in services):
        scores.append(FingerprintScore('Linux/Windows/macOS', 'workstation', 6, f'mDNS workstation: {mdns.get("friendly_name")}'))
    elif friendly:
        scores.append(FingerprintScore('Unknown', 'unknown', 3, f'mDNS name: {mdns.get("friendly_name")}'))

    return scores


def _score_from_hostname(hostname: Optional[str]) -> List[FingerprintScore]:
    if not hostname:
        return []

    name = hostname.lower().strip('.')
    scores: List[FingerprintScore] = []

    patterns = [
        (r'iphone|ipad|ipod', 'iOS', 'phone', 8, 'Hostname suggests Apple mobile device'),
        (r'macbook|imac|mac-mini|mac\.|mac-', 'macOS', 'laptop', 8, 'Hostname suggests Mac'),
        (r'android', 'Android', 'phone', 8, 'Hostname mentions Android'),
        (r'pixel|galaxy|samsung-sm-|oneplus|xiaomi|redmi', 'Android', 'phone', 6, 'Hostname suggests Android phone'),
        (r'windows|desktop-|pc-|win-', 'Windows', 'desktop', 7, 'Hostname suggests Windows PC'),
        (r'raspberrypi|raspi', 'Linux', 'embedded', 8, 'Hostname suggests Raspberry Pi'),
        (r'ubuntu|debian|centos|fedora|rocky|alpine', 'Linux', 'server', 7, 'Hostname suggests Linux distro'),
        (r'router|gateway|ap-|unifi|synology|nas-', 'Embedded Linux', 'router', 6, 'Hostname suggests network appliance'),
        (r'echo|alexa|firetv|chromecast|roku|esp[0-9]', 'Embedded Linux', 'iot', 6, 'Hostname suggests smart/IoT device'),
    ]

    for pattern, os_name, device_class, points, reason in patterns:
        if re.search(pattern, name):
            scores.append(FingerprintScore(os_name, device_class, points, reason))

    if name.endswith('.local'):
        scores.append(FingerprintScore('macOS/iOS', 'mobile', 4, 'mDNS .local hostname (common on Apple devices)'))

    return scores


def _score_from_banners(probes: Dict[str, str]) -> List[FingerprintScore]:
    scores: List[FingerprintScore] = []
    ssh = probes.get('ssh_banner', '')
    if ssh:
        ssh_l = ssh.lower()
        if 'darwin' in ssh_l or 'macos' in ssh_l:
            scores.append(FingerprintScore('macOS', 'laptop', 9, f'SSH banner: {ssh[:80]}'))
        elif 'ubuntu' in ssh_l or 'debian' in ssh_l:
            scores.append(FingerprintScore('Linux', 'server', 8, f'SSH banner: {ssh[:80]}'))
        elif 'dropbear' in ssh_l:
            scores.append(FingerprintScore('Embedded Linux', 'iot', 7, f'SSH banner: {ssh[:80]}'))
        elif 'openssh' in ssh_l:
            scores.append(FingerprintScore('Linux/Unix', 'server', 5, f'SSH banner: {ssh[:80]}'))
        elif 'windows' in ssh_l:
            scores.append(FingerprintScore('Windows', 'server', 8, f'SSH banner: {ssh[:80]}'))

    for key, value in probes.items():
        if not key.startswith('http_server_'):
            continue
        server_l = value.lower()
        if 'ubuntu' in server_l or 'debian' in server_l:
            scores.append(FingerprintScore('Linux', 'server', 6, f'HTTP Server header: {value[:80]}'))
        elif 'microsoft-iis' in server_l:
            scores.append(FingerprintScore('Windows', 'server', 8, f'HTTP Server header: {value[:80]}'))
        elif 'router' in server_l or 'tp-link' in server_l or 'netgear' in server_l or 'asuswrt' in server_l:
            scores.append(FingerprintScore('Embedded Linux', 'router', 8, f'HTTP Server header: {value[:80]}'))
        elif 'amazon' in server_l or 'cloudfront' in server_l:
            scores.append(FingerprintScore('Embedded Linux', 'iot', 5, f'HTTP Server header: {value[:80]}'))
        elif 'nginx' in server_l:
            scores.append(FingerprintScore('Linux', 'server', 4, f'HTTP Server header: {value[:80]}'))
        elif 'apache' in server_l:
            scores.append(FingerprintScore('Linux', 'server', 4, f'HTTP Server header: {value[:80]}'))

    return scores


def _score_from_ports(ports: set) -> List[FingerprintScore]:
    scores: List[FingerprintScore] = []

    if 3389 in ports or (445 in ports and 135 in ports):
        scores.append(FingerprintScore('Windows', 'desktop', 8, 'Windows management/file-sharing ports open'))
    if 62078 in ports or 548 in ports:
        scores.append(FingerprintScore('macOS/iOS', 'mobile', 7, 'Apple service ports detected'))
    if 5353 in ports and not ({22, 80, 443, 445} & ports):
        scores.append(FingerprintScore('Mobile/IoT', 'iot', 4, 'mDNS only — common on phones and smart devices'))
    if 161 in ports and 80 in ports:
        scores.append(FingerprintScore('Embedded Linux', 'router', 7, 'SNMP + HTTP — likely router or switch'))
    if 161 in ports:
        scores.append(FingerprintScore('Embedded Linux', 'network_device', 5, 'SNMP enabled'))
    if 22 in ports and 6379 in ports and 3306 not in ports and 5432 not in ports:
        scores.append(FingerprintScore('macOS/Linux', 'laptop', 5, 'Developer ports SSH + Redis (common on workstations)'))
    if 22 in ports and not ({80, 443, 445, 3389} & ports):
        scores.append(FingerprintScore('Linux/Unix', 'server', 4, 'SSH exposed without desktop service ports'))
    if 8009 in ports or 8008 in ports:
        scores.append(FingerprintScore('Embedded Linux', 'iot', 6, 'Cast/streaming device ports detected'))
    if 3306 in ports or 5432 in ports:
        scores.append(FingerprintScore('Linux', 'server', 6, 'Database service detected'))
    if 80 in ports or 443 in ports:
        scores.append(FingerprintScore('Linux/Embedded', 'server', 3, 'Web service detected'))

    return scores


def _score_from_mac(mac_type: Optional[str], vendor: Optional[str]) -> List[FingerprintScore]:
    scores: List[FingerprintScore] = []
    vendor_l = (vendor or '').lower()

    if mac_type == 'private':
        scores.append(FingerprintScore('iOS/Android/macOS', 'mobile', 5, 'Privacy MAC with no open ports — often a phone or tablet with inbound firewall'))

    vendor_map = [
        ('apple', 'macOS/iOS', 'mobile', 7, 'Apple network hardware'),
        ('microsoft', 'Windows', 'desktop', 6, 'Microsoft network hardware'),
        ('amazon', 'Embedded Linux', 'iot', 6, 'Amazon smart device'),
        ('google', 'Embedded Linux', 'iot', 6, 'Google/Chromecast device'),
        ('tp-link', 'Embedded Linux', 'router', 7, 'TP-Link network device'),
        ('ubiquiti', 'Embedded Linux', 'router', 7, 'Ubiquiti network device'),
        ('raspberry pi', 'Linux', 'embedded', 8, 'Raspberry Pi'),
        ('vmware', 'Linux', 'server', 5, 'Virtual machine'),
        ('cloud network technology', 'Embedded Linux', 'iot', 4, 'Foxconn Wi‑Fi module (OEM smart device or PC)'),
    ]
    for needle, os_name, device_class, points, reason in vendor_map:
        if needle in vendor_l:
            scores.append(FingerprintScore(os_name, device_class, points, reason))
            break

    return scores


def _score_from_ttl(ttl: Optional[int]) -> List[FingerprintScore]:
    if ttl is None:
        return []
    if ttl <= 64:
        return [FingerprintScore('Linux/Unix/macOS/iOS/Android', 'mobile', 4, f'Ping TTL {ttl} (typical for Unix-like/mobile OS)')]
    if ttl <= 128:
        return [FingerprintScore('Windows', 'desktop', 4, f'Ping TTL {ttl} (typical for Windows)')]
    return [FingerprintScore('Network Device', 'router', 3, f'Ping TTL {ttl} (typical for routers)')]


def _pick_best(scores: List[FingerprintScore]) -> DeviceFingerprint:
    if not scores:
        return DeviceFingerprint(
            os_guess='Unknown',
            device_class='unknown',
            confidence='low',
            suggested_type='unknown',
            identification_clues=['Insufficient signals — try full port scan or install an agent'],
        )

    os_totals: Dict[str, int] = {}
    class_totals: Dict[str, int] = {}
    clues: List[str] = []

    for score in scores:
        os_totals[score.os_name] = os_totals.get(score.os_name, 0) + score.points
        class_totals[score.device_class] = class_totals.get(score.device_class, 0) + score.points
        if score.reason not in clues:
            clues.append(score.reason)

    best_os = max(os_totals, key=os_totals.get)
    best_class = max(class_totals, key=class_totals.get)
    best_points = os_totals[best_os]

    if best_points >= 8:
        confidence = 'high'
    elif best_points >= 5:
        confidence = 'medium'
    else:
        confidence = 'low'

    suggested_type = _to_suggested_type(best_os, best_class)
    return DeviceFingerprint(
        os_guess=best_os,
        device_class=best_class,
        confidence=confidence,
        suggested_type=suggested_type,
        identification_clues=clues[:6],
    )


def _to_suggested_type(os_name: str, device_class: str) -> str:
    mapping = {
        'macOS': 'macos',
        'macOS/iOS': 'apple_device',
        'iOS': 'ios',
        'Android': 'android',
        'Linux': 'linux',
        'Linux/Unix': 'linux',
        'Linux/Embedded': 'linux',
        'Embedded Linux': 'embedded',
        'Windows': 'windows',
        'Mobile/IoT': 'mobile',
        'Mobile/Desktop': 'mobile',
        'Network Device': 'network_device',
    }
    if os_name in mapping:
        return mapping[os_name]
    if device_class == 'router':
        return 'network_device'
    if device_class == 'server':
        return 'linux_server'
    if device_class in ('phone', 'mobile', 'tablet', 'laptop', 'desktop'):
        return 'workstation'
    if device_class == 'iot':
        return 'iot_device'
    if device_class == 'privacy_device':
        return 'privacy_device'
    return 'unknown'


def fingerprint_device(
    ip: str,
    *,
    hostname: Optional[str] = None,
    services: Optional[List[Dict]] = None,
    mac_type: Optional[str] = None,
    vendor: Optional[str] = None,
    ping_ttl: Optional[int] = None,
    mdns: Optional[Dict] = None,
    deep_probe: bool = True,
) -> DeviceFingerprint:
    """
    Estimate OS and device class from all available discovery signals.
    """
    services = services or []
    open_ports = {s['port'] for s in services if s.get('port')}

    scores: List[FingerprintScore] = []
    scores.extend(_score_from_mdns(mdns))
    scores.extend(_score_from_hostname(hostname))
    scores.extend(_score_from_ports(open_ports))
    scores.extend(_score_from_mac(mac_type, vendor))
    scores.extend(_score_from_ttl(ping_ttl))

    if deep_probe and open_ports:
        probes = collect_probe_data(ip, list(open_ports))
        scores.extend(_score_from_banners(probes))

    result = _pick_best(scores)
    stamped = stamp_privacy_device({
        'device_class': result.device_class,
        'mac_type': mac_type,
        'hostname': hostname,
        'mdns_name': (mdns or {}).get('friendly_name'),
        'services': services,
        'ping_ttl': ping_ttl,
        'identification_clues': list(result.identification_clues),
        'suggested_type': result.suggested_type,
    })
    result.device_class = stamped['device_class']
    result.suggested_type = stamped.get('suggested_type') or result.suggested_type
    result.identification_clues = stamped.get('identification_clues') or result.identification_clues
    result.privacy_reason = stamped.get('privacy_reason')
    return result
