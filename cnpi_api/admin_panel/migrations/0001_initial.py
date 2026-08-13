"""
Operations for admin_panel app migrations
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AdminUser',
            fields=[
                ('password', models.CharField(max_length=128)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('is_superuser', models.BooleanField(default=False)),
                ('username', models.CharField(max_length=150, unique=True)),
                ('first_name', models.CharField(max_length=150, blank=True)),
                ('last_name', models.CharField(max_length=150, blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('role', models.CharField(default='viewer', max_length=50, choices=[('manager', 'Manager'), ('editor', 'Editor'), ('viewer', 'Viewer')])),
                ('permissions', models.JSONField(blank=True, default=list)),
            ],
            options={
                'verbose_name': 'Admin User',
                'db_table': 'admin_users',
            },
        ),
    ]