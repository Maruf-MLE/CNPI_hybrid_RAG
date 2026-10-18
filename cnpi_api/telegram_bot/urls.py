"""
telegram_bot/urls.py
====================
URL routing for Telegram Bot webhook.

The webhook URL includes a secret token for security:
/telegram-webhook/<secret-token>/
"""

from django.urls import path

from telegram_bot import views

urlpatterns = [
    # Telegram Bot webhook — POST only, token-based authentication
    # Example: /telegram-webhook/your_secret_token_here/
    path("telegram-webhook/<str:token>/", views.telegram_webhook_view, name="telegram-webhook"),
]
