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
    5555: 'ADB',
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

# Only these labels are specific enough to show as an OS.
SPECIFIC_OS = frozenset({
    'Windows',
    'macOS',
    'iOS',
    'tvOS',
    'Android',
    'Linux',
    'Embedded Linux',
})

MIN_OS_POINTS = 6


def is_specific_os(os_name: Optional[str]) -> bool:
    return bool(os_name) and os_name in SPECIFIC_OS


def _service_has(services: List[str], needle: str) -> bool:
    token = needle.lower()
    return any(token in str(service).lower() for service in services)


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
    props = mdns.get('mdns_properties') or {}
    cast_model = str(props.get('md') or props.get('fn') or mdns.get('friendly_name') or '').lower()

    if apple_model.startswith('mac') or 'macbook' in friendly or 'imac' in friendly or 'mac mini' in friendly:
        label = mdns.get('apple_model') or 'Mac'
        scores.append(FingerprintScore('macOS', 'laptop', 10, f'mDNS: {mdns.get("friendly_name")} ({label})'))
    elif apple_model.startswith('iphone') or 'iphone' in friendly:
        scores.append(FingerprintScore('iOS', 'phone', 10, f'mDNS: {mdns.get("friendly_name")} ({mdns.get("apple_model") or "iPhone"})'))
    elif apple_model.startswith('ipad') or 'ipad' in friendly:
        scores.append(FingerprintScore('iOS', 'tablet', 10, f'mDNS: {mdns.get("friendly_name")}'))
    elif 'appletv' in apple_model or 'apple tv' in friendly or apple_model.startswith('appletv'):
        scores.append(FingerprintScore('tvOS', 'tv', 10, f'mDNS: {mdns.get("friendly_name")} ({mdns.get("apple_model") or "Apple TV"})'))
    elif _service_has(services, '_androidtvremote2') or 'android tv' in friendly:
        scores.append(FingerprintScore('Android', 'tv', 10, f'mDNS Android TV: {mdns.get("friendly_name")}'))
    elif _service_has(services, '_amzn-wplay') or 'firetv' in friendly or 'fire tv' in friendly:
        scores.append(FingerprintScore('Android', 'tv', 9, f'mDNS Fire TV / Fire OS: {mdns.get("friendly_name")}'))
    elif _service_has(services, '_googlecast'):
        if any(token in cast_model or token in friendly for token in (
            'android tv', 'google tv', 'chromecast', 'shield', 'bravia', 'fire tv', 'firetv',
        )):
            scores.append(FingerprintScore('Android', 'tv', 8, f'mDNS Cast TV: {cast_model or mdns.get("friendly_name")}'))
        elif any(token in cast_model or token in friendly for token in ('nest', 'home mini', 'speaker', 'audio')):
            scores.append(FingerprintScore('Embedded Linux', 'iot', 8, f'mDNS Cast speaker: {cast_model or mdns.get("friendly_name")}'))
        else:
            scores.append(FingerprintScore('Android', 'tv', 6, f'mDNS Cast device: {cast_model or mdns.get("friendly_name")}'))
    elif _service_has(services, '_apple-mobdev'):
        scores.append(FingerprintScore('iOS', 'phone', 8, f'mDNS Apple mobile sync: {mdns.get("friendly_name")}'))
    elif _service_has(services, '_companion-link'):
        if _service_has(services, '_ssh') or _service_has(services, '_workstation') or _service_has(services, '_smb'):
            scores.append(FingerprintScore('macOS', 'laptop', 8, f'mDNS Apple workstation: {mdns.get("friendly_name")}'))
        else:
            scores.append(FingerprintScore('iOS', 'phone', 7, f'mDNS Apple companion device: {mdns.get("friendly_name")}'))
    elif _service_has(services, '_workstation') and apple_model:
        scores.append(FingerprintScore('macOS', 'laptop', 7, f'mDNS workstation on Apple hardware: {mdns.get("friendly_name")}'))
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
        (r'echo|alexa|chromecast|roku|esp[0-9]', 'Embedded Linux', 'iot', 6, 'Hostname suggests smart/IoT device'),
        (r'firetv|fire-tv|firestick|aftmm|aftsss', 'Android', 'tv', 8, 'Hostname suggests Amazon Fire OS (Android)'),
        (r'appletv|apple-tv', 'tvOS', 'tv', 8, 'Hostname suggests Apple TV'),
    ]

    for pattern, os_name, device_class, points, reason in patterns:
        if re.search(pattern, name):
            scores.append(FingerprintScore(os_name, device_class, points, reason))

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
            scores.append(FingerprintScore('Unknown', 'server', 2, f'SSH is OpenSSH — Linux, macOS, or BSD; banner does not name one'))
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
    if 548 in ports:
        scores.append(FingerprintScore('macOS', 'laptop', 8, 'AFP file sharing — typical of macOS'))
    if 62078 in ports:
        scores.append(FingerprintScore('iOS', 'phone', 8, 'Apple lockdownd port — typical of iPhone/iPad'))
    if 5555 in ports:
        scores.append(FingerprintScore('Android', 'phone', 8, 'ADB port — typical of Android'))
    if 5353 in ports and not ({22, 80, 443, 445} & ports):
        scores.append(FingerprintScore('Unknown', 'iot', 2, 'mDNS only — common on phones and smart devices'))
    if 161 in ports and 80 in ports:
        scores.append(FingerprintScore('Embedded Linux', 'router', 7, 'SNMP + HTTP — likely router or switch'))
    if 161 in ports:
        scores.append(FingerprintScore('Embedded Linux', 'network_device', 5, 'SNMP enabled'))
    if 8009 in ports or 8008 in ports:
        scores.append(FingerprintScore('Android', 'tv', 6, 'Cast/Android TV ports detected'))
    if 3306 in ports or 5432 in ports:
        scores.append(FingerprintScore('Linux', 'server', 6, 'Database service detected'))

    return scores


