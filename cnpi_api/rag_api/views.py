"""
Views for the RAG API.
"""

import logging
import uuid

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import chat_store
from .queue_manager import get_queue_manager
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    SessionActionSerializer,
    SessionListSerializer,
    SessionHistorySerializer,
    HealthResponseSerializer,
    QueueStatusSerializer,
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
    
    ✨ NEW: Queue management - limits to 3 concurrent users
    If queue is full, returns HTTP 429 with queue status.

    Request body (JSON):
        {
            "message": "CST department er CI ke?",
            "session_id": "abc123",         // optional
            "query_source": "telegram"      // optional: "telegram", "web", "default"
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
        
    Or if queued (HTTP 429):
        {
            "queued": true,
            "queue_position": 2,
            "estimated_wait_seconds": 45,
            "message": "Please wait, you are in queue...",
            "session_id": "abc123"
        }
    """
    serializer = ChatRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    message = serializer.validated_data["message"].strip()
    session_id = serializer.validated_data.get("session_id", "").strip()
    query_source = serializer.validated_data.get("query_source", "default").strip()
    
    # ★ DEBUG: Log query_source
    logger.info("Received query_source: '%s' for message: %s", query_source, message[:50])

    if not message:
        return Response(
            {"error": "message field cannot be empty."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Create a new session if none provided
    if not session_id:
        session_id = uuid.uuid4().hex[:16]

    # ====================================================================
    # ✨ QUEUE MANAGEMENT: Check if user can proceed
    # ====================================================================
    queue_manager = get_queue_manager()
    can_proceed, queue_position, estimated_wait = queue_manager.can_proceed(session_id)
    
    if not can_proceed:
        # User must wait in queue
        logger.info(f"Session {session_id} is in queue. Position: {queue_position}, Wait: {estimated_wait}s")
        return Response(
            {
                "queued": True,
                "queue_position": queue_position,
                "estimated_wait_seconds": estimated_wait,
                "message": "অনুগ্রহ করে অপেক্ষা করুন, আপনি সারিতে আছেন...",
                "message_en": "Please wait, you are in queue...",
                "session_id": session_id,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Load chat history for this session
    chat_history = chat_store.get_history(session_id)

    try:
        from .rag_engine import run_rag

        result = run_rag(
            user_input=message, 
            chat_history=chat_history,
            query_source=query_source  # ← Pass query_source to RAG engine
        )

        # Persist updated chat history
        chat_store.set_history(session_id, result["messages"])

        response_data = {
            "answer": result["final_answer"],
            "answer_status": result["answer_status"],
            "decided_path": result["decided_path"],
            "rewritten_query": result["rewritten_query"],
            "session_id": session_id,
            "debug_info": result.get("debug_info", {}),
            "contexts": result.get("contexts", []),
            "queued": False,  # ← Not queued, processed immediately
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
    finally:
        # ====================================================================
        # ✨ QUEUE MANAGEMENT: Release slot when request completes
        # ====================================================================
        queue_manager.release(session_id)
        logger.info(f"Session {session_id} released from queue")


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
