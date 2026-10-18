"""
URL Configuration for WhatsApp Bot

Routes for webhook, health checks, and monitoring endpoints.
"""

from django.urls import path
from . import views


app_name = 'whatsapp_bot'

urlpatterns = [
    # Main webhook endpoint (GET for verification, POST for events)
    path('webhook/', views.whatsapp_webhook, name='webhook'),
    
    # Health check endpoint
    path('health/', views.health_check, name='health'),
    
    # Statistics endpoint
    path('stats/', views.stats, name='stats'),
]
