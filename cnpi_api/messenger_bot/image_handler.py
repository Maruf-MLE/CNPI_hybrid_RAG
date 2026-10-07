"""
messenger_bot/image_handler.py
===============================
Handle image attachments from Messenger:
1. Download image from Meta Graph API
2. Extract text via Gemini Vision API (existing OCR function)
3. Return extracted text
"""

from __future__ import annotations

import logging
import traceback

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def download_image_from_url(image_url: str, page_token: str) -> bytes | None:
    """Download image from Meta CDN using Page Access Token."""
    try:
        resp = requests.get(
            image_url,
            headers={"Authorization": f"Bearer {page_token}"},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.content
        logger.error("Image download failed: %s %s", resp.status_code, resp.text[:200])
        return None
    except Exception:
        logger.error("Image download exception:\n%s", traceback.format_exc())
        return None


def get_image_url_from_attachment(attachment: dict, page_token: str) -> str | None:
    """Extract image URL from Messenger attachment payload."""
    if attachment.get("type") != "image":
        return None
    
    payload = attachment.get("payload", {})
    # Try stickers first (they have a different structure)
    if payload.get("sticker_id"):
        return None  # Skip stickers
    
    # Regular image
    image_url = payload.get("url")
    if not image_url:
        return None
    
    return image_url


def process_image_message(message: dict, page_token: str) -> tuple[str | None, bytes | None]:
    """
    Process a message with image attachment.
    
    Returns:
        (caption_text, image_bytes) tuple
        - caption_text: user's text caption (if any)
        - image_bytes: downloaded image data (if successful)
    """
    caption = message.get("text", "").strip()
    attachments = message.get("attachments", [])
    
    if not attachments:
        return caption, None
    
    # Take first image attachment
    for attachment in attachments:
        image_url = get_image_url_from_attachment(attachment, page_token)
        if image_url:
            logger.info("Downloading image from: %s", image_url[:100])
            image_data = download_image_from_url(image_url, page_token)
            if image_data:
                logger.info("Downloaded %d bytes", len(image_data))
                return caption, image_data
    
    return caption, None
