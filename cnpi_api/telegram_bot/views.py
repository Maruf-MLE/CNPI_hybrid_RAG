"""
telegram_bot/views.py
=====================
Telegram Bot Webhook handler for RAG-powered Q&A bot.

This bot answers questions using the RAG API, similar to answer_bot but for Telegram.

POST /telegram-webhook/<token>/  — Incoming updates from Telegram Bot API

Security: Token-based authentication via URL path (Telegram secret token).
Processing: Done in a background thread for fast response to Telegram.
Duplicate guard: ProcessedTelegramMessage model stores handled message IDs.

Official Telegram Bot API documentation:
https://core.telegram.org/bots/api
"""

from __future__ import annotations

import json
import logging
import threading
import traceback
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

import requests

from telegram_bot.models import ProcessedTelegramMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers — configuration
# ---------------------------------------------------------------------------

def _get_setting(name: str) -> str:
    """Return a setting value, logging an error if it is missing."""
    value = getattr(settings, name, None) or ""
    if not value:
        logger.error("Missing required setting: %s", name)
    return value


# ---------------------------------------------------------------------------
# Helpers — Telegram Bot API
# ---------------------------------------------------------------------------

def _send_message(chat_id: int, text: str, parse_mode: str = None) -> bool:
    """
    Send a text message to a Telegram chat via Bot API.
    
    Args:
        chat_id: Telegram chat ID
        text: Message text (max 4096 characters)
        parse_mode: Optional formatting mode ('Markdown', 'MarkdownV2', 'HTML')
    
    Returns:
        True if successful, False otherwise
    
    Failures are logged but never raise exceptions.
    """
    bot_token = _get_setting("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set — cannot send reply to chat %s", chat_id)
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Telegram has a 4096 character limit per message
    if len(text) > 4096:
        text = text[:4093] + "..."
    
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.ok:
            logger.info("Sent message to chat %s — success", chat_id)
            return True
        else:
            logger.error(
                "Telegram sendMessage error for chat %s — status %s: %s",
                chat_id,
                resp.status_code,
                resp.text,
            )
            return False
    except Exception:
        logger.error(
            "Telegram sendMessage exception for chat %s:\n%s",
            chat_id,
            traceback.format_exc(),
        )
        return False


