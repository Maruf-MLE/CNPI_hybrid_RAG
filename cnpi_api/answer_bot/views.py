"""
answer_bot/views.py
===================
Facebook Messenger Webhook handler for Answer Bot — RAG-powered Q&A bot.

This bot ONLY answers questions using the RAG API. It does NOT save messages.

GET  /answer-webhook/  — Meta webhook verification (hub.challenge handshake)
POST /answer-webhook/  — Incoming message events from Facebook Messenger

Security: HMAC-SHA256 signature verification via X-Hub-Signature-256 header.
Processing: Done in a background thread so Meta gets a fast 200 OK.
Duplicate guard: ProcessedAnswerMessage model stores handled message IDs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import traceback
import uuid
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

import requests

from answer_bot.models import ProcessedAnswerMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers — config
# ---------------------------------------------------------------------------

def _get_setting(name: str) -> str:
    """Return a setting value, logging an error if it is missing."""
    value = getattr(settings, name, None) or ""
    if not value:
        logger.error("Missing required setting: %s", name)
    return value


# ---------------------------------------------------------------------------
# Helpers — Facebook Send API
# ---------------------------------------------------------------------------

def _send_message(psid: str, text: str) -> None:
    """Send a text message to a Messenger user via the Send API.

    Failures are logged but never raise, so the background thread stays alive.
    """
    token = _get_setting("ANSWER_BOT_PAGE_ACCESS_TOKEN")
    if not token:
        logger.error("ANSWER_BOT_PAGE_ACCESS_TOKEN not set — cannot send reply to PSID %s", psid)
        return

    url = "https://graph.facebook.com/v21.0/me/messages"
    payload = {
        "recipient": {"id": psid},
        "messaging_type": "RESPONSE",
        "message": {"text": text},
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.ok:
            logger.info("Send API success for PSID %s", psid)
        else:
            logger.error(
                "Send API error for PSID %s — status %s: %s",
                psid,
                resp.status_code,
                resp.text,
            )
    except Exception:
        logger.error("Send API exception for PSID %s:\n%s", psid, traceback.format_exc())


def _send_typing_on(psid: str) -> None:
    """Send typing indicator (typing_on) to show bot is processing."""
    token = _get_setting("ANSWER_BOT_PAGE_ACCESS_TOKEN")
    if not token:
        return

    url = "https://graph.facebook.com/v21.0/me/messages"
    payload = {
        "recipient": {"id": psid},
        "sender_action": "typing_on",
    }
    try:
        requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except Exception:
        logger.warning("Failed to send typing_on for PSID %s", psid)


# ---------------------------------------------------------------------------
# Helpers — signature verification
# ---------------------------------------------------------------------------

def _verify_signature(body: bytes, header_value: str) -> bool:
    """Return True if X-Hub-Signature-256 matches the HMAC-SHA256 of body."""
    app_secret = _get_setting("ANSWER_BOT_APP_SECRET")
    if not app_secret:
        return False  # already logged inside _get_setting

    if not header_value.startswith("sha256="):
        return False

    expected = header_value[len("sha256="):]
    computed = hmac.new(
        app_secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, expected)


# ---------------------------------------------------------------------------
# RAG API call
# ---------------------------------------------------------------------------

def _call_rag_api(question: str, session_id: str = None) -> dict[str, Any]:
    """
    Call the RAG API to get an answer.
    
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
            timeout=60,  # RAG can take time
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
# Background processor
# ---------------------------------------------------------------------------

def _process_messaging_event(psid: str, message: dict[str, Any]) -> None:
    """
    Called from a background thread for each valid messaging event.
    1. Extracts text from message
    2. Calls RAG API to get answer
    3. Replies to the user via Send API
    """
    text = message.get("text", "").strip()
    
    # Only handle text messages (no images/attachments in Answer Bot)
    if not text:
        _send_message(
            psid,
            "দয়া করে একটি প্রশ্ন লিখুন। 📝\n\nPlease send a text question.",
        )
        return
    
    # Send typing indicator
    _send_typing_on(psid)
    
    # Generate or use existing session_id per user
    session_id = f"answer_bot_{psid}"
    
    logger.info("Processing question from PSID %s: %s", psid, text[:50])
    
    # Call RAG API
    result = _call_rag_api(text, session_id)
    
    if "error" in result:
        _send_message(
            psid,
            f"❌ দুঃখিত, উত্তর দিতে সমস্যা হয়েছে।\n\nError: {result['error']}"
        )
        return
    
    answer = result.get("answer", "")
    answer_status = result.get("answer_status", "not_found")
    
    if not answer:
        _send_message(
            psid,
            "দুঃখিত, এই প্রশ্নের উত্তর আমি খুঁজে পাইনি। 😔\n\nSorry, I couldn't find an answer to this question."
        )
        return
    
    # Send answer
    _send_message(psid, answer)
    logger.info(
        "Sent answer to PSID %s — status=%s answer_len=%d",
        psid, answer_status, len(answer)
    )


