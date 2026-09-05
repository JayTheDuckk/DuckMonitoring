"""
SSDP / UPnP discovery for local network host identification.
"""

from __future__ import annotations

import logging
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SSDP_MULTICAST = ('239.255.255.250', 1900)


@dataclass
class SsdpRecord:
    ip_address: str
    friendly_name: str
    server: str
    usn: str
    location: str = ''
    st: str = ''

    def to_dict(self) -> Dict:
        return {
            'friendly_name': self.friendly_name,
            'server': self.server,
            'usn': self.usn,
            'location': self.location,
            'st': self.st,
        }


def _parse_ssdp_response(text: str, ip: str) -> Optional[SsdpRecord]:
    headers: Dict[str, str] = {}
    for line in text.split('\r\n'):
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        headers[key.strip().upper()] = value.strip()

    server = headers.get('SERVER', '')
    usn = headers.get('USN', '')
    location = headers.get('LOCATION', '')
    st = headers.get('ST', headers.get('NT', ''))

    name = ''
    match = re.search(r'uuid:[^:]+', usn, re.IGNORECASE)
    if server:
        name = server.split('/')[0].strip()
    if not name and st:
        name = st.split(':')[-1]

    if not any([server, usn, location]):
        return None

    return SsdpRecord(
        ip_address=ip,
        friendly_name=name or f'UPnP device ({ip})',
        server=server,
        usn=usn,
        location=location,
        st=st,
    )


def discover_ssdp_hosts(timeout: float = 4.0) -> Dict[str, SsdpRecord]:
    """Send SSDP M-SEARCH and collect UPnP device metadata by IP."""
    records: Dict[str, SsdpRecord] = {}
    message = '\r\n'.join([
        'M-SEARCH * HTTP/1.1',
        f'HOST: {SSDP_MULTICAST[0]}:{SSDP_MULTICAST[1]}',
        'MAN: "ssdp:discover"',
        'MX: 2',
        'ST: ssdp:all',
        'USER-AGENT: DuckMonitoring/2.0',
        '',
        '',
    ]).encode('utf-8')

    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(0.5)
        sock.sendto(message, SSDP_MULTICAST)

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(8192)
            except socket.timeout:
                continue
            ip = addr[0]
            text = data.decode('utf-8', errors='ignore')
            if not text.startswith('HTTP/1.') and 'NOTIFY' not in text[:20].upper():
                continue
            record = _parse_ssdp_response(text, ip)
            if not record:
                continue
            if ip not in records or len(record.server) > len(records[ip].server):
                records[ip] = record
    except Exception as exc:
        logger.warning('SSDP discovery failed: %s', exc)
    finally:
        if sock is not None:
            sock.close()

    return records


def guess_vendor_from_ssdp(record: SsdpRecord) -> Optional[str]:
    server = (record.server or record.friendly_name or '').lower()
    vendors = [
        ('tp-link', 'TP-Link'),
        ('amazon', 'Amazon'),
        ('google', 'Google'),
        ('philips', 'Philips'),
        ('samsung', 'Samsung'),
        ('sony', 'Sony'),
        ('roku', 'Roku'),
        ('microsoft', 'Microsoft'),
        ('apple', 'Apple Inc.'),
        ('asus', 'ASUS'),
        ('netgear', 'Netgear'),
        ('ubiquiti', 'Ubiquiti'),
    ]
    for needle, label in vendors:
        if needle in server:
            return label
    return None
