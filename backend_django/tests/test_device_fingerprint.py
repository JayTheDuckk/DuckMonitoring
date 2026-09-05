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
        self.assertIn(result.os_guess.lower(), ('macos', 'macos/ios', 'linux/unix/macOS'.lower(), 'macos/linux'))
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
