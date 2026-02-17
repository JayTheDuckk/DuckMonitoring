import os
import django
import sys

# Setup Django environment
# sys.path.append(os.path.join(os.getcwd(), 'backend_django')) # Removed as we run from inside
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from inventory.models import Host, HostGroup

def add_hosts():
    hosts_data = [
        {'hostname': 'web-server-1', 'ip_address': '192.168.1.101', 'agent_id': 'web-server-1-agent'},
        {'hostname': 'web-server-2', 'ip_address': '192.168.1.102', 'agent_id': 'web-server-2-agent'},
        {'hostname': 'db-server', 'ip_address': '192.168.1.103', 'agent_id': 'db-server-agent'},
        {'hostname': 'cache-server', 'ip_address': '192.168.1.104', 'agent_id': 'cache-server-agent'},
        {'hostname': 'app-server-1', 'ip_address': '192.168.1.105', 'agent_id': 'app-server-1-agent'},
        {'hostname': 'app-server-2', 'ip_address': '192.168.1.106', 'agent_id': 'app-server-2-agent'},
    ]

    # Create a group for them
    group, created = HostGroup.objects.get_or_create(
        name='Docker Stack',
        defaults={'description': 'Hosts from docker-compose stack', 'color': '#00bcd4'}
    )
    if created:
        print(f"Created group: {group.name}")
    else:
        print(f"Using existing group: {group.name}")

    for host_data in hosts_data:
        host, created = Host.objects.get_or_create(
            hostname=host_data['hostname'],
            defaults={
                'ip_address': host_data['ip_address'],
                'agent_id': host_data['agent_id'],
                'group': group,
                'status': 'up' # Initialize as UP for testing/demo purposes
            }
        )
        if created:
            print(f"Added host: {host.hostname}")
        else:
            print(f"Host already exists: {host.hostname}")
            # Ensure it's in the group
            if host.group != group:
                host.group = group
                host.save()
                print(f"  -> Moved to group {group.name}")

if __name__ == '__main__':
    add_hosts()
