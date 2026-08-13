"""
Django authentication configuration file
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# ----------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db.sqlite3'),
    }
}

# Required for AdminUser authentication
AUTH_USER_MODEL = 'admin_panel.AdminUser'

# Administrative users with django.contrib.auth models
# (Use these only for Django system tasks, not for admin panel)
# The admin panel uses the custom AdminUser model
ADMINS = [
    # ('Your Name', 'your_email@example.com'),
]

# Use these usernames/email when creating superusers for Django auth
# For admin panel access, use the custom admin_users table instead
# Example: python manage.py createsuperuser --username=test_user --email=test@example.com
USE_I18N = False

# Default users from .env for convenience
DEFAULT_SUPERUSER = os.getenv('DEFAULT_SUPERUSER', '')
DEFAULT_SUPERUSER_PASSWORD = os.getenv('DEFAULT_SUPERUSER_PASSWORD', '')

if DEFAULT_SUPERUSER:
    manage_createsuperuser = f"""
    Always create the admin user manually using python manage.py createsuperuser
    --username={os.getenv('DEFAULT_SUPERUSER', 'admin')}
    --email=admin@example.com

    For the custom AdminUser model (admin panel), users are created in the
    admin_users table via the superuser account or directly via the admin interface.
    """