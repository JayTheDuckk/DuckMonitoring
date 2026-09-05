from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from inventory.models import DeviceObservation, Host

User = get_user_model()


def _host_payload(**overrides):
    payload = {
        'ip_address': '192.168.1.10',
        'hostname': 'alpha.local',
        'mdns_name': 'Alpha',
        'apple_model': 'MacBookPro18,1',
        'device_class': 'laptop',
        'confidence': 'high',
        'identification_clues': ['mDNS name', 'SSH open'],
        'mac_address': 'aa:bb:cc:dd:ee:ff',
        'vendor': 'Apple',
        'mac_type': 'manufacturer',
        'vendor_source': 'ieee_local',
        'services': [],
    }
    payload.update(overrides)
    return payload


class DiscoveryPersistenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='scanner',
            password='testpassword123',
            email='scanner@example.com',
            role='admin',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_import_hosts_writes_identity_fields(self):
        response = self.client.post(
            '/api/inventory/discovery/import_hosts/',
            {'hosts': [_host_payload()]},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        host = Host.objects.get(ip_address='192.168.1.10')
        self.assertEqual(host.hostname, 'Alpha')
        self.assertEqual(host.mdns_name, 'Alpha')
        self.assertEqual(host.apple_model, 'MacBookPro18,1')
        self.assertEqual(host.device_class, 'laptop')
        self.assertEqual(host.confidence, 80)
        self.assertEqual(host.identification_clues, ['mDNS name', 'SSH open'])
        self.assertEqual(host.vendor, 'Apple')
        self.assertIsNotNone(host.first_seen)
        self.assertIsNotNone(host.last_seen)

    def test_import_hosts_keeps_names_when_incoming_empty(self):
        self.client.post(
            '/api/inventory/discovery/import_hosts/',
            {'hosts': [_host_payload()]},
            format='json',
        )
        self.client.post(
            '/api/inventory/discovery/import_hosts/',
            {'hosts': [_host_payload(hostname='', mdns_name='', apple_model='')]},
            format='json',
        )

        host = Host.objects.get(ip_address='192.168.1.10')
        self.assertEqual(host.hostname, 'Alpha')
        self.assertEqual(host.mdns_name, 'Alpha')
        self.assertEqual(host.apple_model, 'MacBookPro18,1')

    def test_host_first_seen_is_stable_across_reimport(self):
        self.client.post(
            '/api/inventory/discovery/import_hosts/',
            {'hosts': [_host_payload()]},
            format='json',
        )
        host = Host.objects.get(ip_address='192.168.1.10')
        first_seen = host.first_seen
        last_seen = host.last_seen

        self.client.post(
            '/api/inventory/discovery/import_hosts/',
            {'hosts': [_host_payload(hostname='alpha-renamed.local')]},
            format='json',
        )
        host.refresh_from_db()
        self.assertEqual(host.first_seen, first_seen)
        self.assertGreaterEqual(host.last_seen, last_seen)

    @patch('inventory.views.perform_discovery')
    def test_second_scan_returns_missing_host_as_stale(self, mock_discover):
        mock_discover.return_value = {
            'hosts': [_host_payload()],
            'mdns_devices_found': 1,
        }
        first = self.client.post(
            '/api/inventory/discovery/scan/',
            {'network': '192.168.1.0/24', 'scan_type': 'quick'},
            format='json',
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(first.data['hosts']), 1)
        self.assertTrue(first.data['hosts'][0]['seen_this_scan'])
        self.assertTrue(first.data['hosts'][0]['last_seen'])

        mock_discover.return_value = {
            'hosts': [_host_payload(
                ip_address='192.168.1.20',
                hostname='beta.local',
                mdns_name='Beta',
                apple_model=None,
            )],
            'mdns_devices_found': 1,
        }
        second = self.client.post(
            '/api/inventory/discovery/scan/',
            {'network': '192.168.1.0/24', 'scan_type': 'quick'},
            format='json',
        )
        self.assertEqual(second.status_code, 200)

        by_ip = {host['ip_address']: host for host in second.data['hosts']}
        self.assertIn('192.168.1.10', by_ip)
        self.assertIn('192.168.1.20', by_ip)
        self.assertFalse(by_ip['192.168.1.10']['seen_this_scan'])
        self.assertTrue(by_ip['192.168.1.10']['last_seen'])
        self.assertEqual(by_ip['192.168.1.10']['mdns_name'], 'Alpha')
        self.assertTrue(by_ip['192.168.1.20']['seen_this_scan'])
        self.assertEqual(DeviceObservation.objects.count(), 2)
