import pytest
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cnpi_api.settings')

# Enable admin panel auth pattern
AUTH_USER_MODEL = 'admin_panel.AdminUser'

TestAdminUser = type('TestAdminUser', (), {
    'username': 'test_admin',
    'email': 'test@example.com',
    'is_active': True,
    'is_staff': True,
    'is_superuser': True
})

from cnpi_api.admin_panel.models import AdminUser
user = TestAdminUser()
print(f"User created: {user.username}")
print(f"Email: {user.email}")
print(f"Active: {user.is_active}")
print(f"Staff: {user.is_staff}")
print(f"Superuser: {user.is_superuser}")