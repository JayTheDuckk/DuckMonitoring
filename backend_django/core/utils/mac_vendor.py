"""
MAC address vendor lookup using the IEEE OUI database.

Uses mac-vendor-lookup with an optional project-local cache at data/mac_vendors.txt.
Run `python manage.py update_mac_vendors` to refresh from IEEE.

For MACs not in the local database, optional online lookup via maclookup.app.
Locally-administered (random/private) MACs are classified separately — they will
never match a manufacturer OUI.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from django.conf import settings

_lookup = None


def _vendor_cache_path() -> Path:
    return Path(settings.BASE_DIR) / 'data' / 'mac_vendors.txt'


def _research_cache_path() -> Path:
    return Path(settings.BASE_DIR) / 'data' / 'mac_research_cache.json'


def _get_lookup():
    global _lookup
    if _lookup is not None:
        return _lookup

    from mac_vendor_lookup import BaseMacLookup, MacLookup

    cache_path = _vendor_cache_path()
    if cache_path.exists():
        BaseMacLookup.cache_path = str(cache_path)

    _lookup = MacLookup()
    return _lookup


def normalize_mac(mac: str) -> Optional[str]:
    """Normalize a MAC to uppercase XX:XX:XX:XX:XX:XX format."""
    if not mac:
        return None
    cleaned = mac.strip().replace('-', ':').upper()
    parts = cleaned.split(':')
    if len(parts) == 6 and all(len(p) == 2 for p in parts):
        return cleaned
    hex_only = ''.join(c for c in cleaned if c in '0123456789ABCDEF')
    if len(hex_only) == 12:
        return ':'.join(hex_only[i:i + 2] for i in range(0, 12, 2))
    return None


def is_multicast_mac(mac: str) -> bool:
    normalized = normalize_mac(mac)
    if not normalized:
        return False
    first_octet = int(normalized.split(':')[0], 16)
    return bool(first_octet & 0x01)


def is_locally_administered_mac(mac: str) -> bool:
    """True for privacy/random MACs (common on phones, laptops, IoT)."""
    normalized = normalize_mac(mac)
    if not normalized:
        return False
    first_octet = int(normalized.split(':')[0], 16)
    return bool(first_octet & 0x02)


def _load_research_cache() -> Dict[str, Any]:
    path = _research_cache_path()
    if not path.exists():
        return {}
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_research_cache(cache: Dict[str, Any]) -> None:
    path = _research_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)


def _lookup_vendor_online(mac: str) -> Optional[str]:
    """Fallback online OUI lookup (cached). Disabled unless MAC_VENDOR_ONLINE_LOOKUP=true."""
    enabled = os.environ.get('MAC_VENDOR_ONLINE_LOOKUP', 'true').lower() == 'true'
    if not enabled:
        return None

    normalized = normalize_mac(mac)
    if not normalized:
        return None

    cache = _load_research_cache()
    if normalized in cache:
        entry = cache[normalized]
        return entry.get('vendor') or None

    try:
        response = requests.get(
            f'https://api.maclookup.app/v2/macs/{normalized}',
            timeout=5,
            headers={'User-Agent': 'DuckMonitoring/2.0'},
        )
        response.raise_for_status()
        data = response.json()
        vendor = None
        if data.get('found') and data.get('company'):
            vendor = data['company'].strip()
        cache[normalized] = {
            'vendor': vendor,
            'is_private': data.get('isRand') or data.get('isPrivate'),
            'source': 'maclookup.app',
        }
        _save_research_cache(cache)
        return vendor
    except Exception:
        return None


def _infer_device_hint(
    mac_type: str,
    hostname: Optional[str] = None,
    suggested_type: Optional[str] = None,
    services: Optional[list] = None,
) -> str:
    hostname = (hostname or '').lower()

    if mac_type == 'private':
        if any(k in hostname for k in ('iphone', 'ipad', 'ipod', 'apple')):
            return 'Likely Apple device using a privacy (randomized) Wi‑Fi MAC'
        if 'android' in hostname:
            return 'Likely Android device using a privacy (randomized) Wi‑Fi MAC'
        if any(k in hostname for k in ('macbook', 'imac', 'mac-', 'mac.')):
            return 'Likely Mac using a privacy (randomized) Wi‑Fi MAC'
        if any(k in hostname for k in ('windows', 'desktop', 'laptop', 'pc-')):
            return 'Likely Windows PC using a privacy (randomized) Wi‑Fi MAC'
        if suggested_type and suggested_type != 'unknown':
            return (
                f'Private/random MAC — device behaves like a {suggested_type.replace("_", " ")} '
                '(common on phones, laptops, and modern OS privacy settings)'
            )
        return (
            'Private/random MAC — not assigned to a manufacturer. '
            'Common on phones, laptops, and guest devices with privacy features enabled.'
        )

    if mac_type == 'unknown':
        hints = []
        if hostname:
            hints.append(f'Hostname: {hostname}')
        if suggested_type and suggested_type != 'unknown':
            hints.append(f'Device type hint: {suggested_type.replace("_", " ")}')
        if services:
            port_list = ', '.join(
                f"{s.get('port')}/{s.get('service', '?')}" for s in services[:4]
            )
            hints.append(f'Open ports: {port_list}')
        if hints:
            return 'Unknown manufacturer OUI. Clues: ' + '; '.join(hints)
        return 'Unknown manufacturer OUI — try hostname, open ports, or importing with an agent for more detail.'

    return ''


def research_mac(
    mac: str,
    hostname: Optional[str] = None,
    suggested_type: Optional[str] = None,
    services: Optional[list] = None,
    use_online: bool = True,
) -> Dict[str, Any]:
    """
    Classify a MAC and resolve vendor information with fallbacks.

    Returns:
        vendor: display string (manufacturer name or classification label)
        mac_type: manufacturer | private | multicast | unknown
        vendor_source: ieee_local | ieee_online | classified | none
        device_hint: human-readable explanation / clues
    """
    normalized = normalize_mac(mac)
    if not normalized:
        return {
            'vendor': None,
            'mac_type': 'unknown',
            'vendor_source': 'none',
            'device_hint': 'Invalid MAC address format',
        }

    if is_multicast_mac(normalized):
        return {
            'vendor': 'Multicast',
            'mac_type': 'multicast',
            'vendor_source': 'classified',
            'device_hint': 'Multicast address — not a physical device NIC',
        }

    if is_locally_administered_mac(normalized):
        return {
            'vendor': 'Private/Random MAC',
            'mac_type': 'private',
            'vendor_source': 'classified',
            'device_hint': _infer_device_hint('private', hostname, suggested_type, services),
        }

    vendor = lookup_vendor(normalized)
    source = 'ieee_local' if vendor else 'none'

    if not vendor and use_online:
        vendor = _lookup_vendor_online(normalized)
        if vendor:
            source = 'ieee_online'

    mac_type = 'manufacturer' if vendor else 'unknown'
    display_vendor = vendor
    if not display_vendor:
        display_vendor = 'Unknown Manufacturer'

    return {
        'vendor': display_vendor,
        'mac_type': mac_type,
        'vendor_source': source,
        'device_hint': _infer_device_hint(mac_type, hostname, suggested_type, services),
    }


def lookup_vendor(mac: str) -> Optional[str]:
    """Return the vendor/manufacturer name for a globally-assigned MAC, or None."""
    normalized = normalize_mac(mac)
    if not normalized or is_locally_administered_mac(normalized):
        return None

    try:
        from mac_vendor_lookup import VendorNotFoundError

        vendor = _get_lookup().lookup(normalized)
        return vendor.strip() if vendor else None
    except VendorNotFoundError:
        return None
    except Exception:
        return None


def update_vendor_database() -> int:
    """
    Download the latest IEEE OUI list into data/mac_vendors.txt.
    Returns the number of vendor prefixes loaded.
    """
    from mac_vendor_lookup import BaseMacLookup, MacLookup

    global _lookup

    cache_path = _vendor_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    BaseMacLookup.cache_path = str(cache_path)

    lookup = MacLookup()
    lookup.update_vendors()

    _lookup = lookup
    if cache_path.exists():
        with cache_path.open('r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())
    return 0
