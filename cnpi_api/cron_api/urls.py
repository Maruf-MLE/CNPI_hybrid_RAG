"""
URL configuration for cron_api app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path("cron/trigger/", views.cron_job_endpoint, name="cron_trigger"),
    path("cron/health/", views.cron_health_check, name="cron_health"),
]
