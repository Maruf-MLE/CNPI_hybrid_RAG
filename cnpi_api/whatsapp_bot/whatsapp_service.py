"""
WhatsApp API Service Layer

Handles all communication with WhatsApp Business API including:
- Sending messages
- Webhook signature verification
- API authentication
- Error handling and retries
"""

import os
import hmac
import hashlib
import logging
import requests
from typing import Dict, Optional, Any
from django.conf import settings


logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Service class for WhatsApp Business API integration.
    
    Provides methods for sending messages, verifying webhooks,
    and handling API communication with proper error handling.
    """
    
    def __init__(self):
        """Initialize WhatsApp service with configuration from environment."""
        self.api_token = os.getenv('WHATSAPP_API_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.webhook_verify_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN')
        self.webhook_secret = os.getenv('WHATSAPP_WEBHOOK_SECRET')
        self.api_version = os.getenv('WHATSAPP_API_VERSION', 'v18.0')
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # Validate required configuration
        if not self.api_token:
            logger.error("WHATSAPP_API_TOKEN not configured")
        if not self.phone_number_id:
            logger.error("WHATSAPP_PHONE_NUMBER_ID not configured")
    
    def send_message(
        self,
        to_phone_number: str,
        message_text: str,
        preview_url: bool = False
    ) -> Dict[str, Any]:
        """
        Send a text message to a WhatsApp user.
        
        Args:
            to_phone_number: Recipient's phone number with country code
            message_text: Message content to send
            preview_url: Whether to show URL previews (default: False)
        
        Returns:
            Dict containing API response with message_id and status
        
        Raises:
            Exception: If API call fails after retries
        """
        if not self.api_token or not self.phone_number_id:
            raise ValueError("WhatsApp API credentials not configured")
        
        # Truncate message if too long (WhatsApp limit is 4096 chars)
        if len(message_text) > 4096:
            message_text = message_text[:4093] + "..."
            logger.warning(f"Message truncated to 4096 characters for {to_phone_number}")
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone_number,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message_text
            }
        }
        
        try:
            logger.info(f"Sending message to {to_phone_number}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Message sent successfully: {result.get('messages', [{}])[0].get('id')}")
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout sending message to {to_phone_number}")
            raise Exception("WhatsApp API request timed out")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to {to_phone_number}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"API error details: {error_data}")
                except:
                    logger.error(f"API error status: {e.response.status_code}")
            raise Exception(f"Failed to send WhatsApp message: {str(e)}")
    
    def send_typing_indicator(self, to_phone_number: str, typing: bool = True):
        """
        Send typing indicator to show bot is processing.
        
        Args:
            to_phone_number: Recipient's phone number
            typing: True to show typing, False to clear (default: True)
        
        Note: This is optional and may not be supported by all WhatsApp Business APIs
        """
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_phone_number,
                "type": "typing" if typing else "read"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            # Don't fail if typing indicator fails
            logger.debug(f"Could not send typing indicator: {str(e)}")
    
    def verify_webhook_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """
        Verify webhook request signature using HMAC-SHA256.
        
        Args:
            payload_body: Raw request body as bytes
            signature_header: X-Hub-Signature-256 header value
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("WHATSAPP_WEBHOOK_SECRET not configured, skipping signature verification")
            return True
        
        try:
            # Extract signature from header (format: "sha256=<signature>")
            if not signature_header.startswith('sha256='):
                logger.error("Invalid signature format")
                return False
            
            expected_signature = signature_header.split('sha256=')[1]
            
            # Compute HMAC-SHA256
            computed_signature = hmac.new(
                key=self.webhook_secret.encode('utf-8'),
                msg=payload_body,
                digestmod=hashlib.sha256
            ).hexdigest()
            
            # Constant-time comparison to prevent timing attacks
            is_valid = hmac.compare_digest(computed_signature, expected_signature)
            
            if not is_valid:
                logger.error("Webhook signature verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    def verify_webhook_token(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook subscription request from WhatsApp.
        
        This is called during webhook setup to verify your endpoint.
        
        Args:
            mode: Should be "subscribe"
            token: Verify token sent by WhatsApp
            challenge: Challenge string to echo back
        
        Returns:
            Challenge string if verification passes, None otherwise
        """
        if not self.webhook_verify_token:
            logger.error("WHATSAPP_WEBHOOK_VERIFY_TOKEN not configured")
            return None
        
        if mode == "subscribe" and token == self.webhook_verify_token:
            logger.info("Webhook verification successful")
            return challenge
        
        logger.error(f"Webhook verification failed: mode={mode}, token_match={token == self.webhook_verify_token}")
        return None
    
    def mark_message_as_read(self, message_id: str) -> bool:
        """
        Mark a message as read (optional feature).
        
        Args:
            message_id: WhatsApp message ID to mark as read
        
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.debug(f"Could not mark message as read: {str(e)}")
            return False


# Singleton instance
_whatsapp_service = None


def get_whatsapp_service() -> WhatsAppService:
    """
    Get singleton instance of WhatsAppService.
    
    Returns:
        WhatsAppService instance
    """
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service