def _handle_payload(body: dict[str, Any]) -> None:
    """
    Parse the webhook payload and dispatch each valid messaging event to
    _process_messaging_event.  Called inside a daemon background thread.
    """
    # Get allowed PSIDs (empty string means all users allowed)
    allowed_psids_raw = getattr(settings, "ANSWER_BOT_ALLOWED_PSIDS", "")
    allowed_psids: set[str] = (
        {p.strip() for p in allowed_psids_raw.split(",") if p.strip()}
        if allowed_psids_raw
        else set()
    )

    if body.get("object") != "page":
        logger.info("Ignoring non-page webhook object: %s", body.get("object"))
        return

    for entry in body.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender_id: str = messaging.get("sender", {}).get("id", "")
            message: dict[str, Any] = messaging.get("message", {})

            # Skip delivery / read receipts and other non-message events
            if not message:
                continue

            # Skip echo events (page's own outgoing messages reflected back)
            if message.get("is_echo"):
                continue

            # Authorization check — allow all if ANSWER_BOT_ALLOWED_PSIDS is empty
            if allowed_psids and sender_id not in allowed_psids:
                logger.info("Unauthorized PSID (not in whitelist): %s", sender_id)
                continue
            
            # Log allowed access
            if not allowed_psids:
                logger.info("Processing message from PSID %s (all users allowed)", sender_id)

            mid: str = message.get("mid", "")

            # Duplicate guard
            if mid:
                _, created = ProcessedAnswerMessage.objects.get_or_create(
                    mid=mid,
                    defaults={"psid": sender_id},
                )
                if not created:
                    logger.info("Duplicate mid ignored: %s", mid)
                    continue

            # Process in same thread (we're already in a background thread)
            try:
                _process_messaging_event(sender_id, message)
            except Exception:
                logger.error(
                    "Unhandled exception processing event for PSID %s:\n%s",
                    sender_id,
                    traceback.format_exc(),
                )


# ---------------------------------------------------------------------------
# Main webhook view
# ---------------------------------------------------------------------------

@csrf_exempt
def answer_webhook_view(request: HttpRequest) -> HttpResponse:
    """Single view handling both GET (verification) and POST (events)."""

    # ------------------------------------------------------------------ GET
    if request.method == "GET":
        mode = request.GET.get("hub.mode", "")
        token = request.GET.get("hub.verify_token", "")
        challenge = request.GET.get("hub.challenge", "")

        expected_token = _get_setting("ANSWER_BOT_VERIFY_TOKEN")

        logger.info(
            "Answer Bot Webhook GET — path=%s mode=%r has_token=%s has_challenge=%s",
            request.path,
            mode,
            bool(token),
            bool(challenge),
        )

        if mode == "subscribe" and token == expected_token and expected_token:
            logger.info("Answer Bot webhook verification successful")
            return HttpResponse(challenge, content_type="text/plain", status=200)

        logger.warning(
            "Answer Bot webhook verification failed — mode=%r token_match=%s",
            mode,
            token == expected_token,
        )
        return HttpResponse("Forbidden", status=403)

    # ------------------------------------------------------------------ POST
    if request.method == "POST":
        raw_body: bytes = request.body
        signature_header: str = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")

        logger.info(
            "Answer Bot Webhook POST — path=%s sig_present=%s body_len=%d",
            request.path,
            bool(signature_header),
            len(raw_body),
        )

        if not _verify_signature(raw_body, signature_header):
            logger.warning("Answer Bot webhook signature verification failed")
            return HttpResponse("Forbidden", status=403)

        # Parse JSON
        try:
            payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            logger.warning("Answer Bot webhook received invalid JSON body")
            return HttpResponse("Bad Request", status=400)

        # Immediately return 200 — process in background
        thread = threading.Thread(
            target=_handle_payload,
            args=(payload,),
            daemon=True,
            name="answer-bot-webhook-handler",
        )
        thread.start()

        return HttpResponse("EVENT_RECEIVED", content_type="text/plain", status=200)

    # ------------------------------------------------------------------ Other
    return HttpResponse("Method Not Allowed", status=405)
