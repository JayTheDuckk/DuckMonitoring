import os
import sys
import django

# Add the parent directory (backend_django) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from inventory.models import Host
print(f"Total Hosts: {Host.objects.count()}")
for h in Host.objects.all():
    print(f"Host: {h.hostname} (IP: {h.ip_address}, Group: {h.group})")
