"""
mDNS / Bonjour discovery for local network host identification.

Browses common service types and maps IP addresses to friendly names,
Apple device models, and advertised services.
"""

from __future__ import annotations

import logging
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from core.utils.mac_vendor import normalize_mac as normalize_mac_address

logger = logging.getLogger(__name__)

LOOPBACK = '127.0.0.1'

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
    '_amzn-wplay._tcp.local.',
    '_spotify-connect._tcp.local.',
    '_androidtvremote2._tcp.local.',
]


@dataclass
class MdnsRecord:
    ip_address: str
    friendly_name: str
    hostname: str
    services: List[str] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    apple_model: Optional[str] = None
    mac_address: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'friendly_name': self.friendly_name,
            'hostname': self.hostname,
            'mdns_services': self.services,
            'mdns_properties': self.properties,
            'apple_model': self.apple_model,
        }


@dataclass
class MdnsDiscoveryResult:
    by_ip: Dict[str, MdnsRecord] = field(default_factory=dict)
    by_mac: Dict[str, MdnsRecord] = field(default_factory=dict)

    def device_count(self) -> int:
        seen: Set[int] = set()
        for record in list(self.by_ip.values()) + list(self.by_mac.values()):
            seen.add(id(record))
        return len(seen)


def normalize_mac(mac: str) -> str:
    return mac.replace('-', ':').upper()


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


_DUPLICATE_SUFFIX = re.compile(r'\s+\(\d+\)$')


def _friendly_name_rank(name: str) -> tuple:
    """Lower rank = better display name."""
    return (bool(_DUPLICATE_SUFFIX.search(name)), len(name))


def _pick_better_friendly_name(existing: str, incoming: str) -> str:
    """Prefer names without Apple's duplicate suffix, e.g. '(2)'."""
    if _friendly_name_rank(incoming) < _friendly_name_rank(existing):
        return incoming
    if _friendly_name_rank(existing) < _friendly_name_rank(incoming):
        return existing
    return incoming if len(incoming) > len(existing) else existing


def _friendly_name_from_service(name: str) -> str:
    """Extract human-readable name from e.g. 'Jason's MacBook Pro._airplay._tcp.local.'"""
    return name.split('._')[0].strip()


def _mac_from_props(props: Dict[str, str]) -> Optional[str]:
    for key in ('deviceid', 'rpBA', 'mac', 'hwaddr', 'c'):
        val = props.get(key)
        if not val:
            continue
        val = normalize_mac(val.replace('.', ':'))
        if re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', val):
            return val
    return None


def _resolve_friendly_name(service_name: str, props: Dict[str, str], service_type: str) -> str:
    """Pick the best human-readable label from mDNS metadata."""
    if props.get('fn'):
        return props['fn'].strip()
    if props.get('n'):
        return props['n'].strip()

    raw = _friendly_name_from_service(service_name)

    if '@' in raw:
        raw = raw.split('@', 1)[1].strip()

    if 'googlecast' in service_type:
        if props.get('md'):
            return props['md'].strip()
        # Strip trailing device-id hash from Cast service names
        if re.match(r'^.+-[a-f0-9]{32}$', raw):
            base = raw.rsplit('-', 1)[0]
            return base.replace('-', ' ').strip()

    return raw


def _hostname_from_friendly(friendly_name: str) -> str:
    slug = friendly_name.lower().replace(' ', '-').replace("'", '')
    slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
    return f'{slug}.local' if slug else ''


def _apple_model_label(model_code: Optional[str]) -> Optional[str]:
    """Map Apple internal model codes to friendlier labels when known."""
    if not model_code:
        return None
    known = {
        'Mac16,5': 'MacBook Pro (Apple Silicon)',
        'Mac15,3': 'MacBook Air',
        'Mac14,2': 'MacBook Air M2',
        'iPhone15,2': 'iPhone 14 Pro',
        'iPhone14,5': 'iPhone 13',
        'iPad13,1': 'iPad Air',
    }
    return known.get(model_code, model_code)


