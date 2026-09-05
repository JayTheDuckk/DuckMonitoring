"""Turn discovery observations into watched Hosts."""

from __future__ import annotations

import ipaddress

from django.utils import timezone

from inventory.models import (
    DeviceObservation, Host, LanWatchSettings, apply_host_identity,
    observation_as_host, observation_matches_network,
)

HOST_DOWN_CONDITION = {"field": "status", "operator": "equals", "value": "critical"}


def usable_watch_ip(ip):
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except (ValueError, TypeError):
        return False
    return not (addr.is_loopback or addr.is_multicast or addr.is_unspecified or addr.is_reserved)


def host_info_from_observation(observation, lan_cache=None):
    from inventory.discovery import apply_lan_identity_to_host, load_lan_identity_cache

    host_info = observation_as_host(observation, seen_this_scan=True)
    apply_lan_identity_to_host(host_info, lan_cache if lan_cache is not None else load_lan_identity_cache())
    return host_info


def enrich_host_api_dict(data, observation=None, lan_cache=None):
    """Fill empty Host API fields from the latest observation and host ARP/mDNS cache."""
    if not data:
        return data
    from inventory.discovery import apply_lan_identity_to_host, load_lan_identity_cache

    if observation is not None:
        known = observation_as_host(observation, seen_this_scan=False)
        for key in (
            'mac_address', 'hostname', 'mdns_name', 'apple_model',
            'vendor', 'os_guess', 'device_class', 'identification_clues',
        ):
            if not data.get(key) and known.get(key):
                data[key] = known[key]
        if data.get('confidence') in (None, '') and known.get('confidence') is not None:
            data['confidence'] = known['confidence']
        if not data.get('last_seen') and known.get('last_seen'):
            data['last_seen'] = known['last_seen']
        if not data.get('services') and known.get('services'):
            data['services'] = known['services']
        payload = observation.last_payload or {}
        if data.get('latency_ms') in (None, '') and (payload.get('latency_ms') or payload.get('latency')):
            data['latency_ms'] = payload.get('latency_ms') or payload.get('latency')
        if data.get('ping_ttl') in (None, '') and payload.get('ping_ttl') is not None:
            data['ping_ttl'] = payload.get('ping_ttl')
        if observation.sighting_count:
            data['sighting_count'] = observation.sighting_count
    apply_lan_identity_to_host(data, lan_cache if lan_cache is not None else load_lan_identity_cache())
    _stamp_mac_type(data)
    _refine_os_guess(data)
    return data


def _refine_os_guess(data):
    from core.utils.device_fingerprint import fingerprint_from_host_payload, is_specific_os

    result = fingerprint_from_host_payload(data)
    if is_specific_os(result.os_guess):
        data['os_guess'] = result.os_guess
        if result.confidence and data.get('confidence') in (None, ''):
            data['confidence'] = result.confidence
    elif not is_specific_os(data.get('os_guess')):
        data['os_guess'] = None


def _stamp_mac_type(data):
    mac = data.get('mac_address')
    if not mac:
        return
    if data.get('mac_type'):
        return
    try:
        from core.utils.mac_vendor import research_mac
        research = research_mac(mac, use_online=False)
    except Exception:
        return
    if research.get('mac_type'):
        data['mac_type'] = research['mac_type']
    if not data.get('vendor') and research.get('vendor'):
        data['vendor'] = research['vendor']


def ensure_host_down_rule(host):
    from alerts.models import AlertRule

    if AlertRule.objects.filter(host=host, condition_type='host_down').exists():
        return False
    AlertRule.objects.create(
        name=f"{host.hostname} down",
        condition_type='host_down',
        condition=HOST_DOWN_CONDITION,
        severity='critical',
        host=host,
    )
    return True


def import_or_update_host(host_info, now=None, *, add_services=True):
    """
    Create or update a watched Host from a discovery payload.

    Returns (host, created, alerts_created, service_checks_created).
    """
    from inventory.discovery import apply_lan_identity_to_host
    from monitoring.models import ServiceCheckConfig

    now = now or timezone.now()
    apply_lan_identity_to_host(host_info)
    ip = host_info.get('ip_address')
    if not usable_watch_ip(ip):
        return None, False, 0, 0

    hostname = host_info.get('mdns_name') or host_info.get('hostname') or ip
    host = Host.objects.filter(ip_address=ip).first()
    created = host is None
    if created:
        host = Host(ip_address=ip, hostname=hostname, status='up')
    else:
        host.status = host.status or 'up'

    apply_host_identity(host, host_info, now=now, created=created)
    host.save()

    alerts_created = 0
    service_checks_created = 0
    if created:
        ServiceCheckConfig.objects.create(
            host=host,
            check_type='ping',
            check_name='Ping Check',
            interval=60,
            enabled=True,
            parameters={'count': 3},
        )
        if ensure_host_down_rule(host):
            alerts_created = 1

    if add_services:
        for service in host_info.get('services') or []:
            svc_name = service.get('service', 'unknown')
            svc_port = service.get('port')
            if not svc_port:
                continue
            if ServiceCheckConfig.objects.filter(
                host=host, check_type=svc_name, parameters__port=svc_port
            ).exists():
                continue
            ServiceCheckConfig.objects.create(
                host=host,
                check_type=svc_name,
                check_name=f"{svc_name.upper()} on port {svc_port}",
                interval=60,
                enabled=True,
                parameters={'port': svc_port},
            )
            service_checks_created += 1

    return host, created, alerts_created, service_checks_created


def sync_hosts_from_observations(*, create_missing=False, network=None):
    """Update existing hosts from observations; optionally add unseen IPs as ungrouped."""
    from inventory.discovery import load_lan_identity_cache

    lan_cache = load_lan_identity_cache()
    added = 0
    now = timezone.now()
    for observation in DeviceObservation.objects.all():
        if not usable_watch_ip(observation.ip_address):
            continue
        if network and not observation_matches_network(observation, network):
            continue
        existing = Host.objects.filter(ip_address=observation.ip_address).exists()
        if not existing and not create_missing:
            continue
        host_info = host_info_from_observation(observation, lan_cache=lan_cache)
        host, created, _, _ = import_or_update_host(
            host_info,
            now=now,
            add_services=not existing,
        )
        if created:
            added += 1
    return added


def watch_status():
    settings = LanWatchSettings.load()
    return {
        'auto_add_hosts': settings.auto_add_hosts,
        'network': settings.network or '',
        'updated_at': settings.updated_at.isoformat() if settings.updated_at else None,
    }
