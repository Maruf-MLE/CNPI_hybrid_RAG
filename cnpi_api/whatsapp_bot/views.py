"""
WhatsApp Webhook Views

Handles incoming webhook requests from WhatsApp Business API including:
- Webhook verification (GET)
- Message events (POST)
- Security validation
- Background processing coordination
"""

import json
import logging
import threading
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .whatsapp_service import get_whatsapp_service
from .models import WhatsAppMessage
from .tasks import process_whatsapp_message


logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    Main webhook endpoint for WhatsApp Business API.
    
    GET: Webhook verification during setup
    POST: Incoming message events
    """
    if request.method == "GET":
        return _handle_webhook_verification(request)
    else:  # POST
        return _handle_webhook_event(request)


def _handle_webhook_verification(request):
    """
    Handle webhook verification challenge from WhatsApp.
    
    Called when setting up the webhook in WhatsApp Business settings.
    WhatsApp sends: mode=subscribe, verify_token=<your_token>, challenge=<random_string>
    You must respond with the challenge value to complete verification.
    """
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')
    
    logger.info(f"Webhook verification request: mode={mode}")
    
    whatsapp_service = get_whatsapp_service()
    verified_challenge = whatsapp_service.verify_webhook_token(mode, token, challenge)
    
    if verified_challenge:
        logger.info("Webhook verification successful")
        return HttpResponse(verified_challenge, content_type='text/plain')
    
    logger.error("Webhook verification failed")
    return HttpResponse("Verification failed", status=403)


def _handle_webhook_event(request):
    """
    Handle incoming webhook events from WhatsApp.
    
    Process messages asynchronously to ensure fast response (<5 seconds).
    WhatsApp requires 200 OK within 5 seconds or will retry the webhook.
    """
    try:
        # Get raw body for signature verification
        body = request.body
        signature_header = request.headers.get('X-Hub-Signature-256', '')
        
        # Verify webhook signature
        whatsapp_service = get_whatsapp_service()
        if not whatsapp_service.verify_webhook_signature(body, signature_header):
            logger.error("Invalid webhook signature")
            return HttpResponse("Invalid signature", status=403)
        
        # Parse JSON payload
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {str(e)}")
            return HttpResponse("Invalid JSON", status=400)
        
        logger.info(f"Received webhook event: {json.dumps(payload, indent=2)}")
        
        # Extract messages from payload
        messages = _extract_messages_from_payload(payload)
        
        if not messages:
            logger.info("No messages to process in webhook event")
            return HttpResponse("EVENT_RECEIVED", status=200)
        
        # Process each message in background thread
        for message_data in messages:
            _process_message_async(message_data, payload)
        
        # Return 200 OK immediately (within 5 seconds)
        return HttpResponse("EVENT_RECEIVED", status=200)
        
    except Exception as e:
        logger.error(f"Error handling webhook event: {str(e)}", exc_info=True)
        # Still return 200 to prevent WhatsApp retries
        return HttpResponse("EVENT_RECEIVED", status=200)


def _extract_messages_from_payload(payload):
    """
    Extract message data from WhatsApp webhook payload.
    
    WhatsApp payload structure:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "..."},
                    "contacts": [{"profile": {"name": "..."}, "wa_id": "..."}],
                    "messages": [{
                        "from": "PHONE_NUMBER",
                        "id": "MESSAGE_ID",
                        "timestamp": "TIMESTAMP",
                        "type": "text",
                        "text": {"body": "MESSAGE_TEXT"}
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    """
    messages = []
    
    try:
        entries = payload.get('entry', [])
        
        for entry in entries:
            changes = entry.get('changes', [])
            
            for change in changes:
                value = change.get('value', {})
                
                # Only process message events
                if change.get('field') != 'messages':
                    continue
                
                # Extract metadata
                metadata = value.get('metadata', {})
                contacts = value.get('contacts', [])
                
                # Extract messages
                webhook_messages = value.get('messages', [])
                
                for msg in webhook_messages:
                    message_type = msg.get('type', 'text')
                    
                    # Only process text messages for now
                    if message_type != 'text':
                        logger.info(f"Skipping non-text message type: {message_type}")
                        continue
                    
                    # Get sender info
                    sender_phone = msg.get('from', '')
                    sender_name = None
                    
                    # Try to get sender name from contacts
                    for contact in contacts:
                        if contact.get('wa_id') == sender_phone:
                            sender_name = contact.get('profile', {}).get('name')
                            break
                    
                    # Extract message content
                    message_data = {
                        'message_id': msg.get('id'),
                        'phone_number': sender_phone,
                        'sender_name': sender_name,
                        'message_text': msg.get('text', {}).get('body', ''),
                        'message_type': message_type,
                        'timestamp': msg.get('timestamp'),
                    }
                    
                    messages.append(message_data)
        
        return messages
        
    except Exception as e:
        logger.error(f"Error extracting messages from payload: {str(e)}", exc_info=True)
        return []


def _process_message_async(message_data, raw_payload):
    """
    Process message in background thread to ensure fast webhook response.
    
    Creates a WhatsAppMessage record and spawns a background thread
    for processing to avoid blocking the webhook response.
    """
    try:
        message_id = message_data['message_id']
        
        # Check for duplicate message (idempotency)
        if WhatsAppMessage.objects.filter(message_id=message_id).exists():
            logger.info(f"Duplicate message {message_id}, skipping")
            return
        
        # Create message record
        message = WhatsAppMessage.objects.create(
            message_id=message_id,
            phone_number=message_data['phone_number'],
            sender_name=message_data.get('sender_name', ''),
            message_text=message_data['message_text'],
            message_type=message_data['message_type'],
            status=WhatsAppMessage.STATUS_RECEIVED,
            raw_payload=raw_payload
        )
        
        logger.info(f"Created message record: {message_id}")
        
        # Process in background thread
        thread = threading.Thread(
            target=process_whatsapp_message,
            args=(message.id,),
            daemon=True,
            name=f"whatsapp-{message_id[:8]}"
        )
        thread.start()
        
        logger.info(f"Started background processing for message {message_id}")
        
    except Exception as e:
        logger.error(f"Error creating message record: {str(e)}", exc_info=True)


@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for monitoring.
    
    Returns service status and basic configuration info.
    """
    whatsapp_service = get_whatsapp_service()
    
    status = {
        "status": "healthy",
        "service": "whatsapp_bot",
        "timestamp": timezone.now().isoformat(),
        "configuration": {
            "api_token_configured": bool(whatsapp_service.api_token),
            "phone_number_configured": bool(whatsapp_service.phone_number_id),
            "webhook_secret_configured": bool(whatsapp_service.webhook_secret),
        }
    }
    
    # Check database connectivity
    try:
        message_count = WhatsAppMessage.objects.count()
        status["database"] = {
            "status": "connected",
            "total_messages": message_count
        }
    except Exception as e:
        status["database"] = {
            "status": "error",
            "error": str(e)
        }
        status["status"] = "degraded"
    
    http_status = 200 if status["status"] == "healthy" else 503
    return JsonResponse(status, status=http_status)


@require_http_methods(["GET"])
def stats(request):
    """
    Statistics endpoint for monitoring message processing.
    
    Returns counts by status and recent activity.
    """
    try:
        stats_data = {
            "total_messages": WhatsAppMessage.objects.count(),
            "by_status": {
                "received": WhatsAppMessage.objects.filter(status=WhatsAppMessage.STATUS_RECEIVED).count(),
                "processing": WhatsAppMessage.objects.filter(status=WhatsAppMessage.STATUS_PROCESSING).count(),
                "completed": WhatsAppMessage.objects.filter(status=WhatsAppMessage.STATUS_COMPLETED).count(),
                "failed": WhatsAppMessage.objects.filter(status=WhatsAppMessage.STATUS_FAILED).count(),
            },
            "recent_messages": WhatsAppMessage.objects.order_by('-received_at')[:10].values(
                'message_id', 'phone_number', 'status', 'received_at'
            )
        }
        
        return JsonResponse(stats_data)
        
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)
