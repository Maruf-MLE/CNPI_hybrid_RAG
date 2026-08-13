"""
URL routes for the rag_api app.
"""

from django.urls import path

from . import views
from .ping_views import ping_view

urlpatterns = [
    # Main chat endpoint
    path("chat/", views.chat_view, name="api-chat"),
    # Session management
    path("sessions/", views.session_list_view, name="api-session-list"),
    path("sessions/<str:session_id>/", views.session_history_view, name="api-session-history"),
    path("sessions/<str:session_id>/delete/", views.session_delete_view, name="api-session-delete"),
    # Health check
    path("health/", views.health_view, name="api-health"),
    # Heartbeat/ping endpoint
    path("ping/", ping_view, name="api-ping"),
]
