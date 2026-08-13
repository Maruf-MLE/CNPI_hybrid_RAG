"""
Ping endpoint for heartbeats
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def ping_view(request):
    """
    GET /api/ping/

    Simple heartbeat ping endpoint that returns 200 OK.
    Used by external monitoring systems to keep the server alive.
    """
    return Response({"status": "ok", "message": "pong"}, status=200)