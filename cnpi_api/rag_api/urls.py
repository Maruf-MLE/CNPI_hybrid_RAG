"""
URL routes for the rag_api app.

Public keep-alive endpoints (safe for external cron services):
  GET /api/ping/    → unauthenticated, returns {"status":"ok","message":"pong"}
  GET /api/health/  → protected by X-Heartbeat-Secret header (when env var set)

Use /api/ping/ for cron-job.org / UptimeRobot / Render Cron Jobs.
Use /api/health/ for internal monitoring dashboards.
"""

from django.urls import path

from . import views
from .ping_views import ping_view, health_view as secure_health_view

urlpatterns = [
    # Main chat endpoint
    path("chat/", views.chat_view, name="api-chat"),
    # Session management
    path("sessions/", views.session_list_view, name="api-session-list"),
    path("sessions/<str:session_id>/", views.session_history_view, name="api-session-history"),
    path("sessions/<str:session_id>/delete/", views.session_delete_view, name="api-session-delete"),
    # Health check (detailed, secret-protected)
    path("health/", secure_health_view, name="api-health"),
    # Public keep-alive ping (used by external cron/monitoring services)
    path("ping/", ping_view, name="api-ping"),
]
