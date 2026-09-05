#!/usr/bin/env python3
"""
Publish the host ARP table for Docker LAN discovery.

Docker Desktop on macOS cannot see LAN MAC addresses from the API
container. This helper reads the host ARP table (and optional reverse
DNS / mDNS names) and writes data/lan/identity.json for the scanner.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

IP_RE = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
MAC_RE = re.compile(r'([0-9A-Fa-f]{1,2}[:-]){5}([0-9A-Fa-f]{1,2})')


def default_output_path() -> Path:
    raw = (os.environ.get('LAN_IDENTITY_PATH') or '').strip()
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[1] / 'data' / 'lan' / 'identity.json'


def normalize_mac(raw: str) -> str | None:
    if not raw:
        return None
    parts = raw.replace('-', ':').split(':')
    if len(parts) != 6:
        return None
    try:
        return ':'.join(f'{int(part, 16):02X}' for part in parts)
    except ValueError:
        return None


def usable_ip(ip: str) -> bool:
    if not ip or ip.endswith('.255') or ip in ('0.0.0.0', '255.255.255.255'):
        return False
    octets = ip.split('.')
    if len(octets) != 4:
        return False
    try:
        first = int(octets[0])
    except ValueError:
        return False
    if first >= 224 or ip.startswith('127.'):
        return False
    return True


def usable_mac(mac: str) -> bool:
    if not mac or mac.upper() == 'FF:FF:FF:FF:FF:FF':
        return False
    try:
        first = int(mac.split(':')[0], 16)
    except ValueError:
        return False
    return not bool(first & 0x01)


def parse_arp_line(line: str) -> tuple[str, str, str | None] | None:
    if '(incomplete)' in line.lower():
        return None
    ip_match = IP_RE.search(line)
    mac_match = MAC_RE.search(line)
    if not ip_match or not mac_match:
        return None
    ip = ip_match.group(0)
    mac = normalize_mac(mac_match.group(0))
    if not mac or not usable_ip(ip) or not usable_mac(mac):
        return None
    hostname = None
    prefix = line[:ip_match.start()].strip()
    if prefix and prefix not in {'?', '*'} and not prefix.startswith('('):
        hostname = prefix.split()[0].rstrip('.')
        if hostname in {ip, '?', '*'}:
            hostname = None
    return ip, mac, hostname


def read_arp_table() -> dict[str, dict]:
    hosts: dict[str, dict] = {}
    commands = (
        ['arp', '-an'],
        ['arp', '-a'],
    )
    output = ''
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        except (OSError, subprocess.SubprocessError):
            continue
        if result.stdout:
            output = result.stdout
            break
    for line in output.splitlines():
        parsed = parse_arp_line(line)
        if not parsed:
            continue
        ip, mac, hostname = parsed
        hosts[ip] = {'mac_address': mac}
        if hostname:
            hosts[ip]['hostname'] = hostname
    return hosts


def reverse_dns(ip: str) -> str | None:
    try:
        socket.setdefaulttimeout(0.35)
        name = socket.gethostbyaddr(ip)[0]
    except Exception:
        return None
    if not name or name in {ip, '?', '*'}:
        return None
    return name.rstrip('.')


def enrich_hostnames(hosts: dict[str, dict]) -> None:
    for ip, info in hosts.items():
        if info.get('hostname') or info.get('mdns_name'):
            continue
        name = reverse_dns(ip)
        if name:
            info['hostname'] = name


def enrich_mdns(hosts: dict[str, dict]) -> None:
    backend = Path(__file__).resolve().parents[1] / 'backend_django'
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    try:
        from core.utils.mdns_resolver import discover_mdns_hosts
    except Exception:
        return
    try:
        result = discover_mdns_hosts(timeout=6.0)
    except Exception:
        return
    if not result:
        return
    for ip, record in getattr(result, 'by_ip', {}).items():
        if not usable_ip(ip):
            continue
        info = hosts.setdefault(ip, {})
        if record.friendly_name:
            info['mdns_name'] = record.friendly_name
        if record.hostname:
            info.setdefault('hostname', record.hostname)
            info['mdns_hostname'] = record.hostname
        if record.apple_model:
            info['apple_model'] = record.apple_model
        mac = normalize_mac(getattr(record, 'mac_address', None) or '')
        if mac and usable_mac(mac) and not info.get('mac_address'):
            info['mac_address'] = mac


def write_identity(path: Path, hosts: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'source': 'host-arp',
        'hosts': hosts,
    }
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def collect_once(path: Path) -> int:
    hosts = read_arp_table()
    enrich_mdns(hosts)
    enrich_hostnames(hosts)
    write_identity(path, hosts)
    return len(hosts)


def main() -> int:
    parser = argparse.ArgumentParser(description='Publish host ARP identity for Duck Monitoring')
    parser.add_argument('--out', default=str(default_output_path()), help='identity.json path')
    parser.add_argument('--loop', type=int, default=0, help='Repeat every N seconds (0 = once)')
    args = parser.parse_args()
    path = Path(args.out)

    while True:
        try:
            count = collect_once(path)
            print(f'Wrote {count} LAN identities to {path}', flush=True)
        except Exception as exc:
            print(f'lan_identity failed: {exc}', file=sys.stderr, flush=True)
        if args.loop <= 0:
            return 0
        time.sleep(args.loop)


if __name__ == '__main__':
    raise SystemExit(main())
