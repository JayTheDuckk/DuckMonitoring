"""
Additional probing for hosts that respond to ping but expose little else.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

# Extra TCP ports common on phones, IoT, printers, and cameras
EXTENDED_QUIET_PORTS = {
    139: 'NETBIOS',
    445: 'SMB',
    515: 'LPD',
    554: 'RTSP',
    631: 'IPP',
    1883: 'MQTT',
    1900: 'SSDP',
    3000: 'HTTP_DEV',
    5000: 'UPNP',
    5353: 'MDNS',
    5355: 'LLMNR',
    7000: 'AFS3',
    7100: 'HTTP_ALT2',
    8081: 'HTTP_ALT3',
    8443: 'HTTPS_ALT',
    8554: 'RTSP_ALT',
    8888: 'HTTP_CAM',
    9090: 'HTTP_ALT4',
    9999: 'HTTP_CAM2',
    10001: 'CAMERA',
    32400: 'PLEX',
    3689: 'DAAP',
    49152: 'DYNAMIC',
    62078: 'APPLE_SYNC',
}


def is_sparse_host(host_info: Dict) -> bool:
    """True when we found the host but have little identifying data."""
    has_mdns = bool(host_info.get('mdns_name'))
    has_services = bool(host_info.get('services'))
    has_hostname = bool(host_info.get('hostname'))
    has_vendor = host_info.get('vendor_source') in ('ieee_local', 'ieee_online', 'mdns_guess')
    return not has_mdns and not has_services and not has_hostname and not has_vendor


def deep_probe_quiet_host(ip: str, check_port: Callable[[str, int, float], bool], timeout: float = 0.6) -> Dict:
    """
    Run a slower, wider port scan for ping-only hosts.
    Returns extra services and discovery signal tags.
    """
    services: List[Dict] = []
    signals: List[str] = ['ping_only_host']

    for port, name in EXTENDED_QUIET_PORTS.items():
        if check_port(ip, port, timeout):
            services.append({'port': port, 'service': name, 'state': 'open'})
            signals.append(f'tcp_{port}_open')

    return {
        'services': services,
        'discovery_signals': signals,
    }


STRONGER_DEVICE_CLASSES = frozenset({
    'router', 'server', 'printer', 'tv', 'network_device',
})


def describe_quiet_host(host_info: Dict) -> str:
    """Human-readable summary of what we could and could not learn."""
    ttl = host_info.get('ping_ttl')
    latency = host_info.get('latency_ms')
    mac_type = host_info.get('mac_type')
    signals = host_info.get('discovery_signals') or []

    parts = []
    if mac_type == 'private':
        parts.append('Uses a privacy/random MAC')
    if ttl is not None:
        if ttl <= 64:
            parts.append(f'Responds to ping (TTL {ttl}, typical of Linux/macOS/iOS/Android)')
        elif ttl <= 128:
            parts.append(f'Responds to ping (TTL {ttl}, typical of Windows)')
        else:
            parts.append(f'Responds to ping (TTL {ttl})')
    if latency and latency > 150:
        parts.append(f'High latency ({latency:.0f} ms) — may be sleeping or on weak Wi‑Fi')

    if not host_info.get('services') and 'no_inbound_services' not in signals:
        parts.append('No inbound TCP services detected (common on phones with firewalls enabled)')

    if not host_info.get('mdns_name'):
        parts.append('No mDNS/Bonjour advertisement during scan window')

    if mac_type == 'private' or is_sparse_host(host_info):
        parts.append('Phones often hide from LAN scans; this is expected, not a failed server')

    if not parts:
        return 'Limited discovery signals — device may only allow outbound connections'
    return ' · '.join(parts)


def _has_advertised_name(host_info: Dict) -> bool:
    hostname = (host_info.get('hostname') or '').strip()
    mdns_name = (host_info.get('mdns_name') or '').strip()
    return bool(hostname or mdns_name)


def should_mark_privacy_device(host_info: Dict) -> bool:
    """True when an unnamed private or sparse host should not look like a server."""
    if _has_advertised_name(host_info):
        return False
    if host_info.get('device_class') in STRONGER_DEVICE_CLASSES:
        return False
    return host_info.get('mac_type') == 'private' or is_sparse_host(host_info)


def stamp_privacy_device(host_info: Dict) -> Dict:
    """
    Mark unnamed private-MAC / sparse hosts as privacy devices.

    Phones hide from scans; this is expected, not a down server.
    Stronger classes (router/server/printer/tv) already won are left alone.
    """
    if not should_mark_privacy_device(host_info):
        return host_info

    reason = describe_quiet_host(host_info)
    host_info['device_class'] = 'privacy_device'
    host_info['privacy_reason'] = reason
    host_info['suggested_type'] = 'privacy_device'
    clues = list(host_info.get('identification_clues') or [])
    if reason and reason not in clues:
        clues.insert(0, reason)
    host_info['identification_clues'] = clues
    return host_info
