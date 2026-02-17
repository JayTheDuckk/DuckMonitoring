import sys
import os
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import authenticate, get_user_model
User = get_user_model()

print(f"User model: {User}")
print(f"Username field: {User.USERNAME_FIELD}")

u = User.objects.get(username='admin')
print(f"User found: {u.username} (active={u.is_active})")
print(f"Check password 'admin': {u.check_password('admin')}")

user = authenticate(username='admin', password='admin')
print(f"Authenticate result: {user}")

if user is None:
    print("Authentication FAILED via authenticate()")
else:
    print("Authentication SUCCEEDED via authenticate()")
