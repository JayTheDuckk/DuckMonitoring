from django.test import TestCase

from core.utils.device_fingerprint import fingerprint_device
from core.utils.mdns_resolver import _friendly_name_from_service, _hostname_from_friendly


class MdnsResolverTests(TestCase):
    def test_friendly_name_parse(self):
        self.assertEqual(
            _friendly_name_from_service("Jason's MacBook Pro._airplay._tcp.local."),
            "Jason's MacBook Pro",
        )

    def test_hostname_slug(self):
        self.assertEqual(
            _hostname_from_friendly("Jason's MacBook Pro"),
            'jasons-macbook-pro.local',
        )

    def test_fingerprint_with_mdns_macbook(self):
        result = fingerprint_device(
            '192.168.0.60',
            mdns={
                'friendly_name': "Jason's MacBook Pro",
                'hostname': 'jasons-macbook-pro.local',
                'mdns_services': ['_companion-link._tcp.local.', '_airplay._tcp.local.'],
                'apple_model': 'Mac16,5',
            },
            mac_type='private',
            deep_probe=False,
        )
        self.assertEqual(result.os_guess, 'macOS')
        self.assertEqual(result.confidence, 'high')
        self.assertTrue(any('mDNS' in clue for clue in result.identification_clues))

    def test_fingerprint_with_mdns_chromecast(self):
        result = fingerprint_device(
            '192.168.0.218',
            mdns={
                'friendly_name': 'Den TV',
                'hostname': 'den-tv.local',
                'mdns_services': ['_googlecast._tcp.local.'],
                'mdns_properties': {'md': 'Philips 4K A1'},
            },
            deep_probe=False,
        )
        self.assertEqual(result.device_class, 'iot')
        self.assertIn('Cast', result.identification_clues[0])
