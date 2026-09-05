from django.test import TestCase

from core.utils.device_fingerprint import fingerprint_device
from core.utils.mdns_resolver import (
    MdnsRecord,
    _friendly_name_from_service,
    _hostname_from_friendly,
    _pick_better_friendly_name,
    _resolve_friendly_name,
    guess_vendor_from_mdns,
)


class MdnsResolverTests(TestCase):
    def test_friendly_name_parse(self):
        self.assertEqual(
            _friendly_name_from_service("Jason's MacBook Pro._airplay._tcp.local."),
            "Jason's MacBook Pro",
        )

    def test_raop_friendly_name(self):
        self.assertEqual(
            _resolve_friendly_name(
                "DE65A2633797@Jason's MacBook Pro._raop._tcp.local.",
                {},
                '_raop._tcp.local.',
            ),
            "Jason's MacBook Pro",
        )

    def test_chromecast_friendly_name(self):
        self.assertEqual(
            _resolve_friendly_name(
                'Philips-4K-A1-cc67ca70a28dc98fdceeb69b7da015ba._googlecast._tcp.local.',
                {'fn': 'Den TV', 'md': 'Philips 4K A1'},
                '_googlecast._tcp.local.',
            ),
            'Den TV',
        )

    def test_amazon_friendly_name(self):
        self.assertEqual(
            _resolve_friendly_name(
                'amzn.dmgr:0BAECE33521E1296B79EC5CA4D3510D1:IWtzu2uork:904801._amzn-wplay._tcp.local.',
                {'n': "Christina's FireTVStick"},
                '_amzn-wplay._tcp.local.',
            ),
            "Christina's FireTVStick",
        )

    def test_prefers_name_without_duplicate_suffix(self):
        self.assertEqual(
            _pick_better_friendly_name("Jason's MacBook Pro (2)", "Jason's MacBook Pro"),
            "Jason's MacBook Pro",
        )

    def test_vendor_guess_apple_from_companion_link(self):
        record = MdnsRecord(
            ip_address='192.168.0.60',
            friendly_name="Jason's MacBook Pro",
            hostname='jasons-macbook-pro.local',
            services=['_companion-link._tcp.local.'],
            apple_model='Mac16,5',
        )
        guess = guess_vendor_from_mdns(record)
        self.assertEqual(guess['vendor'], 'Apple Inc.')
        self.assertEqual(guess['vendor_source'], 'mdns_guess')

    def test_vendor_guess_philips_from_googlecast(self):
        record = MdnsRecord(
            ip_address='192.168.0.218',
            friendly_name='Den TV',
            hostname='den-tv.local',
            services=['_googlecast._tcp.local.'],
            properties={'fn': 'Den TV', 'md': 'Philips 4K A1'},
        )
        guess = guess_vendor_from_mdns(record)
        self.assertEqual(guess['vendor'], 'Philips')

    def test_vendor_guess_amazon_from_fire_tv(self):
        record = MdnsRecord(
            ip_address='192.168.0.231',
            friendly_name="Christina's FireTVStick",
            hostname='christinas-firetvstick.local',
            services=['_amzn-wplay._tcp.local.'],
            properties={'n': "Christina's FireTVStick"},
        )
        guess = guess_vendor_from_mdns(record)
        self.assertEqual(guess['vendor'], 'Amazon')

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
