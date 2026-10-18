"""
Background Task Processing for WhatsApp Bot

Handles asynchronous message processing including:
- RAG API integration
- Conversation history management
- Response generation and sending
- Error handling and retry logic
"""

import os
import logging
import requests
from typing import Dict, Any, Optional

from .models import WhatsAppMessage, WhatsAppConversation
from .whatsapp_service import get_whatsapp_service


logger = logging.getLogger(__name__)


# RAG API configuration
RAG_API_URL = os.getenv('RAG_API_URL', 'http://127.0.0.1:8000/api/chat/')
RAG_API_TIMEOUT = int(os.getenv('RAG_API_TIMEOUT', '60'))


def process_whatsapp_message(message_id: int):
    """
    Main background task for processing WhatsApp messages.
    
    This function runs in a background thread and handles:
    1. Fetching the message from database
    2. Getting/creating conversation history
    3. Calling RAG API with context
    4. Sending response back to user
    5. Updating conversation history
    6. Error handling
    
    Args:
        message_id: Database ID of WhatsAppMessage to process
    """
    message = None
    
    try:
        # Fetch message from database
        message = WhatsAppMessage.objects.get(id=message_id)
        
        logger.info(f"Processing message {message.message_id} from {message.phone_number}")
        
        # Mark as processing
        message.mark_processing()
        
        # Get WhatsApp service
        whatsapp_service = get_whatsapp_service()
        
        # Optional: Send typing indicator
        try:
            whatsapp_service.send_typing_indicator(message.phone_number, typing=True)
        except Exception as e:
            logger.debug(f"Could not send typing indicator: {str(e)}")
        
        # Get or create conversation
        conversation, created = WhatsAppConversation.objects.get_or_create(
            phone_number=message.phone_number,
            defaults={
                'user_name': message.sender_name or '',
                'chat_history': [],
                'message_count': 0
            }
        )
        
        if created:
            logger.info(f"Created new conversation for {message.phone_number}")
        
        # Update user name if available
        if message.sender_name and not conversation.user_name:
            conversation.user_name = message.sender_name
            conversation.save(update_fields=['user_name'])
        
        # Get conversation history for RAG
        chat_history = conversation.get_history_for_rag(max_messages=10)
        
        # Call RAG API
        rag_response = call_rag_api(
            user_input=message.message_text,
            chat_history=chat_history,
            session_id=f"whatsapp_{message.phone_number}"
        )
        
        # Extract answer from RAG response
        answer_text = rag_response.get('final_answer') or rag_response.get('answer', '')
        
        if not answer_text:
            logger.warning("Empty response from RAG API")
            answer_text = "দুঃখিত, আমি এই মুহূর্তে আপনার প্রশ্নের উত্তর দিতে পারছি না। অনুগ্রহ করে আবার চেষ্টা করুন।"
        
        # Send response to user
        whatsapp_service.send_message(
            to_phone_number=message.phone_number,
            message_text=answer_text,
            preview_url=True
        )
        
        logger.info(f"Response sent to {message.phone_number}")
        
        # Update message status
        message.mark_completed(answer_text)
        
        # Update conversation history
        conversation.add_user_message(message.message_text)
        conversation.add_bot_message(answer_text)
        
        # Clean old history to prevent unlimited growth
        conversation.clear_old_history(keep_last=20)
        
        logger.info(f"Successfully processed message {message.message_id}")
        
    except WhatsAppMessage.DoesNotExist:
        logger.error(f"Message with id {message_id} not found")
        
    except Exception as e:
        logger.error(f"Error processing message {message_id}: {str(e)}", exc_info=True)
        
        # Mark message as failed
        if message:
            error_msg = f"{type(e).__name__}: {str(e)}"
            message.mark_failed(error_msg)
            
            # Try to send error message to user (optional)
            try:
                whatsapp_service = get_whatsapp_service()
                error_response = "দুঃখিত, আপনার বার্তা প্রক্রিয়া করতে একটি সমস্যা হয়েছে। অনুগ্রহ করে কিছুক্ষণ পরে আবার চেষ্টা করুন।"
                whatsapp_service.send_message(
                    to_phone_number=message.phone_number,
                    message_text=error_response
                )
            except Exception as send_error:
                logger.error(f"Could not send error message to user: {str(send_error)}")


def call_rag_api(
    user_input: str,
    chat_history: list,
    session_id: str,
    timeout: int = RAG_API_TIMEOUT
) -> Dict[str, Any]:
    """
    Call the RAG API to get answer for user's question.
    
    Args:
        user_input: User's message/question
        chat_history: List of LangChain message objects for context
        session_id: Unique session identifier
        timeout: Request timeout in seconds
    
    Returns:
        Dict containing RAG API response with 'final_answer' or 'answer'
    
    Raises:
        Exception: If API call fails
    """
    try:
        logger.info(f"Calling RAG API for session {session_id}")
        
        # Format chat history for API
        formatted_history = []
        for msg in chat_history:
            msg_type = type(msg).__name__
            formatted_history.append({
                'type': 'human' if 'Human' in msg_type else 'ai',
                'content': msg.content
            })
        
        # Prepare API payload
        payload = {
            'question': user_input,
            'chat_history': formatted_history,
            'session_id': session_id
        }
        
        # Call RAG API
        response = requests.post(
            RAG_API_URL,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"RAG API response received for session {session_id}")
        
        return result
        
    except requests.exceptions.Timeout:
        logger.error(f"RAG API timeout after {timeout} seconds")
        raise Exception("RAG API request timed out")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"RAG API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                logger.error(f"RAG API error details: {error_data}")
            except:
                logger.error(f"RAG API status code: {e.response.status_code}")
        raise Exception(f"Failed to call RAG API: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error calling RAG API: {str(e)}", exc_info=True)
        raise


def retry_failed_messages(limit: int = 10):
    """
    Retry processing of failed messages.
    
    This can be called manually or scheduled as a periodic task
    to retry messages that failed due to temporary errors.
    
    Args:
        limit: Maximum number of failed messages to retry
    """
    try:
        failed_messages = WhatsAppMessage.objects.filter(
            status=WhatsAppMessage.STATUS_FAILED
        ).order_by('-received_at')[:limit]
        
        count = failed_messages.count()
        
        if count == 0:
            logger.info("No failed messages to retry")
            return
        
        logger.info(f"Retrying {count} failed messages")
        
        for message in failed_messages:
            # Reset status to received
            message.status = WhatsAppMessage.STATUS_RECEIVED
            message.error_message = None
            message.save(update_fields=['status', 'error_message'])
            
            # Process again
            process_whatsapp_message(message.id)
        
        logger.info(f"Initiated retry for {count} messages")
        
    except Exception as e:
        logger.error(f"Error retrying failed messages: {str(e)}", exc_info=True)


def get_conversation_summary(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Get conversation summary for a user.
    
    Useful for debugging and monitoring.
    
    Args:
        phone_number: User's phone number
    
    Returns:
        Dict with conversation info or None if not found
    """
    try:
        conversation = WhatsAppConversation.objects.get(phone_number=phone_number)
        
        return {
            'phone_number': conversation.phone_number,
            'user_name': conversation.user_name,
            'message_count': conversation.message_count,
            'last_message_at': conversation.last_message_at.isoformat(),
            'history_length': len(conversation.chat_history),
            'recent_messages': conversation.chat_history[-5:] if conversation.chat_history else []
        }
        
    except WhatsAppConversation.DoesNotExist:
        logger.warning(f"No conversation found for {phone_number}")
        return None
    except Exception as e:
        logger.error(f"Error getting conversation summary: {str(e)}")
        return None
