from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from inventory.models import DeviceObservation, Host, LanWatchSettings
from inventory.watch import import_or_update_host, sync_hosts_from_observations
from monitoring.models import ServiceCheckConfig

User = get_user_model()


class LanWatchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='watcher',
            password='testpassword123',
            email='watcher@example.com',
            role='admin',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_import_keeps_mac_and_private_vendor(self):
        host, created, _, _ = import_or_update_host({
            'ip_address': '192.168.0.68',
            'mac_address': 'FE:00:B9:F4:EA:33',
            'vendor': 'Private/Random MAC',
            'mac_type': 'private',
            'os_guess': 'Android',
            'mdns_name': None,
        })
        self.assertTrue(created)
        self.assertEqual(host.mac_address, 'FE:00:B9:F4:EA:33')
        self.assertEqual(host.vendor, 'Private/Random MAC')
        self.assertEqual(host.os_guess, 'Android')

        import_or_update_host({
            'ip_address': '192.168.0.68',
            'mac_address': None,
            'vendor': None,
        })
        host.refresh_from_db()
        self.assertEqual(host.mac_address, 'FE:00:B9:F4:EA:33')
        self.assertEqual(host.vendor, 'Private/Random MAC')

    def test_hosts_api_includes_observation_identity(self):
        Host.objects.create(hostname='192.168.0.1', ip_address='192.168.0.1', status='up')
        DeviceObservation.objects.create(
            ip_address='192.168.0.1',
            mac_address='48:22:54:32:BA:18',
            vendor='TP-Link Systems Inc',
            os_guess='Embedded Linux',
        )
        response = self.client.get('/api/inventory/hosts/')
        self.assertEqual(response.status_code, 200)
        payload = response.data['results'][0] if isinstance(response.data, dict) else response.data[0]
        self.assertEqual(payload['mac_address'], '48:22:54:32:BA:18')
        self.assertEqual(payload['vendor'], 'TP-Link Systems Inc')
        self.assertEqual(payload['os_guess'], 'Embedded Linux')

    def test_watch_toggle_adds_ungrouped_hosts(self):
        DeviceObservation.objects.create(
            ip_address='192.168.0.218',
            mac_address='7A:9E:E3:9F:6D:79',
            mdns_name='Den TV',
            hostname='den-tv.local',
            vendor='Private/Random MAC',
            last_network='192.168.0.0/24',
        )
        self.assertEqual(Host.objects.count(), 0)

        off = self.client.get('/api/inventory/watch/')
        self.assertEqual(off.status_code, 200)
        self.assertFalse(off.data['auto_add_hosts'])

        on = self.client.patch('/api/inventory/watch/', {'auto_add_hosts': True}, format='json')
        self.assertEqual(on.status_code, 200)
        self.assertTrue(on.data['auto_add_hosts'])
        self.assertEqual(on.data['added'], 1)

        host = Host.objects.get(ip_address='192.168.0.218')
        self.assertIsNone(host.group_id)
        self.assertEqual(host.mdns_name, 'Den TV')
        self.assertTrue(ServiceCheckConfig.objects.filter(host=host, check_type='ping').exists())

    def test_sync_does_not_add_when_watch_off(self):
        DeviceObservation.objects.create(ip_address='192.168.0.50', last_network='192.168.0.0/24')
        added = sync_hosts_from_observations(create_missing=False)
        self.assertEqual(added, 0)
        self.assertEqual(Host.objects.count(), 0)

    def test_sync_skips_loopback(self):
        DeviceObservation.objects.create(ip_address='127.0.0.1')
        settings = LanWatchSettings.load()
        settings.auto_add_hosts = True
        settings.save()
        added = sync_hosts_from_observations(create_missing=True)
        self.assertEqual(added, 0)
        self.assertFalse(Host.objects.filter(ip_address='127.0.0.1').exists())

    @patch('inventory.discovery.load_lan_identity_cache', return_value={
        '192.168.0.60': {'mac_address': '2A:3F:24:93:29:23', 'mdns_name': "Jason's MacBook Pro"},
    })
    def test_hosts_api_uses_lan_identity_cache(self, _cache):
        Host.objects.create(hostname='192.168.0.60', ip_address='192.168.0.60', status='up')
        response = self.client.get('/api/inventory/hosts/')
        payload = response.data['results'][0] if isinstance(response.data, dict) else response.data[0]
        self.assertEqual(payload['mac_address'], '2A:3F:24:93:29:23')
        self.assertEqual(payload['mdns_name'], "Jason's MacBook Pro")

    def test_import_persists_discovered_services(self):
        host, created, _, service_checks = import_or_update_host({
            'ip_address': '192.168.0.60',
            'hostname': '192.168.0.60',
            'services': [
                {'port': 22, 'service': 'ssh', 'state': 'open'},
                {'port': 6379, 'service': 'redis', 'state': 'open'},
            ],
        })
        self.assertTrue(created)
        host.refresh_from_db()
        self.assertEqual([item['port'] for item in host.discovered_services], [22, 6379])
        self.assertGreaterEqual(service_checks, 2)

        response = self.client.get('/api/inventory/hosts/')
        payload = response.data['results'][0] if isinstance(response.data, dict) else response.data[0]
        self.assertEqual({item['port'] for item in payload['services']}, {22, 6379})

    def test_hosts_api_includes_observation_services(self):
        Host.objects.create(hostname='192.168.0.218', ip_address='192.168.0.218', status='up')
        DeviceObservation.objects.create(
            ip_address='192.168.0.218',
            last_payload={'services': [{'port': 8443, 'service': 'https', 'state': 'open'}]},
        )
        response = self.client.get('/api/inventory/hosts/')
        payload = response.data['results'][0] if isinstance(response.data, dict) else response.data[0]
        self.assertEqual(payload['services'][0]['port'], 8443)

    def test_hosts_api_includes_observation_latency(self):
        Host.objects.create(hostname='192.168.0.1', ip_address='192.168.0.1', status='up')
        DeviceObservation.objects.create(
            ip_address='192.168.0.1',
            sighting_count=4,
            last_payload={'latency_ms': 3.2, 'ping_ttl': 64, 'services': []},
        )
        response = self.client.get('/api/inventory/hosts/')
        payload = response.data['results'][0] if isinstance(response.data, dict) else response.data[0]
        self.assertEqual(payload['latency_ms'], 3.2)
        self.assertEqual(payload['ping_ttl'], 64)
        self.assertEqual(payload['sighting_count'], 4)
