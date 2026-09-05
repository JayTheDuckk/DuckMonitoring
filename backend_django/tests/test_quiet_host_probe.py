from django.test import TestCase

from core.utils.quiet_host_probe import (
    describe_quiet_host,
    is_sparse_host,
    stamp_privacy_device,
)
from core.utils.ssdp_resolver import _parse_ssdp_response, guess_vendor_from_ssdp, SsdpRecord


class QuietHostProbeTests(TestCase):
    def test_sparse_host_detection(self):
        sparse = {'mac_type': 'private', 'services': [], 'mdns_name': None, 'hostname': None, 'vendor_source': 'classified'}
        rich = {'mac_type': 'private', 'services': [{'port': 22}], 'mdns_name': 'Mac'}
        self.assertTrue(is_sparse_host(sparse))
        self.assertFalse(is_sparse_host(rich))

    def test_describe_quiet_host(self):
        host = {
            'mac_type': 'private',
            'ping_ttl': 64,
            'latency_ms': 420,
            'services': [],
            'mdns_name': None,
        }
        text = describe_quiet_host(host)
        self.assertIn('privacy/random MAC', text)
        self.assertIn('TTL 64', text)
        self.assertIn('High latency', text)
        self.assertIn('expected, not a failed server', text)

    def test_stamp_privacy_device_for_private_mac_without_name(self):
        host = {
            'mac_type': 'private',
            'hostname': None,
            'mdns_name': None,
            'services': [],
            'device_class': 'mobile',
        }
        stamped = stamp_privacy_device(host)
        self.assertEqual(stamped['device_class'], 'privacy_device')
        self.assertTrue(stamped['privacy_reason'])
        self.assertIn(stamped['privacy_reason'], stamped['identification_clues'])

    def test_stamp_privacy_device_skips_named_or_stronger_class(self):
        named = stamp_privacy_device({
            'mac_type': 'private',
            'hostname': 'iphone.local',
            'mdns_name': None,
            'device_class': 'phone',
        })
        self.assertEqual(named['device_class'], 'phone')

        router = stamp_privacy_device({
            'mac_type': 'private',
            'hostname': None,
            'mdns_name': None,
            'device_class': 'router',
        })
        self.assertEqual(router['device_class'], 'router')


class SsdpResolverTests(TestCase):
    def test_parse_ssdp_response(self):
        text = '\r\n'.join([
            'HTTP/1.1 200 OK',
            'CACHE-CONTROL: max-age=1800',
            'EXT:',
            'LOCATION: http://192.168.0.1:1900/rootDesc.xml',
            'SERVER: TP-LINK/TP-LINK UPnP/1.1 MiniUPnPd/1.8',
            'ST: upnp:rootdevice',
            'USN: uuid:abc::upnp:rootdevice',
            '',
            '',
        ])
        record = _parse_ssdp_response(text, '192.168.0.1')
        self.assertIsNotNone(record)
        self.assertEqual(record.ip_address, '192.168.0.1')
        self.assertEqual(guess_vendor_from_ssdp(record), 'TP-Link')
