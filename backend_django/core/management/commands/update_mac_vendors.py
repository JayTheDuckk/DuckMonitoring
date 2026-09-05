from django.core.management.base import BaseCommand

from core.utils.mac_vendor import lookup_vendor, update_vendor_database
from discovery.models import DiscoveredHost
from inventory.models import Host


class Command(BaseCommand):
    help = 'Download/update the IEEE MAC vendor (OUI) database and optionally backfill existing records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backfill',
            action='store_true',
            help='Update vendor/manufacturer on hosts that have a MAC but no vendor',
        )

    def handle(self, *args, **options):
        self.stdout.write('Downloading IEEE OUI vendor database...')
        count = update_vendor_database()
        self.stdout.write(self.style.SUCCESS(f'Loaded {count} vendor prefixes'))

        if not options['backfill']:
            return

        updated_hosts = 0
        for host in Host.objects.exclude(mac_address__isnull=True).exclude(mac_address=''):
            if host.vendor:
                continue
            vendor = lookup_vendor(host.mac_address)
            if vendor:
                host.vendor = vendor
                host.save(update_fields=['vendor'])
                updated_hosts += 1

        updated_discovered = 0
        for item in DiscoveredHost.objects.exclude(mac_address__isnull=True).exclude(mac_address=''):
            if item.manufacturer:
                continue
            vendor = lookup_vendor(item.mac_address)
            if vendor:
                item.manufacturer = vendor
                item.save(update_fields=['manufacturer'])
                updated_discovered += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Backfilled {updated_hosts} hosts and {updated_discovered} discovered devices'
            )
        )
