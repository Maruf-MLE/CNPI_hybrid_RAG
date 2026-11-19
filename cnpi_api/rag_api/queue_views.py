"""
Additional API endpoint for queue status checking.
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .queue_manager import get_queue_manager
from .serializers import QueueStatusSerializer


@api_view(["GET"])
def queue_status_view(request):
    """GET /api/queue/status/?session_id=xxx
    
    Check current queue status for a session.
    
    Response:
        {
            "is_active": false,
            "in_queue": true,
            "queue_position": 2,
            "estimated_wait_seconds": 45,
            "active_count": 3,
            "queue_length": 5,
            "max_active": 3
        }
    """
    session_id = request.query_params.get("session_id", "")
    
    if not session_id:
        return Response(
            {"error": "session_id query parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    queue_manager = get_queue_manager()
    status_data = queue_manager.get_status(session_id)
    
    serializer = QueueStatusSerializer(status_data)
    return Response(serializer.data, status=status.HTTP_200_OK)
