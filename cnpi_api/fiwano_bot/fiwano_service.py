"""
Fiwano Service Layer
====================

Fiwano API এর সাথে communicate করার জন্য সব functions এখানে।
"""

import hmac
import hashlib
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class FiwanoAPIError(Exception):
    """Fiwano API error."""
    pass


def verify_webhook_signature(body: bytes, signature_header: str) -> bool:
    """
    Webhook signature verify করে (HMAC-SHA256)।
    
    Args:
        body: Raw request body bytes
        signature_header: X-Webhook-Signature header value
    
    Returns:
        True if valid, False otherwise
    """
    webhook_secret = settings.FIWANO_WEBHOOK_SECRET
    
    if not webhook_secret:
        logger.warning("FIWANO_WEBHOOK_SECRET not set - signature verification skipped")
        return True  # Allow in development
    
    if not signature_header:
        logger.warning("No X-Webhook-Signature header present")
        return False
    
    # Remove "sha256=" prefix if present
    signature = signature_header.replace("sha256=", "")
    
    # Compute expected signature
    expected = hmac.new(
        webhook_secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    is_valid = hmac.compare_digest(expected, signature)
    
    if not is_valid:
        logger.warning("Invalid webhook signature")
    
    return is_valid


def send_message(channel_id: str, recipient: str, text: str) -> dict:
    """
    Fiwano এর মাধ্যমে Facebook Messenger-এ message পাঠায়।
    
    Args:
        channel_id: Fiwano channel ID
        recipient: User's PSID
        text: Message text to send
    
    Returns:
        dict: API response
    
    Raises:
        FiwanoAPIError: If API call fails
    """
    api_key = settings.FIWANO_API_KEY
    base_url = settings.FIWANO_API_BASE_URL
    
    if not api_key:
        raise FiwanoAPIError("FIWANO_API_KEY not configured")
    
    # Facebook Messenger has 2000 character limit
    max_length = 2000
    if len(text) > max_length:
        # Truncate at sentence boundary
        text = _truncate_at_sentence(text, max_length)
    
    url = f"{base_url}/messages/send"
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }
    payload = {
        'channel_id': channel_id,
        'recipient': recipient,
        'text': text
    }
    
    try:
        logger.info(f"Sending message to {recipient} via Fiwano (length: {len(text)})")
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Check if send was successful
        if not result.get('success'):
            status = result.get('status', 'unknown')
            error_msg = f"Fiwano send failed with status: {status}"
            logger.error(error_msg)
            raise FiwanoAPIError(error_msg)
        
        logger.info(f"Message sent successfully: {result.get('message_id')}")
        return result
        
    except requests.exceptions.Timeout:
        error_msg = "Fiwano API timeout"
        logger.error(error_msg)
        raise FiwanoAPIError(error_msg)
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        
        if status_code == 401:
            error_msg = "Fiwano API authentication failed - check FIWANO_API_KEY"
        elif status_code == 402:
            error_msg = "Fiwano API payment required - check subscription"
        elif status_code == 404:
            error_msg = f"Fiwano channel not found: {channel_id}"
        elif status_code == 422:
            error_msg = f"Fiwano API validation error: {e.response.text}"
        elif status_code == 429:
            retry_after = e.response.headers.get('Retry-After', 'unknown')
            error_msg = f"Fiwano API rate limited - retry after {retry_after}s"
        elif status_code >= 500:
            error_msg = f"Fiwano API server error: {status_code}"
        else:
            error_msg = f"Fiwano API error: {status_code}"
        
        logger.error(f"{error_msg}: {e.response.text[:200]}")
        raise FiwanoAPIError(error_msg)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Fiwano API request failed: {str(e)}"
        logger.error(error_msg)
        raise FiwanoAPIError(error_msg)


def _truncate_at_sentence(text: str, max_length: int) -> str:
    """
    Text কে sentence boundary-তে কাটে।
    """
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    
    # Try to find sentence endings
    for ending in ['।', '.', '!', '?', '\n']:
        pos = truncated.rfind(ending)
        if pos > max_length * 0.7:  # At least 70% of max length
            return truncated[:pos + 1] + "…"
    
    # Fallback: cut at last space
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space] + "…"
    
    return truncated + "…"


def get_channels() -> list:
    """
    Fiwano থেকে সব channels list আনে (diagnostic/testing জন্য)।
    
    Returns:
        list: Channel list
    """
    api_key = settings.FIWANO_API_KEY
    base_url = settings.FIWANO_API_BASE_URL
    
    if not api_key:
        raise FiwanoAPIError("FIWANO_API_KEY not configured")
    
    url = f"{base_url}/channels"
    headers = {
        'X-API-Key': api_key
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result.get('channels', [])
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get channels: {e}")
        raise FiwanoAPIError(f"Failed to get channels: {e}")