def _send_chat_action(chat_id: int, action: str = "typing") -> None:
    """
    Send a chat action (typing indicator) to show bot is processing.
    
    Args:
        chat_id: Telegram chat ID
        action: Action type ('typing', 'upload_photo', 'record_video', etc.)
    
    Typing indicator lasts for 5 seconds or until a message is sent.
    """
    bot_token = _get_setting("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendChatAction"
    payload = {
        "chat_id": chat_id,
        "action": action,
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        logger.warning("Failed to send chat action for chat %s", chat_id)


# ---------------------------------------------------------------------------
# RAG API integration
# ---------------------------------------------------------------------------

def _call_rag_api(question: str, session_id: str = None) -> dict[str, Any]:
    """
    Call the RAG API to get an answer to a question.
    
    Args:
        question: User's question text
        session_id: Optional session ID for context retention
    
    Returns:
        {
            "answer": "...",
            "answer_status": "found" | "not_found",
            "session_id": "...",
            "error": "..." (if failed)
        }
    """
    rag_api_url = _get_setting("RAG_API_URL") or "http://127.0.0.1:8000/api/chat/"
    
    payload = {"message": question}
    if session_id:
        payload["session_id"] = session_id
    
    try:
        resp = requests.post(
            rag_api_url,
            json=payload,
            timeout=60,  # RAG processing can take time
        )
        if resp.ok:
            return resp.json()
        else:
            logger.error("RAG API error — status %s: %s", resp.status_code, resp.text)
            return {"error": f"RAG API returned {resp.status_code}"}
    except requests.Timeout:
        logger.error("RAG API timeout for question: %s", question[:50])
        return {"error": "RAG API timeout"}
    except Exception as e:
        logger.error("RAG API exception: %s", e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Message processing
# ---------------------------------------------------------------------------

def _process_message(message: dict[str, Any]) -> None:
    """
    Process a single Telegram message event.
    
    Called from a background thread for each valid message.
    1. Extracts text from message
    2. Calls RAG API to get answer
    3. Replies to the user via Telegram Bot API
    
    Args:
        message: Telegram message object from webhook update
    """
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user_id = message.get("from", {}).get("id")
    username = message.get("from", {}).get("username", "")
    text = message.get("text", "").strip()
    
    if not chat_id or not message_id or not user_id:
        logger.warning("Incomplete message data — skipping")
        return
    
    # Handle /start command
    if text == "/start":
        welcome_message = (
            "🙏 স্বাগতম! CNPI RAG Bot এ আপনাকে স্বাগতম।\n\n"
            "আমি CNPI সম্পর্কিত যেকোনো প্রশ্নের উত্তর দিতে পারি। "
            "আপনার প্রশ্ন লিখুন এবং আমি সেরা উত্তর খুঁজে দেওয়ার চেষ্টা করব।\n\n"
            "Welcome! I'm CNPI RAG Bot.\n\n"
            "I can answer questions about CNPI. "
            "Just type your question and I'll find the best answer."
        )
        _send_message(chat_id, welcome_message)
        return
    
    # Only handle text messages
    if not text:
        _send_message(
            chat_id,
            "দয়া করে একটি প্রশ্ন লিখুন। 📝\n\nPlease send a text question.",
        )
        return
    
    # Send typing indicator
    _send_chat_action(chat_id, "typing")
    
    # Generate session ID per user for context retention
    session_id = f"telegram_bot_{user_id}"
    
    logger.info(
        "Processing question from user %s (chat %s): %s",
        user_id,
        chat_id,
        text[:50],
    )
    
    # Call RAG API
    result = _call_rag_api(text, session_id)
    
    if "error" in result:
        _send_message(
            chat_id,
            f"❌ দুঃখিত, উত্তর দিতে সমস্যা হয়েছে।\n\nError: {result['error']}"
        )
        return
    
    answer = result.get("answer", "")
    answer_status = result.get("answer_status", "not_found")
    
    if not answer:
        _send_message(
            chat_id,
            "দুঃখিত, এই প্রশ্নের উত্তর আমি খুঁজে পাইনি। 😔\n\n"
            "Sorry, I couldn't find an answer to this question."
        )
        return
    
    # Send answer
    _send_message(chat_id, answer)
    logger.info(
        "Sent answer to user %s (chat %s) — status=%s answer_len=%d",
        user_id,
        chat_id,
        answer_status,
        len(answer)
    )


def _handle_update(update: dict[str, Any]) -> None:
    """
    Parse a Telegram webhook update and process valid messages.
    
    Called inside a daemon background thread.
    
    Args:
        update: Telegram Update object from webhook
    """
    # Get allowed user IDs (empty string means all users allowed)
    allowed_users_raw = getattr(settings, "TELEGRAM_BOT_ALLOWED_USERS", "")
    allowed_users: set[int] = (
        {int(uid.strip()) for uid in allowed_users_raw.split(",") if uid.strip()}
        if allowed_users_raw
        else set()
    )
    
    # Extract message from update
    message = update.get("message")
    if not message:
        # Could be edited_message, channel_post, etc. — we only handle regular messages
        logger.debug("No 'message' field in update — skipping")
        return
    
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user_id = message.get("from", {}).get("id")
    username = message.get("from", {}).get("username", "")
    
    if not chat_id or not message_id or not user_id:
        logger.warning("Incomplete message data — skipping")
        return
    
    # Authorization check — allow all if TELEGRAM_BOT_ALLOWED_USERS is empty
    if allowed_users and user_id not in allowed_users:
        logger.info("Unauthorized user (not in whitelist): %s", user_id)
        _send_message(
            chat_id,
            "দুঃখিত, আপনি এই bot ব্যবহার করার অনুমতি পাননি। 🚫\n\n"
            "Sorry, you are not authorized to use this bot."
        )
        return
    
    # Log allowed access
    if not allowed_users:
        logger.info("Processing message from user %s (all users allowed)", user_id)
    
    # Duplicate guard — check if we've already processed this message
    _, created = ProcessedTelegramMessage.objects.get_or_create(
        chat_id=chat_id,
        message_id=message_id,
        defaults={
            "user_id": user_id,
            "username": username,
        },
    )
    
    if not created:
        logger.info("Duplicate message ignored: chat=%s msg=%s", chat_id, message_id)
        return
    
    # Process the message
    try:
        _process_message(message)
    except Exception:
        logger.error(
            "Unhandled exception processing message from user %s:\n%s",
            user_id,
            traceback.format_exc(),
        )


# ---------------------------------------------------------------------------
# Webhook view
# ---------------------------------------------------------------------------

@csrf_exempt
def telegram_webhook_view(request: HttpRequest, token: str) -> HttpResponse:
    """
    Handle incoming Telegram webhook updates.
    
    URL pattern: /telegram-webhook/<token>/
    
    Security: Token in URL path must match TELEGRAM_WEBHOOK_SECRET_TOKEN.
    This prevents unauthorized webhook calls.
    
    Args:
        request: Django HTTP request
        token: Secret token from URL path
    
    Returns:
        200 OK for valid requests, 403 Forbidden for invalid tokens
    """
    
    # Only accept POST requests
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    # Verify secret token
    expected_token = _get_setting("TELEGRAM_WEBHOOK_SECRET_TOKEN")
    if not expected_token:
        logger.error("TELEGRAM_WEBHOOK_SECRET_TOKEN not configured")
        return JsonResponse({"error": "Server configuration error"}, status=500)
    
    if token != expected_token:
        logger.warning(
            "Invalid webhook token — expected=%s received=%s",
            expected_token[:8] + "...",
            token[:8] + "..." if len(token) >= 8 else token,
        )
        return JsonResponse({"error": "Forbidden"}, status=403)
    
    # Parse JSON body
    try:
        update: dict[str, Any] = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        logger.warning("Telegram webhook received invalid JSON body")
        return JsonResponse({"error": "Bad request"}, status=400)
    
    logger.info(
        "Telegram webhook update — update_id=%s",
        update.get("update_id", "unknown"),
    )
    
    # Process in background thread and return immediately
    thread = threading.Thread(
        target=_handle_update,
        args=(update,),
        daemon=True,
        name="telegram-webhook-handler",
    )
    thread.start()
    
    # Telegram expects 200 OK response
    return JsonResponse({"ok": True}, status=200)
