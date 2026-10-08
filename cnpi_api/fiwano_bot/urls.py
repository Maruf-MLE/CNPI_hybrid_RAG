"""
URL routes for the fiwano_bot app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Main webhook endpoint
    path('fiwano/webhook/', views.fiwano_webhook, name='fiwano-webhook'),
    
    # Health check
    path('fiwano/health/', views.health_check, name='fiwano-health'),
    
    # Test endpoint (for diagnostics)
    path('fiwano/test/', views.webhook_test, name='fiwano-test'),
]
