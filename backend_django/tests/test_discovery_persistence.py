import json
import os
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from inventory.discovery import load_lan_identity_cache
from inventory.models import DeviceObservation, Host, merge_identity_payload, upsert_observation

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

    @patch('inventory.views.perform_discovery')
    def test_scan_keeps_mac_vendor_name_when_live_scan_omits_them(self, mock_discover):
        mock_discover.return_value = {
            'hosts': [_host_payload()],
            'mdns_devices_found': 1,
        }
        self.client.post(
            '/api/inventory/discovery/scan/',
            {'network': '192.168.1.0/24', 'scan_type': 'quick'},
            format='json',
        )

        mock_discover.return_value = {
            'hosts': [{
                'ip_address': '192.168.1.10',
                'hostname': None,
                'mdns_name': None,
                'mac_address': None,
                'vendor': None,
                'services': [],
                'os_guess': 'Linux',
            }],
            'mdns_devices_found': 0,
        }
        response = self.client.post(
            '/api/inventory/discovery/scan/',
            {'network': '192.168.1.0/24', 'scan_type': 'quick'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        host = response.data['hosts'][0]
        self.assertEqual(host['mac_address'], 'aa:bb:cc:dd:ee:ff')
        self.assertEqual(host['vendor'], 'Apple')
        self.assertEqual(host['mdns_name'], 'Alpha')
        self.assertEqual(host['hostname'], 'alpha.local')


class ObservationIdentityTests(TestCase):
    def test_merge_identity_payload_keeps_previous_mac(self):
        merged = merge_identity_payload(
            {'ip_address': '192.168.1.10', 'mac_address': None, 'os_guess': 'Linux'},
            {'mac_address': 'AA:BB:CC:DD:EE:FF', 'vendor': 'Apple', 'hostname': 'alpha.local'},
        )
        self.assertEqual(merged['mac_address'], 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(merged['vendor'], 'Apple')
        self.assertEqual(merged['hostname'], 'alpha.local')
        self.assertEqual(merged['os_guess'], 'Linux')

    def test_upsert_does_not_wipe_known_mac(self):
        first = _host_payload()
        upsert_observation(first, '192.168.1.0/24')
        second = {
            'ip_address': '192.168.1.10',
            'mac_address': None,
            'hostname': None,
            'vendor': None,
        }
        observation = upsert_observation(second, '192.168.1.0/24')
        self.assertEqual(observation.mac_address, 'aa:bb:cc:dd:ee:ff')
        self.assertEqual(observation.vendor, 'Apple')
        self.assertEqual(observation.hostname, 'alpha.local')
        self.assertEqual(observation.last_payload.get('mac_address'), 'aa:bb:cc:dd:ee:ff')
        self.assertEqual(second['mac_address'], 'aa:bb:cc:dd:ee:ff')


class LanIdentityCacheTests(TestCase):
    def test_load_lan_identity_cache_from_env_path(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'identity.json'
            path.write_text(json.dumps({
                'hosts': {
                    '192.168.0.1': {
                        'mac_address': '48:22:54:32:BA:18',
                        'hostname': 'router',
                    }
                }
            }))
            with patch.dict(os.environ, {'LAN_IDENTITY_PATH': str(path)}):
                cache = load_lan_identity_cache()
        self.assertEqual(cache['192.168.0.1']['mac_address'], '48:22:54:32:BA:18')
        self.assertEqual(cache['192.168.0.1']['hostname'], 'router')
