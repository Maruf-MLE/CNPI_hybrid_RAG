"""
Public cron endpoint for scheduled tasks.
"""
import logging
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def cron_job_endpoint(request):
    """
    Public endpoint that can be called by cron job every 5 minutes.
    
    This endpoint is CSRF-exempt and publicly accessible.
    Add your periodic task logic here.
    
    Returns:
        JSON response with status and timestamp
    """
    try:
        current_time = datetime.now().isoformat()
        logger.info(f"Cron job triggered at {current_time}")
        
        # ========================================
        # ADD YOUR CRON JOB LOGIC HERE
        # ========================================
        # Example tasks:
        # - Database cleanup
        # - Send scheduled notifications
        # - Update cache
        # - Sync external data
        # - Generate reports
        # ========================================
        
        # Example: Log the execution
        result = {
            "status": "success",
            "message": "Cron job executed successfully",
            "timestamp": current_time,
            "execution_count": 1
        }
        
        logger.info(f"Cron job completed: {result}")
        
        return JsonResponse(result, status=200)
        
    except Exception as e:
        logger.error(f"Cron job failed: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def cron_health_check(request):
    """
    Simple health check endpoint for monitoring.
    
    Returns:
        JSON response indicating service is alive
    """
    return JsonResponse({
        "status": "ok",
        "service": "cron_api",
        "timestamp": datetime.now().isoformat()
    }, status=200)
