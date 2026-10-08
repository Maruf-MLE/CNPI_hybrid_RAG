"""
Background Task Processing for Fiwano Bot
==========================================

Celery/RQ নেই বলে threading ব্যবহার করে background processing করা হচ্ছে।

WARNING: এটি development/small-scale production এর জন্য। 
High-traffic production এর জন্য Celery/RQ ব্যবহার করুন।
"""

import logging
import threading
from django.utils import timezone

logger = logging.getLogger(__name__)


def process_message_background(message_record):
    """
    Background thread-এ message process করে।
    
    এটি webhook acknowledgement এর পরে চলে, যাতে Fiwano 5-second timeout 
    এর মধ্যে 200 response পায়।
    
    Args:
        message_record: FiwanoInboundMessage instance
    """
    from .fiwano_service import send_message, FiwanoAPIError
    from rag_api.rag_engine import run_rag
    
    try:
        # Mark as processing
        message_record.mark_processing()
        
        # Get conversation history
        from .models import FiwanoConversation
        conversation, _ = FiwanoConversation.objects.get_or_create(
            channel_id=message_record.channel_id,
            sender_id=message_record.sender_id
        )
        
        # Add user message to history
        conversation.add_message('human', message_record.message_text)
        
        # Get chat history for RAG
        chat_history = conversation.get_history_for_rag()
        
        logger.info(
            f"Processing message {message_record.message_id} from {message_record.sender_id}"
        )
        
        # Call RAG system with 30-second timeout
        # (Fiwano তে 24-hour window আছে তাই আমরা একটু সময় নিতে পারি)
        result = run_rag(
            user_input=message_record.message_text,
            chat_history=chat_history
        )
        
        ai_response = result.get('final_answer', '')
        
        if not ai_response or not ai_response.strip():
            # Fallback response
            ai_response = "দুঃখিত, আপনার প্রশ্নের উত্তর দিতে পারছি না। আবার চেষ্টা করুন।"
        
        logger.info(f"RAG generated answer (length: {len(ai_response)})")
        
        # Send response via Fiwano
        send_result = send_message(
            channel_id=message_record.channel_id,
            recipient=message_record.sender_id,
            text=ai_response
        )
        
        # Add AI response to conversation history
        conversation.add_message('ai', ai_response)
        
        # Mark as completed
        message_record.mark_completed(ai_response)
        message_record.response_sent_at = timezone.now()
        message_record.save(update_fields=['response_sent_at'])
        
        logger.info(f"Message {message_record.message_id} processed successfully")
        
    except FiwanoAPIError as e:
        error_msg = f"Fiwano API error: {str(e)}"
        logger.error(f"Failed to process message {message_record.message_id}: {error_msg}")
        message_record.mark_failed(error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"Failed to process message {message_record.message_id}: {error_msg}")
        message_record.mark_failed(error_msg)


def start_background_processing(message_record):
    """
    একটি background thread শুরু করে message processing এর জন্য।
    
    Args:
        message_record: FiwanoInboundMessage instance
    """
    thread = threading.Thread(
        target=process_message_background,
        args=(message_record,),
        daemon=True,
        name=f"fiwano-{message_record.message_id[:8]}"
    )
    thread.start()
    
    logger.info(f"Started background thread for message {message_record.message_id}")
