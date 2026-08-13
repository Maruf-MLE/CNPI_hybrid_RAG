# Fetch admin users from the database
import os
import sys

# Add the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cnpi_api'))

from django.core.management import execute_from_command_line
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cnpi_api.settings')
django.setup()

def list_admin_users():
    """List all admin users with their details"""
    from admin_panel.models import AdminUser

    users = AdminUser.objects.all()

    if not users.exists():
        print("\n❌ No admin users found!")
        print("\nTo create your first admin user:")
        print("1. Run: python create_admin_user.py")
        print("   (or use: python manage.py createsuperuser)\n")
        return

    print("\n✅ Admin Users:")
    print("=" * 50)
    for user in users:
        status = "✅ Active" if user.is_active else "❌ Inactive"
        superuser = "👑 Superuser" if user.is_superuser else ""
        print(f"\nUsername: {user.username}")
        print(f"Email: {user.email or 'No email'}")
        print(f"Role: {user.role}")
        print(f"Status: {status} {superuser}")
        print(f"Last Login: {user.last_login}")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    list_admin_users()