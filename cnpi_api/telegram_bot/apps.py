"""
telegram_bot/apps.py
====================
Django app configuration for Telegram Bot.
"""

from django.apps import AppConfig


class TelegramBotConfig(AppConfig):
    """Configuration for the Telegram Bot Django app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telegram_bot'
    verbose_name = 'Telegram Bot (RAG-powered Q&A)'
