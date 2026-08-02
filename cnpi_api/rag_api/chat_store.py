"""
Chat Store
==========

In-memory session store for chat history.

Each session_id maps to a list of langchain BaseMessage objects
(HumanMessage / AIMessage).  This lets the RAG system remember prior
turns so pronouns and references can be resolved.

For production, swap this out for Redis / DB-backed storage.
"""

import threading
import time
from collections import defaultdict

# Session storage: session_id -> list[BaseMessage]
_sessions: dict[str, list] = defaultdict(list)

_lock = threading.Lock()

# Auto-expire sessions after this many seconds of inactivity
_SESSION_TTL = 3600  # 1 hour
_last_access: dict[str, float] = {}


def get_history(session_id: str) -> list:
    """Return the chat history (list of BaseMessage) for a session."""
    with _lock:
        _last_access[session_id] = time.time()
        return list(_sessions.get(session_id, []))


def set_history(session_id: str, messages: list) -> None:
    """Overwrite the chat history for a session."""
    with _lock:
        _sessions[session_id] = list(messages)
        _last_access[session_id] = time.time()


def clear_session(session_id: str) -> bool:
    """Delete a session's history. Returns True if it existed."""
    with _lock:
        existed = session_id in _sessions
        _sessions.pop(session_id, None)
        _last_access.pop(session_id, None)
        return existed


def list_sessions() -> list[str]:
    """Return all active session IDs."""
    with _lock:
        return list(_sessions.keys())


def cleanup_expired() -> int:
    """Remove sessions that have been inactive longer than _SESSION_TTL.

    Returns the number of sessions removed.
    """
    now = time.time()
    expired = [
        sid
        for sid, ts in _last_access.items()
        if now - ts > _SESSION_TTL
    ]
    with _lock:
        for sid in expired:
            _sessions.pop(sid, None)
            _last_access.pop(sid, None)
    return len(expired)
