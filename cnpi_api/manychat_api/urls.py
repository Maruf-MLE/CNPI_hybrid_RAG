"""
URL routes for the manychat_api app.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("manychat/webhook", views.manychat_webhook, name="manychat-webhook"),
    path("health", views.health_check, name="health-check"),
]
