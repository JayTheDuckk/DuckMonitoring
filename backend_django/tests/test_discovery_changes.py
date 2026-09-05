from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from inventory.models import DeviceObservation

User = get_user_model()


def _observation(*, ip, first_seen, last_seen, device_class='laptop', mdns_name=None, network='192.168.1.0/24', **extra):
    """Create a DeviceObservation with explicit first/last seen timestamps."""
    payload = {
        'ip_address': ip,
        'device_class': device_class,
        'mdns_name': mdns_name,
        **extra,
    }
    return DeviceObservation.objects.create(
        ip_address=ip,
        hostname=extra.get('hostname'),
        mdns_name=mdns_name,
        device_class=device_class,
        last_payload=payload,
        first_seen=first_seen,
        last_seen=last_seen,
        last_network=network,
        sighting_count=1,
    )


class DiscoveryChangesTests(TestCase):
    """
    GET /api/inventory/discovery/changes/?days=7

    new: first_seen >= since (appeared during the window).
    gone: first_seen < since (they used to be around) AND last_seen is older
          than max(since, now-24h) AND last_seen is still within 30 days.
          A host seen in the last 24 hours is not gone. A host last seen more
          than 30 days ago is too old to count as recently gone.
    unnamed_mobile: device_class in {privacy_device, mobile, phone} and no mdns_name.
    """

    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user(
            username='changes',
            password='testpassword123',
            email='changes@example.com',
            role='admin',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_changes_classifies_new_vs_gone(self):
        since_window = self.now - timedelta(days=7)

        new_host = _observation(
            ip='192.168.1.10',
            first_seen=self.now - timedelta(days=2),
            last_seen=self.now - timedelta(minutes=5),
            device_class='laptop',
            mdns_name='New Laptop',
        )
        gone_host = _observation(
            ip='192.168.1.20',
            first_seen=self.now - timedelta(days=14),
            last_seen=self.now - timedelta(days=2),
            device_class='desktop',
            mdns_name='Old Desktop',
        )
        still_here = _observation(
            ip='192.168.1.30',
            first_seen=self.now - timedelta(days=20),
            last_seen=self.now - timedelta(hours=1),
            device_class='router',
            mdns_name='Gateway',
        )
        ancient = _observation(
            ip='192.168.1.40',
            first_seen=self.now - timedelta(days=90),
            last_seen=self.now - timedelta(days=40),
            device_class='printer',
        )
        unnamed_phone = _observation(
            ip='192.168.1.50',
            first_seen=self.now - timedelta(days=10),
            last_seen=self.now - timedelta(hours=2),
            device_class='privacy_device',
            mdns_name=None,
            hostname=None,
        )
        named_phone = _observation(
            ip='192.168.1.60',
            first_seen=self.now - timedelta(days=3),
            last_seen=self.now - timedelta(minutes=20),
            device_class='phone',
            mdns_name="Jay's iPhone",
        )

        response = self.client.get('/api/inventory/discovery/changes/', {'days': 7})
        self.assertEqual(response.status_code, 200)
        self.assertIn('since', response.data)

        new_ips = {host['ip_address'] for host in response.data['new']}
        gone_ips = {host['ip_address'] for host in response.data['gone']}
        unnamed_ips = {host['ip_address'] for host in response.data['unnamed_mobile']}

        self.assertIn(new_host.ip_address, new_ips)
        self.assertNotIn(gone_host.ip_address, new_ips)
        self.assertNotIn(still_here.ip_address, new_ips)

        self.assertIn(gone_host.ip_address, gone_ips)
        self.assertNotIn(new_host.ip_address, gone_ips)
        self.assertNotIn(still_here.ip_address, gone_ips)
        self.assertNotIn(ancient.ip_address, gone_ips)

        self.assertIn(unnamed_phone.ip_address, unnamed_ips)
        self.assertNotIn(named_phone.ip_address, unnamed_ips)
        self.assertNotIn(new_host.ip_address, unnamed_ips)

        since = datetime.fromisoformat(response.data['since'])
        self.assertLessEqual(abs((since - since_window).total_seconds()), 5)

    def test_changes_filters_by_network(self):
        _observation(
            ip='10.0.0.10',
            first_seen=self.now - timedelta(days=1),
            last_seen=self.now,
            network='10.0.0.0/24',
        )
        _observation(
            ip='192.168.1.10',
            first_seen=self.now - timedelta(days=1),
            last_seen=self.now,
            network='192.168.1.0/24',
        )

        response = self.client.get(
            '/api/inventory/discovery/changes/',
            {'days': 7, 'network': '10.0.0.0/24'},
        )
        self.assertEqual(response.status_code, 200)
        new_ips = {host['ip_address'] for host in response.data['new']}
        self.assertEqual(new_ips, {'10.0.0.10'})
