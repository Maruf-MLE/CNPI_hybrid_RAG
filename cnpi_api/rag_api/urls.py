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
from .queue_views import queue_status_view
from .trending_views import trending_questions_view, track_question_click, generate_trending_questions_view

urlpatterns = [
    # Main chat endpoint
    path("chat/", views.chat_view, name="api-chat"),
    # Session management
    path("sessions/", views.session_list_view, name="api-session-list"),
    path("sessions/<str:session_id>/", views.session_history_view, name="api-session-history"),
    path("sessions/<str:session_id>/delete/", views.session_delete_view, name="api-session-delete"),
    # Queue status
    path("queue/status/", queue_status_view, name="api-queue-status"),
    # Trending questions
    path("trending-questions/", trending_questions_view, name="api-trending-questions"),
    path("trending-questions/generate/", generate_trending_questions_view, name="api-trending-questions-generate"),
    path("trending-questions/<int:question_id>/click/", track_question_click, name="api-question-click"),
    # Health check (detailed, secret-protected)
    path("health/", secure_health_view, name="api-health"),
    # Public keep-alive ping (used by external cron/monitoring services)
    path("ping/", ping_view, name="api-ping"),
]
