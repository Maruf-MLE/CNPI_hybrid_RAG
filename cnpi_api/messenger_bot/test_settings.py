"""
messenger_bot/test_settings.py
===============================
Minimal Django settings for running messenger_bot tests locally
without requiring a PostgreSQL connection.

Usage:
    python manage.py test messenger_bot --settings=messenger_bot.test_settings
"""

from cnpi_api.settings import *  # noqa: F401, F403

# Override DB to SQLite so tests run without any Postgres server
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Silence warnings about missing FB_ vars during tests
FB_VERIFY_TOKEN = "test_verify_token"
FB_APP_SECRET = "test_app_secret"
FB_PAGE_ACCESS_TOKEN = "test_page_token"
FB_ALLOWED_PSIDS = "111111111,222222222"
