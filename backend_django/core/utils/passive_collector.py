"""
Periodic mDNS / SSDP / ARP collection for the DeviceObservation cache.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from core.utils.device_fingerprint import fingerprint_device
from core.utils.mac_vendor import parse_mac_from_text, research_mac
from core.utils.mdns_resolver import (
    MdnsDiscoveryResult,
    MdnsRecord,
    discover_mdns_hosts,
    guess_vendor_from_mdns,
    mac_from_mdns_record,
)
from core.utils.ssdp_resolver import SsdpRecord, discover_ssdp_hosts, guess_vendor_from_ssdp

logger = logging.getLogger(__name__)

_WEAK_VENDORS = {'', 'Private/Random MAC', 'Unknown Manufacturer', 'Multicast'}
_IP_RE = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')


def collect_passive_hosts(network: str, listen_seconds: float = 8) -> List[dict]:
    """
    Browse mDNS, listen for SSDP, and read ARP/neighbor tables.

    Returns host_info dicts compatible with upsert_observation.
    Never pings. One failing source does not fail the collect.
    """
    mdns_result = MdnsDiscoveryResult()
    ssdp_map: Dict[str, SsdpRecord] = {}
    arp_hosts: Dict[str, str] = {}

    def _run_mdns() -> None:
        nonlocal mdns_result
        try:
            mdns_result = discover_mdns_hosts(timeout=listen_seconds) or MdnsDiscoveryResult()
        except Exception as exc:
            logger.warning('Passive mDNS collection failed: %s', exc)

    def _run_ssdp() -> None:
        nonlocal ssdp_map
        try:
            ssdp_map = discover_ssdp_hosts(timeout=listen_seconds) or {}
        except Exception as exc:
            logger.warning('Passive SSDP collection failed: %s', exc)

    def _run_arp() -> None:
        nonlocal arp_hosts
        try:
            arp_hosts = _read_arp_and_neighbors()
        except Exception as exc:
            logger.warning('Passive ARP collection failed: %s', exc)

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(_run_mdns), pool.submit(_run_ssdp), pool.submit(_run_arp)]
            for future in futures:
                future.result()
    except Exception as exc:
        logger.warning('Passive collector network unavailable: %s', exc)
        return []

    hosts: Dict[str, dict] = {}
    for ip, mac in arp_hosts.items():
        if _ip_in_network(ip, network):
            _merge_host(hosts, _host_from_arp(ip, mac))

    for ip, record in ssdp_map.items():
        if _ip_in_network(ip, network):
            _merge_host(hosts, _host_from_ssdp(record))

    for ip, record in mdns_result.by_ip.items():
        if _ip_in_network(ip, network):
            _merge_host(hosts, _host_from_mdns(record))

    for host_info in hosts.values():
        mdns_record = mdns_result.by_ip.get(host_info['ip_address'])
        _apply_cheap_fingerprint(host_info, mdns_record)

    if not hosts:
        try:
            import zeroconf  # noqa: F401
        except ImportError:
            logger.warning('zeroconf not installed — passive collector skipped')
        if os.path.exists('/.dockerenv'):
            logger.warning(
                'Passive collector found no hosts; multicast/network may be unavailable (Docker Desktop)'
            )

    return list(hosts.values())


def _read_arp_and_neighbors() -> Dict[str, str]:
    from inventory.discovery import get_active_hosts_from_arp

    hosts = dict(get_active_hosts_from_arp() or {})
    hosts.update(_read_neighbor_table())
    return hosts


def _read_neighbor_table() -> Dict[str, str]:
    hosts: Dict[str, str] = {}
    for cmd in (['ip', 'neighbor', 'show'], ['ip', 'neigh']):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            continue
        if not result.stdout:
            continue
        for line in result.stdout.splitlines():
            if 'FAILED' in line or 'incomplete' in line.lower():
                continue
            ip_match = _IP_RE.search(line)
            mac = parse_mac_from_text(line)
            if not ip_match or not mac:
                continue
            ip = ip_match.group(0)
            if ip != '0.0.0.0' and not ip.endswith('.255'):
                hosts[ip] = mac
        if hosts:
            break
    return hosts


def _ip_in_network(ip: str, network: str) -> bool:
    if not ip or not network:
        return False
    try:
        addr = ipaddress.ip_address(ip)
        if addr.is_loopback or addr.is_unspecified:
            return False
        if '/' in network:
            return addr in ipaddress.ip_network(network, strict=False)
        if '-' in network:
            from inventory.discovery import parse_network_range
            return str(addr) in set(parse_network_range(network))
        return str(addr) == network
    except (ValueError, TypeError):
        return False


def _host_from_mdns(record: MdnsRecord) -> dict:
    host_info = {
        'ip_address': record.ip_address,
        'hostname': record.hostname or record.friendly_name,
        'mdns_name': record.friendly_name,
        'apple_model': record.apple_model,
        'mac_address': mac_from_mdns_record(record),
        'identification_clues': ['passive_mdns'],
    }
    guess = guess_vendor_from_mdns(record)
    if guess:
        host_info['vendor'] = guess['vendor']
        host_info['vendor_source'] = guess['vendor_source']
    elif host_info.get('mac_address'):
        host_info.update(_cheap_mac_vendor(host_info['mac_address']))
    return host_info


def _host_from_ssdp(record: SsdpRecord) -> dict:
    host_info = {
        'ip_address': record.ip_address,
        'hostname': record.friendly_name,
        'identification_clues': ['passive_ssdp'],
    }
    vendor = guess_vendor_from_ssdp(record)
    if vendor:
        host_info['vendor'] = vendor
        host_info['vendor_source'] = 'ssdp_guess'
    return host_info


def _host_from_arp(ip: str, mac: str) -> dict:
    host_info = {
        'ip_address': ip,
        'mac_address': mac,
        'identification_clues': ['passive_arp'],
    }
    host_info.update(_cheap_mac_vendor(mac))
    return host_info


def _cheap_mac_vendor(mac: Optional[str]) -> dict:
    if not mac:
        return {}
    try:
        research = research_mac(mac, use_online=False)
    except Exception:
        return {}
    extra = {}
    vendor = research.get('vendor')
    if vendor and vendor not in _WEAK_VENDORS:
        extra['vendor'] = vendor
        extra['vendor_source'] = research.get('vendor_source')
    if research.get('mac_type'):
        extra['mac_type'] = research['mac_type']
    return extra


def _merge_host(hosts: Dict[str, dict], incoming: dict) -> None:
    ip = incoming.get('ip_address')
    if not ip:
        return
    existing = hosts.get(ip)
    if existing is None:
        hosts[ip] = incoming
        return

    for key in (
        'hostname', 'mdns_name', 'apple_model', 'mac_address',
        'device_class', 'confidence', 'mac_type',
    ):
        if incoming.get(key) and not existing.get(key):
            existing[key] = incoming[key]

    incoming_vendor = incoming.get('vendor')
    if incoming_vendor and (
        not existing.get('vendor') or existing.get('vendor') in _WEAK_VENDORS
    ):
        existing['vendor'] = incoming_vendor
        if incoming.get('vendor_source'):
            existing['vendor_source'] = incoming['vendor_source']

    clues = list(existing.get('identification_clues') or [])
    for clue in incoming.get('identification_clues') or []:
        if clue not in clues:
            clues.append(clue)
    existing['identification_clues'] = clues


def _apply_cheap_fingerprint(host_info: dict, mdns_record: Optional[MdnsRecord] = None) -> None:
    try:
        fingerprint = fingerprint_device(
            host_info['ip_address'],
            hostname=host_info.get('mdns_name') or host_info.get('hostname'),
            mac_type=host_info.get('mac_type'),
            vendor=host_info.get('vendor'),
            mdns=mdns_record.to_dict() if mdns_record else None,
            deep_probe=False,
        )
    except Exception:
        return

    if fingerprint.device_class and fingerprint.device_class != 'unknown':
        host_info.setdefault('device_class', fingerprint.device_class)
        if fingerprint.confidence:
            host_info.setdefault('confidence', fingerprint.confidence)
        clues = list(host_info.get('identification_clues') or [])
        for clue in fingerprint.identification_clues:
            if clue and clue not in clues and 'Insufficient' not in clue:
                clues.append(clue)
        host_info['identification_clues'] = clues
