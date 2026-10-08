"""
Fiwano Webhook Views
====================

Fiwano থেকে webhook events receive করে এবং process করে।
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import FiwanoInboundMessage
from .fiwano_service import verify_webhook_signature
from .tasks import start_background_processing

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def fiwano_webhook(request):
    """
    POST /api/fiwano/webhook/
    
    Fiwano থেকে message.received এবং অন্যান্য events receive করে।
    
    গুরুত্বপূর্ণ:
    - দ্রুত 200 return করতে হবে (5 seconds এর মধ্যে)
    - Signature verification অবশ্যই করতে হবে
    - Background processing করতে হবে
    - Duplicate message_id handle করতে হবে
    """
    
    # 1. Verify signature
    signature = request.headers.get('X-Webhook-Signature', '')
    if not verify_webhook_signature(request.body, signature):
        logger.warning("Invalid webhook signature received")
        return JsonResponse({'error': 'Invalid signature'}, status=401)
    
    # 2. Parse payload
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Invalid JSON payload: {e}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    event_type = payload.get('event')
    channel_id = payload.get('channel_id')
    channel_type = payload.get('channel_type')
    timestamp = payload.get('timestamp')
    data = payload.get('data', {})
    
    # 3. Log incoming webhook
    logger.info(
        f"Fiwano webhook received: event={event_type}, channel={channel_id}, "
        f"type={channel_type}"
    )
    
    # 4. Handle only message.received for now
    if event_type != 'message.received':
        logger.info(f"Ignoring event type: {event_type}")
        return JsonResponse({'status': 'ignored'}, status=200)
    
    # 5. Extract message data
    message_id = data.get('message_id')
    sender_id = data.get('from')  # PSID for Messenger
    sender_name = data.get('from_name')
    message_type = data.get('type', 'text')
    message_text = data.get('text', '')
    
    if not message_id or not sender_id:
        logger.error("Missing required fields: message_id or from")
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    
    # 6. Check for supported message type
    if message_type != 'text':
        logger.info(f"Unsupported message type: {message_type}")
        
        # Send a polite response for unsupported types
        unsupported_msg = FiwanoInboundMessage.objects.create(
            message_id=message_id,
            channel_id=channel_id,
            channel_type=channel_type,
            sender_id=sender_id,
            sender_name=sender_name,
            message_type=message_type,
            message_text='',
            status='completed',
            response_text='দুঃখিত, আমি শুধুমাত্র টেক্সট মেসেজ বুঝতে পারি।',
            raw_payload=payload,
            processed_at=timezone.now()
        )
        
        # Send unsupported response in background
        start_background_processing(unsupported_msg)
        
        return JsonResponse({'status': 'ok', 'message': 'unsupported_type'}, status=200)
    
    # 7. Check for empty text
    if not message_text or not message_text.strip():
        logger.warning("Empty message text received")
        return JsonResponse({'status': 'ok', 'message': 'empty_text'}, status=200)
    
    # 8. Idempotency check - check if message already exists
    existing = FiwanoInboundMessage.objects.filter(message_id=message_id).first()
    if existing:
        logger.info(f"Duplicate message_id: {message_id} - already processed")
        return JsonResponse({'status': 'ok', 'message': 'duplicate'}, status=200)
    
    # 9. Create message record
    try:
        message_record = FiwanoInboundMessage.objects.create(
            message_id=message_id,
            channel_id=channel_id,
            channel_type=channel_type,
            sender_id=sender_id,
            sender_name=sender_name or '',
            message_type=message_type,
            message_text=message_text,
            status='received',
            raw_payload=payload
        )
        
        logger.info(f"Message saved: {message_id}")
        
    except Exception as e:
        logger.exception(f"Failed to save message: {e}")
        return JsonResponse({'error': 'Database error'}, status=500)
    
    # 10. Start background processing
    start_background_processing(message_record)
    
    # 11. Return 200 immediately (within 5 seconds)
    return JsonResponse({'status': 'ok'}, status=200)


@require_http_methods(["GET"])
def health_check(request):
    """
    GET /api/fiwano/health/
    
    Simple health check endpoint.
    """
    return JsonResponse({'status': 'ok'}, status=200)


@require_http_methods(["GET"])
def webhook_test(request):
    """
    GET /api/fiwano/test/
    
    Test endpoint to verify Fiwano API connectivity.
    Protected endpoint - should add authentication in production.
    """
    from .fiwano_service import get_channels, FiwanoAPIError
    
    try:
        channels = get_channels()
        
        return JsonResponse({
            'status': 'ok',
            'channels_count': len(channels),
            'channels': [
                {
                    'id': ch.get('channel_id'),
                    'type': ch.get('channel_type'),
                    'is_active': ch.get('is_active'),
                }
                for ch in channels
            ]
        }, status=200)
        
    except FiwanoAPIError as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
