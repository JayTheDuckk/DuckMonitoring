import os
import sys
import django

# Add the parent directory (backend_django) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user = User.objects.get(username='admin')
    user.role = 'admin'
    user.save()
    print(f"User '{user.username}' role updated to '{user.role}'.")
except User.DoesNotExist:
    print("User 'admin' does not exist.")
