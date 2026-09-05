from django.test import TestCase

from core.utils.device_fingerprint import fingerprint_device


class DeviceFingerprintTests(TestCase):
    def test_macbook_ssh_redis_fingerprint(self):
        result = fingerprint_device(
            '192.168.0.60',
            hostname='Jasons-MacBook-Pro.local',
            services=[
                {'port': 22, 'service': 'SSH'},
                {'port': 6379, 'service': 'REDIS'},
            ],
            mac_type='private',
            vendor='Private/Random MAC',
            ping_ttl=64,
            deep_probe=False,
        )
        self.assertEqual(result.os_guess, 'macOS')
        self.assertGreater(len(result.identification_clues), 0)

    def test_windows_rdp_fingerprint(self):
        result = fingerprint_device(
            '192.168.0.10',
            services=[{'port': 3389, 'service': 'RDP'}, {'port': 445, 'service': 'SMB'}],
            ping_ttl=128,
            deep_probe=False,
        )
        self.assertEqual(result.os_guess, 'Windows')
        self.assertIn(result.confidence, ('high', 'medium'))

    def test_android_hostname(self):
        result = fingerprint_device(
            '192.168.0.20',
            hostname='android-abc123',
            mac_type='private',
            deep_probe=False,
        )
        self.assertEqual(result.os_guess, 'Android')

    def test_router_snmp_http(self):
        result = fingerprint_device(
            '192.168.0.1',
            vendor='TP-Link Systems Inc',
            services=[{'port': 53, 'service': 'DNS'}, {'port': 80, 'service': 'HTTP'}],
            deep_probe=False,
        )
        self.assertIn(result.device_class, ('router', 'network_device', 'server'))

    def test_private_mac_without_name_is_privacy_device(self):
        result = fingerprint_device(
            '192.168.0.80',
            hostname=None,
            services=[],
            mac_type='private',
            vendor='Private/Random MAC',
            ping_ttl=64,
            deep_probe=False,
        )
        self.assertEqual(result.device_class, 'privacy_device')
        self.assertTrue(result.privacy_reason)
        self.assertTrue(any('expected' in clue.lower() or 'privacy' in clue.lower()
                            for clue in result.identification_clues))

    def test_private_mac_with_name_is_not_privacy_device(self):
        result = fingerprint_device(
            '192.168.0.81',
            hostname='android-abc123',
            services=[],
            mac_type='private',
            deep_probe=False,
        )
        self.assertNotEqual(result.device_class, 'privacy_device')
        self.assertEqual(result.os_guess, 'Android')

    def test_private_mac_does_not_override_router(self):
        result = fingerprint_device(
            '192.168.0.1',
            hostname=None,
            vendor='TP-Link Systems Inc',
            services=[{'port': 161, 'service': 'SNMP'}, {'port': 80, 'service': 'HTTP'}],
            mac_type='private',
            deep_probe=False,
        )
        self.assertIn(result.device_class, ('router', 'network_device', 'server'))
        self.assertNotEqual(result.device_class, 'privacy_device')

    def test_ttl_alone_is_not_an_os(self):
        result = fingerprint_device(
            '192.168.0.90',
            ping_ttl=64,
            deep_probe=False,
        )
        self.assertEqual(result.os_guess, 'Unknown')

    def test_privacy_mac_alone_is_not_an_os(self):
        result = fingerprint_device(
            '192.168.0.91',
            mac_type='private',
            vendor='Private/Random MAC',
            ping_ttl=64,
            deep_probe=False,
        )
        self.assertEqual(result.os_guess, 'Unknown')

    def test_fire_tv_is_android(self):
        result = fingerprint_device(
            '192.168.0.231',
            hostname="Christina's FireTVStick",
            vendor='Amazon Technologies Inc.',
            services=[{'port': 8009, 'service': 'CAST'}],
            deep_probe=False,
        )
        self.assertEqual(result.os_guess, 'Android')

    def test_android_tv_mdns(self):
        result = fingerprint_device(
            '192.168.0.50',
            hostname='Living Room',
            mdns={
                'friendly_name': 'Living Room',
                'mdns_services': ['_androidtvremote2._tcp.local.'],
            },
            deep_probe=False,
        )
        self.assertEqual(result.os_guess, 'Android')

    def test_openssh_banner_alone_is_not_linux(self):
        result = fingerprint_device(
            '192.168.0.60',
            services=[{'port': 22, 'service': 'SSH'}],
            ping_ttl=64,
            deep_probe=False,
        )
        self.assertEqual(result.os_guess, 'Unknown')

    def test_ubuntu_ssh_banner_is_linux(self):
        from core.utils import device_fingerprint as fingerprint_mod

        original = fingerprint_mod.collect_probe_data
        fingerprint_mod.collect_probe_data = lambda ip, ports: {
            'ssh_banner': 'SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6',
        }
        try:
            result = fingerprint_device(
                '192.168.0.12',
                services=[{'port': 22, 'service': 'SSH'}],
                deep_probe=True,
            )
        finally:
            fingerprint_mod.collect_probe_data = original
        self.assertEqual(result.os_guess, 'Linux')
