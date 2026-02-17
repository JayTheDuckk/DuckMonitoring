from django.core.management.base import BaseCommand
from inventory.models import Host
from monitoring.models import ServiceCheckConfig

class Command(BaseCommand):
    help = 'Ensures all hosts have a Ping service check configured'

    def handle(self, *args, **options):
        hosts = Host.objects.all()
        created_count = 0
        
        for host in hosts:
            # Check if ping check exists
            exists = ServiceCheckConfig.objects.filter(
                host=host,
                check_type='ping'
            ).exists()
            
            if not exists:
                ServiceCheckConfig.objects.create(
                    host=host,
                    check_type='ping',
                    check_name='Ping Check',
                    interval=60,
                    enabled=True,
                    parameters={'count': 3}
                )
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created Ping check for host {host.hostname}'))
            else:
                self.stdout.write(f'Ping check already exists for host {host.hostname}')
                
        self.stdout.write(self.style.SUCCESS(f'Finished. Created {created_count} missing ping checks.'))