def _merge_record(existing: MdnsRecord, incoming: MdnsRecord) -> None:
    better_name = _pick_better_friendly_name(existing.friendly_name, incoming.friendly_name)
    if better_name != existing.friendly_name:
        existing.friendly_name = better_name
        existing.hostname = _hostname_from_friendly(better_name) or better_name
    for svc in incoming.services:
        if svc not in existing.services:
            existing.services.append(svc)
    existing.properties.update(incoming.properties)
    if incoming.apple_model and not existing.apple_model:
        existing.apple_model = incoming.apple_model
    if incoming.mac_address and not existing.mac_address:
        existing.mac_address = incoming.mac_address
    if existing.ip_address == LOOPBACK and incoming.ip_address != LOOPBACK:
        existing.ip_address = incoming.ip_address


def _store_record(result: MdnsDiscoveryResult, record: MdnsRecord) -> None:
    if record.mac_address:
        mac_key = normalize_mac(record.mac_address)
        if mac_key in result.by_mac:
            _merge_record(result.by_mac[mac_key], record)
        else:
            result.by_mac[mac_key] = record

    if record.ip_address and record.ip_address != LOOPBACK:
        if record.ip_address in result.by_ip:
            _merge_record(result.by_ip[record.ip_address], record)
        else:
            result.by_ip[record.ip_address] = record


def discover_mdns_hosts(timeout: float = 8.0) -> MdnsDiscoveryResult:
    """
    Browse mDNS services on the local network.

    Returns IP and MAC keyed indexes of discovered metadata.
    """
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except ImportError:
        logger.warning('zeroconf not installed — mDNS discovery skipped')
        return MdnsDiscoveryResult()

    result = MdnsDiscoveryResult()

    class _MdnsListener(ServiceListener):
        def add_service(self, zc, type_, name) -> None:
            try:
                info = zc.get_service_info(type_, name, timeout=2000)
                if not info or not info.addresses:
                    return

                props = _decode_props(info.properties)
                friendly = _resolve_friendly_name(name, props, type_)
                apple_model = _apple_model_label(props.get('model') or props.get('am'))
                mac = _mac_from_props(props)

                for addr in info.addresses:
                    if len(addr) != 4:
                        continue
                    ip = socket.inet_ntoa(addr)
                    if ip == LOOPBACK and not mac:
                        continue

                    record = MdnsRecord(
                        ip_address=ip if ip != LOOPBACK else '',
                        friendly_name=friendly,
                        hostname=_hostname_from_friendly(friendly) or friendly,
                        apple_model=apple_model,
                        mac_address=mac,
                    )
                    if type_ not in record.services:
                        record.services.append(type_)
                    record.properties.update(props)
                    if apple_model:
                        record.apple_model = apple_model

                    _store_record(result, record)
            except Exception as exc:
                logger.debug('mDNS service parse failed for %s: %s', name, exc)

        def remove_service(self, zc, type_, name) -> None:
            pass

        def update_service(self, zc, type_, name) -> None:
            pass

    zc = None
    browsers = []
    try:
        zc = Zeroconf()
        listener = _MdnsListener()
        browsers = [
            ServiceBrowser(zc, service_type, listener)
            for service_type in MDNS_SERVICE_TYPES
        ]
        time.sleep(timeout)
    except Exception as exc:
        logger.warning('mDNS discovery failed: %s', exc)
        return MdnsDiscoveryResult()
    finally:
        browsers.clear()
        if zc is not None:
            zc.close()

    return result


def _service_matches(services: List[str], marker: str) -> bool:
    return any(marker in service for service in services)


def _brand_from_model(model: str) -> Optional[str]:
    """Extract a likely brand from a model string like 'Philips 4K A1'."""
    if not model:
        return None
    first = model.strip().split()[0]
    if len(first) >= 2 and first.replace('-', '').isalpha():
        return first[0].upper() + first[1:] if len(first) > 1 else first.upper()
    return None


def mac_from_mdns_record(record: MdnsRecord) -> Optional[str]:
    """Return a MAC advertised in mDNS metadata, if any."""
    if record.mac_address:
        return normalize_mac_address(record.mac_address)
    return _mac_from_props(record.properties)


