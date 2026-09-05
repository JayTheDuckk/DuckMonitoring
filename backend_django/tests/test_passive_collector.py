import os
from unittest.mock import patch

from django.test import TestCase

from core.utils.mdns_resolver import MdnsDiscoveryResult, MdnsRecord
from core.utils.passive_collector import collect_passive_hosts
from core.utils.ssdp_resolver import SsdpRecord
from inventory.models import DeviceObservation
from inventory.tasks import passive_collect


def _mdns_one():
    result = MdnsDiscoveryResult()
    record = MdnsRecord(
        ip_address='192.168.0.10',
        friendly_name='Living Room TV',
        hostname='living-room-tv.local',
        services=['_googlecast._tcp.local.'],
    )
    result.by_ip['192.168.0.10'] = record
    return result


def _ssdp_one():
    return {
        '192.168.0.20': SsdpRecord(
            ip_address='192.168.0.20',
            friendly_name='Roku UPnP',
            server='Roku/1.0 UPnP/1.0',
            usn='uuid:roku',
        )
    }


def _arp_one():
    return {'192.168.0.30': 'AA:BB:CC:DD:EE:FF'}


class PassiveCollectorTests(TestCase):
    @patch('core.utils.passive_collector._read_arp_and_neighbors', return_value=_arp_one())
    @patch('core.utils.passive_collector.discover_ssdp_hosts', return_value=_ssdp_one())
    @patch('core.utils.passive_collector.discover_mdns_hosts', return_value=_mdns_one())
    def test_collect_returns_one_host_per_source(self, _mdns, _ssdp, _arp):
        hosts = collect_passive_hosts('192.168.0.0/24', listen_seconds=0.1)
        by_ip = {host['ip_address']: host for host in hosts}

        self.assertEqual(len(by_ip), 3)
        self.assertIn('passive_mdns', by_ip['192.168.0.10']['identification_clues'])
        self.assertEqual(by_ip['192.168.0.10']['mdns_name'], 'Living Room TV')
        self.assertIn('passive_ssdp', by_ip['192.168.0.20']['identification_clues'])
        self.assertEqual(by_ip['192.168.0.20']['hostname'], 'Roku UPnP')
        self.assertIn('passive_arp', by_ip['192.168.0.30']['identification_clues'])
        self.assertEqual(by_ip['192.168.0.30']['mac_address'], 'AA:BB:CC:DD:EE:FF')

    @patch('core.utils.passive_collector._read_arp_and_neighbors', return_value=_arp_one())
    @patch('core.utils.passive_collector.discover_ssdp_hosts', return_value=_ssdp_one())
    @patch(
        'core.utils.passive_collector.discover_mdns_hosts',
        side_effect=RuntimeError('mdns down'),
    )
    def test_collect_swallows_source_exception(self, _mdns, _ssdp, _arp):
        hosts = collect_passive_hosts('192.168.0.0/24', listen_seconds=0.1)
        ips = {host['ip_address'] for host in hosts}

        self.assertIn('192.168.0.20', ips)
        self.assertIn('192.168.0.30', ips)
        self.assertNotIn('192.168.0.10', ips)

    @patch('core.utils.passive_collector._read_arp_and_neighbors', return_value=_arp_one())
    @patch('core.utils.passive_collector.discover_ssdp_hosts', return_value=_ssdp_one())
    @patch('core.utils.passive_collector.discover_mdns_hosts', return_value=_mdns_one())
    def test_task_upserts_observations(self, _mdns, _ssdp, _arp):
        with patch.dict(os.environ, {'PASSIVE_COLLECT_NETWORK': '192.168.0.0/24'}):
            created = passive_collect()

        self.assertEqual(created, 3)
        self.assertEqual(DeviceObservation.objects.count(), 3)

        tv = DeviceObservation.objects.get(ip_address='192.168.0.10')
        self.assertEqual(tv.mdns_name, 'Living Room TV')
        self.assertEqual(tv.hostname, 'living-room-tv.local')
        self.assertIn('passive_mdns', tv.identification_clues)
        self.assertEqual(tv.last_network, '192.168.0.0/24')
        self.assertEqual(tv.sighting_count, 1)

        roku = DeviceObservation.objects.get(ip_address='192.168.0.20')
        self.assertEqual(roku.hostname, 'Roku UPnP')
        self.assertEqual(roku.vendor, 'Roku')

        arp_host = DeviceObservation.objects.get(ip_address='192.168.0.30')
        self.assertEqual(arp_host.mac_address, 'AA:BB:CC:DD:EE:FF')

        with patch.dict(os.environ, {'PASSIVE_COLLECT_NETWORK': '192.168.0.0/24'}):
            updated = passive_collect()

        self.assertEqual(updated, 3)
        self.assertEqual(DeviceObservation.objects.count(), 3)
        tv.refresh_from_db()
        self.assertEqual(tv.sighting_count, 2)
        self.assertEqual(tv.mdns_name, 'Living Room TV')
