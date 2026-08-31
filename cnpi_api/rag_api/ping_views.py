"""
Ping / Health endpoints for keep-alive heartbeats and monitoring.

Security model
--------------
GET /api/ping/
    Public, unauthenticated.  Returns minimal JSON.  Safe to expose — no
    sensitive data, no side-effects.  Use this URL for external cron services
    (cron-job.org, UptimeRobot, Render Cron Jobs, etc.).

GET /api/health/
    Detailed health check.  Requires the X-Heartbeat-Secret header to match
    the HEARTBEAT_SECRET env var when that var is set.  Falls back to open
    access when the env var is blank (e.g. local dev).
"""

import os
import time
from datetime import datetime, timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_START_TIME = time.time()


def _check_heartbeat_secret(request) -> bool:
    """Return True if the request carries the correct heartbeat secret."""
    expected = os.getenv("HEARTBEAT_SECRET", "").strip()
    if not expected:
        # Secret not configured → allow (useful for local dev).
        return True
    provided = request.META.get("HTTP_X_HEARTBEAT_SECRET", "").strip()
    # Constant-time comparison to resist timing attacks.
    import hmac
    return hmac.compare_digest(expected, provided)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@api_view(["GET"])
def ping_view(request):
    """
    GET /api/ping/

    Lightweight public keep-alive endpoint.
    Returns 200 OK with a minimal JSON body — safe for cron services.
    """
    return Response(
        {
            "status": "ok",
            "message": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        status=200,
    )


@api_view(["GET"])
def health_view(request):
    """
    GET /api/health/

    Detailed health check.  Protected by HEARTBEAT_SECRET when that env var
    is configured.  Returns uptime, Django version, and DB connectivity.
    """
    if not _check_heartbeat_secret(request):
        return Response(
            {"error": "Unauthorized — missing or invalid X-Heartbeat-Secret header."},
            status=401,
        )

    import django
    db_ok = _check_db()
    uptime_seconds = int(time.time() - _START_TIME)

    payload = {
        "status": "ok" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "django_version": django.get_version(),
        "database": "connected" if db_ok else "error",
        "render_url": os.getenv("RENDER_PUBLIC_URL", "not-set"),
    }
    status_code = 200 if db_ok else 503
    return Response(payload, status=status_code)


def _check_db() -> bool:
    """Quick DB connectivity check — returns True on success."""
    try:
        from django.db import connection
        connection.ensure_connection()
        return True
    except Exception:
        return False
