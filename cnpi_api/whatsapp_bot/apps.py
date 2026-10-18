"""Django app configuration for WhatsApp bot."""

from django.apps import AppConfig


class WhatsappBotConfig(AppConfig):
    """Configuration for the WhatsApp bot application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'whatsapp_bot'
    verbose_name = 'WhatsApp Bot'
    
    def ready(self):
        """Initialize app when Django starts."""
        # Import signals or perform startup tasks here if needed
        pass