def should_apply_mdns_vendor(
    mac_type: Optional[str],
    vendor: Optional[str],
    vendor_source: Optional[str] = None,
) -> bool:
    if vendor_source == 'mdns_guess':
        return False
    if mac_type in ('private', 'unknown', None):
        return True
    return vendor in (None, 'Unknown Manufacturer', 'Private/Random MAC')


def guess_vendor_from_mdns(record: MdnsRecord) -> Optional[Dict[str, str]]:
    """Infer manufacturer from mDNS services and metadata."""
    services = record.services
    props = record.properties
    friendly = (record.friendly_name or '').lower()

    if _service_matches(services, '_amzn-wplay') or 'firetv' in friendly or 'fire tv' in friendly:
        return {
            'vendor': 'Amazon',
            'vendor_source': 'mdns_guess',
            'device_hint': f"Vendor inferred from mDNS ({record.friendly_name or 'Amazon device'})",
        }

    if record.apple_model or _service_matches(services, '_companion-link') or _service_matches(services, '_apple-mobdev'):
        return {
            'vendor': 'Apple Inc.',
            'vendor_source': 'mdns_guess',
            'device_hint': f"Vendor inferred from mDNS ({record.friendly_name or 'Apple device'})",
        }

    if any(token in friendly for token in ('macbook', 'imac', 'mac mini', 'mac studio', 'iphone', 'ipad')):
        return {
            'vendor': 'Apple Inc.',
            'vendor_source': 'mdns_guess',
            'device_hint': f"Vendor inferred from mDNS ({record.friendly_name})",
        }

    if _service_matches(services, '_googlecast'):
        model = props.get('md') or record.friendly_name
        brand = _brand_from_model(model or '')
        vendor = brand or 'Google (Chromecast)'
        detail = model or record.friendly_name or 'Chromecast device'
        return {
            'vendor': vendor,
            'vendor_source': 'mdns_guess',
            'device_hint': f'Vendor inferred from mDNS Cast advertisement ({detail})',
        }

    if _service_matches(services, '_androidtvremote2'):
        return {
            'vendor': 'Google',
            'vendor_source': 'mdns_guess',
            'device_hint': f"Vendor inferred from mDNS ({record.friendly_name or 'Android TV'})",
        }

    if _service_matches(services, '_airplay') or _service_matches(services, '_raop'):
        model = props.get('md') or props.get('model')
        brand = _brand_from_model(model or '')
        if brand and brand.lower() != 'apple':
            return {
                'vendor': brand,
                'vendor_source': 'mdns_guess',
                'device_hint': f'Vendor inferred from mDNS AirPlay device ({model or record.friendly_name})',
            }
        if record.apple_model or _service_matches(services, '_device-info'):
            return {
                'vendor': 'Apple Inc.',
                'vendor_source': 'mdns_guess',
                'device_hint': f"Vendor inferred from mDNS ({record.friendly_name or 'Apple device'})",
            }

    return None


def enrich_vendor_from_mdns(host_info: Dict, mdns_record: Optional[MdnsRecord]) -> None:
    """Fill vendor from mDNS when MAC OUI lookup is inconclusive."""
    if not mdns_record:
        return
    if not should_apply_mdns_vendor(
        host_info.get('mac_type'),
        host_info.get('vendor'),
        host_info.get('vendor_source'),
    ):
        return

    guess = guess_vendor_from_mdns(mdns_record)
    if not guess:
        return

    host_info['vendor'] = guess['vendor']
    host_info['vendor_source'] = guess['vendor_source']
    hint = guess['device_hint']
    if host_info.get('device_hint'):
        host_info['device_hint'] = f"{hint} · {host_info['device_hint']}"
    else:
        host_info['device_hint'] = hint


def lookup_mdns_for_ip(
    ip: str,
    mdns_result: Optional[MdnsDiscoveryResult] = None,
    known_mac: Optional[str] = None,
) -> Optional[MdnsRecord]:
    if not mdns_result:
        return None

    record = mdns_result.by_ip.get(ip)
    if record:
        return record

    if known_mac:
        return mdns_result.by_mac.get(normalize_mac(known_mac))

    return None