def _score_from_mac(
    mac_type: Optional[str],
    vendor: Optional[str],
    *,
    ports: Optional[set] = None,
    hostname: Optional[str] = None,
) -> List[FingerprintScore]:
    scores: List[FingerprintScore] = []
    vendor_l = (vendor or '').lower()
    ports = ports or set()
    name = (hostname or '').lower()

    if mac_type == 'private':
        scores.append(FingerprintScore('Unknown', 'mobile', 2, 'Privacy MAC — common on phones; not enough to name the OS'))

    if 'apple' in vendor_l:
        if {22, 548, 5900, 445} & ports or any(token in name for token in ('macbook', 'imac', 'mac-mini', 'mac.')):
            scores.append(FingerprintScore('macOS', 'laptop', 8, 'Apple hardware with workstation services'))
        elif 62078 in ports or any(token in name for token in ('iphone', 'ipad', 'ipod')):
            scores.append(FingerprintScore('iOS', 'phone', 8, 'Apple hardware with mobile sync/name'))
        elif 'tv' in name or 'appletv' in name:
            scores.append(FingerprintScore('tvOS', 'tv', 8, 'Apple TV hardware'))
        elif mac_type == 'private' and not ports:
            scores.append(FingerprintScore('iOS', 'phone', 6, 'Apple vendor + privacy MAC and no inbound ports — usually an iPhone'))
        return scores

    android_vendors = (
        'samsung', 'google', 'xiaomi', 'redmi', 'oneplus', 'huawei', 'honor',
        'motorola', 'oppo', 'vivo', 'pixel',
    )
    if any(token in vendor_l for token in android_vendors):
        if mac_type == 'private' or not ports:
            scores.append(FingerprintScore('Android', 'phone', 7, f'{vendor} hardware — typically Android'))
        else:
            scores.append(FingerprintScore('Android', 'phone', 6, f'{vendor} network hardware'))
        return scores

    if 'amazon' in vendor_l:
        if 'echo' in name or 'alexa' in name:
            scores.append(FingerprintScore('Embedded Linux', 'iot', 7, 'Amazon Echo / Alexa device'))
        else:
            scores.append(FingerprintScore('Android', 'tv', 7, 'Amazon hardware — Fire OS is Android-based'))
        return scores

    vendor_map = [
        ('microsoft', 'Windows', 'desktop', 6, 'Microsoft network hardware'),
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
        return [FingerprintScore('Unknown', 'unknown', 1, f'Ping TTL {ttl} is Unix-like (Linux, macOS, iOS, and Android all use 64)')]
    if ttl <= 128:
        return [FingerprintScore('Windows', 'desktop', 6, f'Ping TTL {ttl} (typical for Windows)')]
    return [FingerprintScore('Embedded Linux', 'router', 3, f'Ping TTL {ttl} (typical for routers)')]


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
        if is_specific_os(score.os_name):
            os_totals[score.os_name] = os_totals.get(score.os_name, 0) + score.points
        if score.device_class and score.device_class != 'unknown':
            class_totals[score.device_class] = class_totals.get(score.device_class, 0) + score.points
        if score.reason not in clues:
            clues.append(score.reason)

    if os_totals:
        best_os = max(os_totals, key=os_totals.get)
        best_points = os_totals[best_os]
        if best_points < MIN_OS_POINTS:
            best_os = 'Unknown'
            best_points = 0
    else:
        best_os = 'Unknown'
        best_points = 0

    best_class = max(class_totals, key=class_totals.get) if class_totals else 'unknown'

    if best_points >= 8:
        confidence = 'high'
    elif best_points >= MIN_OS_POINTS:
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
        'tvOS': 'tv',
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
    scores.extend(_score_from_mac(mac_type, vendor, ports=open_ports, hostname=hostname))
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


def fingerprint_from_host_payload(data: Optional[Dict], *, deep_probe: bool = False) -> DeviceFingerprint:
    """Re-score a stored host/observation dict without opening new sockets."""
    data = data or {}
    mdns = None
    if data.get('mdns_services') or data.get('apple_model') or data.get('mdns_name'):
        mdns = {
            'friendly_name': data.get('mdns_name') or data.get('display_name'),
            'hostname': data.get('hostname') or data.get('mdns_hostname'),
            'mdns_services': data.get('mdns_services') or [],
            'mdns_properties': data.get('mdns_properties') or {},
            'apple_model': data.get('apple_model'),
        }
    return fingerprint_device(
        data.get('ip_address') or '',
        hostname=data.get('mdns_name') or data.get('hostname'),
        services=data.get('services') or data.get('discovered_services'),
        mac_type=data.get('mac_type'),
        vendor=data.get('vendor'),
        ping_ttl=data.get('ping_ttl'),
        mdns=mdns,
        deep_probe=deep_probe,
    )
