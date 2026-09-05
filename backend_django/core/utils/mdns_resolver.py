"""
mDNS / Bonjour discovery for local network host identification.

Browses common service types and maps IP addresses to friendly names,
Apple device models, and advertised services.
"""

from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Service types that help identify devices on a LAN
MDNS_SERVICE_TYPES = [
    '_workstation._tcp.local.',
    '_ssh._tcp.local.',
    '_device-info._tcp.local.',
    '_airplay._tcp.local.',
    '_googlecast._tcp.local.',
    '_companion-link._tcp.local.',
    '_apple-mobdev2._tcp.local.',
    '_hap._tcp.local.',
    '_printer._tcp.local.',
    '_smb._tcp.local.',
    '_http._tcp.local.',
    '_raop._tcp.local.',
]


@dataclass
class MdnsRecord:
    ip_address: str
    friendly_name: str
    hostname: str
    services: List[str] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    apple_model: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'friendly_name': self.friendly_name,
            'hostname': self.hostname,
            'mdns_services': self.services,
            'mdns_properties': self.properties,
            'apple_model': self.apple_model,
        }


def _decode_props(raw: Optional[dict]) -> Dict[str, str]:
    props: Dict[str, str] = {}
    if not raw:
        return props
    for key, value in raw.items():
        k = key.decode('utf-8', errors='ignore') if isinstance(key, bytes) else str(key)
        if not k:
            continue
        if value is None:
            continue
        v = value.decode('utf-8', errors='ignore') if isinstance(value, bytes) else str(value)
        props[k] = v
    return props


def _friendly_name_from_service(name: str) -> str:
    """Extract human-readable name from e.g. 'Jason's MacBook Pro._airplay._tcp.local.'"""
    return name.split('._')[0].strip()


def _hostname_from_friendly(friendly_name: str) -> str:
    slug = friendly_name.lower().replace(' ', '-').replace("'", '')
    slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
    return f'{slug}.local' if slug else ''


def _apple_model_label(model_code: Optional[str]) -> Optional[str]:
    """Map Apple internal model codes to friendlier labels when known."""
    if not model_code:
        return None
    # Common Apple model identifiers (subset)
    known = {
        'Mac16,5': 'MacBook Pro (Apple Silicon)',
        'Mac15,3': 'MacBook Air',
        'Mac14,2': 'MacBook Air M2',
        'iPhone15,2': 'iPhone 14 Pro',
        'iPhone14,5': 'iPhone 13',
        'iPad13,1': 'iPad Air',
    }
    return known.get(model_code, model_code)


def discover_mdns_hosts(timeout: float = 5.0) -> Dict[str, MdnsRecord]:
    """
    Browse mDNS services on the local network.

    Returns a dict keyed by IP address with discovered metadata.
    """
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except ImportError:
        logger.warning('zeroconf not installed — mDNS discovery skipped')
        return {}

    records: Dict[str, MdnsRecord] = {}

    class _MdnsListener(ServiceListener):
        def add_service(self, zc, type_, name) -> None:
            try:
                info = zc.get_service_info(type_, name, timeout=1500)
                if not info or not info.addresses:
                    return

                for addr in info.addresses:
                    if len(addr) != 4:
                        continue
                    ip = socket.inet_ntoa(addr)
                    friendly = _friendly_name_from_service(name)
                    props = _decode_props(info.properties)
                    apple_model = _apple_model_label(props.get('model'))

                    if ip not in records:
                        records[ip] = MdnsRecord(
                            ip_address=ip,
                            friendly_name=friendly,
                            hostname=_hostname_from_friendly(friendly) or friendly,
                            apple_model=apple_model,
                        )
                    else:
                        record = records[ip]
                        if len(friendly) > len(record.friendly_name):
                            record.friendly_name = friendly
                            record.hostname = _hostname_from_friendly(friendly) or friendly
                        if apple_model and not record.apple_model:
                            record.apple_model = apple_model

                    record = records[ip]
                    if type_ not in record.services:
                        record.services.append(type_)
                    record.properties.update(props)
                    if apple_model:
                        record.apple_model = apple_model
            except Exception as exc:
                logger.debug('mDNS service parse failed for %s: %s', name, exc)

        def remove_service(self, zc, type_, name) -> None:
            pass

        def update_service(self, zc, type_, name) -> None:
            pass

    zc = None
    try:
        zc = Zeroconf()
        listener = _MdnsListener()
        browsers = [ServiceBrowser(zc, service_type, listener) for service_type in MDNS_SERVICE_TYPES]
        del browsers  # keep references via closure
        time.sleep(timeout)
    except Exception as exc:
        logger.warning('mDNS discovery failed: %s', exc)
        return {}
    finally:
        if zc is not None:
            zc.close()

    return records


def lookup_mdns_for_ip(ip: str, mdns_map: Optional[Dict[str, MdnsRecord]] = None) -> Optional[MdnsRecord]:
    if not mdns_map:
        return None
    return mdns_map.get(ip)
