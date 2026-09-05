from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from alerts.models import Alert, AlertRule
from alerts.pack import ensure_default_alert_pack
from alerts.tasks import evaluate_inventory_events
from inventory.models import DeviceObservation, Host
from monitoring.models import ServiceCheckConfig

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


class ImportHostsWatchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='importer',
            password='testpassword123',
            email='importer@example.com',
            role='admin',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_import_hosts_creates_ping_and_host_down_rule(self):
        response = self.client.post(
            '/api/inventory/discovery/import_hosts/',
            {'hosts': [_host_payload()]},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['alerts_created'], 1)

        host = Host.objects.get(ip_address='192.168.1.10')
        self.assertTrue(
            ServiceCheckConfig.objects.filter(host=host, check_type='ping').exists()
        )
        rule = AlertRule.objects.get(host=host, condition_type='host_down')
        self.assertEqual(rule.name, 'Alpha down')
        self.assertEqual(rule.severity, 'critical')
        self.assertEqual(
            rule.condition,
            {'field': 'status', 'operator': 'equals', 'value': 'critical'},
        )

        second = self.client.post(
            '/api/inventory/discovery/import_hosts/',
            {'hosts': [_host_payload()]},
            format='json',
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data['alerts_created'], 0)
        self.assertEqual(
            AlertRule.objects.filter(host=host, condition_type='host_down').count(),
            1,
        )
        self.assertEqual(
            ServiceCheckConfig.objects.filter(host=host, check_type='ping').count(),
            1,
        )


class DefaultAlertPackTests(TestCase):
    def test_ensure_default_alert_pack_is_idempotent(self):
        first = ensure_default_alert_pack()
        second = ensure_default_alert_pack()

        self.assertEqual(len(first), 3)
        self.assertEqual(len(second), 3)
        globals_qs = AlertRule.objects.filter(host__isnull=True, host_group__isnull=True)
        self.assertEqual(globals_qs.count(), 3)
        self.assertEqual(
            set(globals_qs.values_list('condition_type', flat=True)),
            {'host_down', 'device_new', 'device_gone'},
        )
        self.assertEqual(
            {rule.id for rule in first},
            {rule.id for rule in second},
        )


class InventoryEventTests(TestCase):
    def test_evaluate_inventory_events_creates_new_and_gone_without_duplicates(self):
        now = timezone.now()
        DeviceObservation.objects.create(
            ip_address='10.0.0.5',
            hostname='fresh',
            first_seen=now - timedelta(minutes=2),
            last_seen=now,
        )
        DeviceObservation.objects.create(
            ip_address='10.0.0.6',
            hostname='stale',
            first_seen=now - timedelta(days=5),
            last_seen=now - timedelta(hours=25),
        )

        evaluate_inventory_events()

        new_alerts = Alert.objects.filter(rule__condition_type='device_new', status='firing')
        gone_alerts = Alert.objects.filter(rule__condition_type='device_gone', status='firing')
        self.assertEqual(new_alerts.count(), 1)
        self.assertEqual(gone_alerts.count(), 1)
        self.assertIn('10.0.0.5', new_alerts.get().message)
        self.assertIn('10.0.0.6', gone_alerts.get().message)
        self.assertEqual(new_alerts.get().severity, 'info')
        self.assertEqual(gone_alerts.get().severity, 'warning')

        evaluate_inventory_events()
        self.assertEqual(
            Alert.objects.filter(rule__condition_type='device_new', status='firing').count(),
            1,
        )
        self.assertEqual(
            Alert.objects.filter(rule__condition_type='device_gone', status='firing').count(),
            1,
        )
        self.assertEqual(Alert.objects.count(), 2)
