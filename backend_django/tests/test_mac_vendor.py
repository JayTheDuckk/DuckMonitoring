from django.test import TestCase

from core.utils.mac_vendor import (
    is_locally_administered_mac,
    lookup_vendor,
    normalize_mac,
    research_mac,
)


class MacVendorLookupTests(TestCase):
    def test_normalize_mac(self):
        self.assertEqual(normalize_mac('48-22-54-32-ba-18'), '48:22:54:32:BA:18')
        self.assertEqual(normalize_mac('48225432ba18'), '48:22:54:32:BA:18')

    def test_lookup_known_vendors(self):
        self.assertEqual(lookup_vendor('00:0C:29:12:34:56'), 'VMware, Inc.')
        self.assertEqual(lookup_vendor('48:22:54:32:BA:18'), 'TP-Link Systems Inc')

    def test_private_mac_classification(self):
        self.assertTrue(is_locally_administered_mac('2A:3F:24:93:29:23'))
        research = research_mac('2A:3F:24:93:29:23', suggested_type='linux_server')
        self.assertEqual(research['mac_type'], 'private')
        self.assertEqual(research['vendor'], 'Private/Random MAC')
        self.assertIn('Private/random MAC', research['device_hint'])

    def test_manufacturer_mac_research(self):
        research = research_mac('48:22:54:32:BA:18')
        self.assertEqual(research['mac_type'], 'manufacturer')
        self.assertEqual(research['vendor'], 'TP-Link Systems Inc')
