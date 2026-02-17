import os
import sys
import django
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def reproduce_group_assignment():
    from inventory.models import Host, HostGroup
    
    print(" reproducing group assignment bug...")
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='test_debug', defaults={'email': 'debug@example.com'})
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Create a group
    group, _ = HostGroup.objects.get_or_create(name='TestGroup')
    print(f"Created Group ID: {group.id}")
    
    # Create a host without group
    host, _ = Host.objects.get_or_create(hostname='test-host-assignment', defaults={'status': 'up'})
    print(f"Created Host ID: {host.id}, Group: {host.group}")
    
    # Try updating with 'group_id' (What frontend sends)
    print("\nAttempting update with 'group_id'...")
    response = client.put(f'/api/inventory/hosts/{host.id}/', {
        'hostname': host.hostname,
        'ip_address': host.ip_address,
        'group_id': group.id
    }, format='json')
    
    if response.status_code == 200:
        host.refresh_from_db()
        print(f"Result after 'group_id' update: Host Group = {host.group}")
        if host.group != group:
            print("-> FAILED: 'group_id' was ignored.")
    else:
        print(f"-> FAILED: Request error {response.status_code} {response.data}")

    # Try updating with 'group' (What serializer expects)
    print("\nAttempting update with 'group'...")
    response = client.put(f'/api/inventory/hosts/{host.id}/', {
        'hostname': host.hostname,
        'ip_address': host.ip_address,
        'group': group.id
    }, format='json')
    
    if response.status_code == 200:
        host.refresh_from_db()
        print(f"Result after 'group' update: Host Group = {host.group}")
        if host.group == group:
            print("-> SUCCESS: 'group' worked.")
    else:
        print(f"-> FAILED: Request error {response.status_code} {response.data}")

if __name__ == '__main__':
    reproduce_group_assignment()
