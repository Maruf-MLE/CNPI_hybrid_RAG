"""
Serializers for the RAG API.
"""

from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for POST /api/chat/ request body."""

    message = serializers.CharField(
        max_length=5000,
        help_text="User's question for this turn.",
    )
    session_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
        help_text="Session ID to keep chat history. If omitted, a new session is created.",
    )


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for POST /api/chat/ response body."""

    answer = serializers.CharField()
    answer_status = serializers.CharField()
    decided_path = serializers.CharField()
    rewritten_query = serializers.CharField()
    session_id = serializers.CharField()
    debug_info = serializers.DictField(required=False)


class SessionActionSerializer(serializers.Serializer):
    """Serializer for session action endpoints."""

    session_id = serializers.CharField(max_length=255)


class SessionListSerializer(serializers.Serializer):
    """Serializer for GET /api/sessions/ response."""

    sessions = serializers.ListField(child=serializers.CharField())
    count = serializers.IntegerField()


class SessionHistorySerializer(serializers.Serializer):
    """Serializer for GET /api/sessions/<id>/ response."""

    session_id = serializers.CharField()
    history = serializers.ListField(child=serializers.DictField())
    message_count = serializers.IntegerField()


class HealthResponseSerializer(serializers.Serializer):
    """Serializer for GET /api/health/ response."""

    status = serializers.CharField()
    graph_compiled = serializers.BooleanField()
    active_sessions = serializers.IntegerField()
