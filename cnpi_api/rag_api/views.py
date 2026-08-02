"""
Views for the RAG API.
"""

import logging
import uuid

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import chat_store
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    SessionActionSerializer,
    SessionListSerializer,
    SessionHistorySerializer,
    HealthResponseSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: serialize BaseMessage objects to plain dicts for JSON response
# ---------------------------------------------------------------------------

def _serialize_messages(messages: list) -> list[dict]:
    """Convert langchain BaseMessage objects into JSON-safe dicts."""
    result = []
    for msg in messages:
        role = "unknown"
        cls = type(msg).__name__
        if cls == "HumanMessage":
            role = "human"
        elif cls == "AIMessage":
            role = "ai"
        elif cls == "SystemMessage":
            role = "system"

        content = msg.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )

        result.append({"role": role, "content": str(content)})
    return result


# ---------------------------------------------------------------------------
# Chat endpoint — the main RAG query endpoint
# ---------------------------------------------------------------------------

@api_view(["POST"])
def chat_view(request):
    """POST /api/chat/

    Accepts a user question (and optional session_id), runs the full RAG
    pipeline, and returns the bot's answer.

    Request body (JSON):
        {
            "message": "CST department er CI ke?",
            "session_id": "abc123"          // optional
        }

    Response (JSON):
        {
            "answer": "CST Department-এর Chief Instructor হলেন ...",
            "answer_status": "found",
            "decided_path": "sql_retrieve",
            "rewritten_query": "Who is the Chief Instructor of the CST department?",
            "session_id": "abc123",
            "debug_info": { ... }
        }
    """
    serializer = ChatRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    message = serializer.validated_data["message"].strip()
    session_id = serializer.validated_data.get("session_id", "").strip()

    if not message:
        return Response(
            {"error": "message field cannot be empty."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Create a new session if none provided
    if not session_id:
        session_id = uuid.uuid4().hex[:16]

    # Load chat history for this session
    chat_history = chat_store.get_history(session_id)

    try:
        from .rag_engine import run_rag

        result = run_rag(user_input=message, chat_history=chat_history)

        # Persist updated chat history
        chat_store.set_history(session_id, result["messages"])

        response_data = {
            "answer": result["final_answer"],
            "answer_status": result["answer_status"],
            "decided_path": result["decided_path"],
            "rewritten_query": result["rewritten_query"],
            "session_id": session_id,
            "debug_info": result.get("debug_info", {}),
        }

        resp_serializer = ChatResponseSerializer(response_data)
        return Response(resp_serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("RAG pipeline error for session %s", session_id)
        return Response(
            {
                "error": "RAG pipeline failed.",
                "detail": str(e),
                "session_id": session_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# Session management endpoints
# ---------------------------------------------------------------------------

@api_view(["GET"])
def session_list_view(request):
    """GET /api/sessions/

    Returns a list of all active session IDs.
    """
    chat_store.cleanup_expired()
    sessions = chat_store.list_sessions()
    data = {"sessions": sessions, "count": len(sessions)}
    serializer = SessionListSerializer(data)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def session_history_view(request, session_id):
    """GET /api/sessions/<session_id>/

    Returns the full chat history (as role/content dicts) for a session.
    """
    messages = chat_store.get_history(session_id)
    serialized = _serialize_messages(messages)
    data = {
        "session_id": session_id,
        "history": serialized,
        "message_count": len(serialized),
    }
    serializer = SessionHistorySerializer(data)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
def session_delete_view(request, session_id):
    """DELETE /api/sessions/<session_id>/

    Clears the chat history for a session.
    """
    existed = chat_store.clear_session(session_id)
    if not existed:
        return Response(
            {"detail": f"Session '{session_id}' not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {"detail": f"Session '{session_id}' cleared."},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@api_view(["GET"])
def health_view(request):
    """GET /api/health/

    Returns server health and graph compilation status.
    """
    graph_compiled = False
    try:
        from .rag_engine import _get_compiled_graph

        _get_compiled_graph()
        graph_compiled = True
    except Exception:
        graph_compiled = False

    data = {
        "status": "ok" if graph_compiled else "degraded",
        "graph_compiled": graph_compiled,
        "active_sessions": len(chat_store.list_sessions()),
    }
    serializer = HealthResponseSerializer(data)
    return Response(serializer.data, status=status.HTTP_200_OK)
