"""
messenger_bot/views.py
======================
Facebook Messenger Webhook handler for the CNPI RAG Django project.

GET  /webhook/  — Meta webhook verification (hub.challenge handshake)
POST /webhook/  — Incoming message events from Facebook Messenger

Security: HMAC-SHA256 signature verification via X-Hub-Signature-256 header.
Processing: Done in a background thread so Meta gets a fast 200 OK.
Duplicate guard: ProcessedMessage model stores handled message IDs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import traceback
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

import requests

from admin_panel import services as admin_services
from messenger_bot.models import ProcessedMessage

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
    token = _get_setting("FB_PAGE_ACCESS_TOKEN")
    if not token:
        logger.error("FB_PAGE_ACCESS_TOKEN not set — cannot send reply to PSID %s", psid)
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


# ---------------------------------------------------------------------------
# Helpers — signature verification
# ---------------------------------------------------------------------------

def _verify_signature(body: bytes, header_value: str) -> bool:
    """Return True if X-Hub-Signature-256 matches the HMAC-SHA256 of body."""
    app_secret = _get_setting("FB_APP_SECRET")
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
# Background processor
# ---------------------------------------------------------------------------

def _process_messaging_event(psid: str, message: dict[str, Any]) -> None:
    """
    Called from a background thread for each valid messaging event.
    1. Calls services.create_document() directly (no HTTP round-trip).
    2. Replies to the user via Send API.
    """
    text: str = message.get("text", "").strip()

    # No text content (image, sticker, etc.)
    if not text:
        _send_message(
            psid,
            "শুধু টেক্সট মেসেজ সমর্থিত। ছবি বা স্টিকার পাঠানো যাবে না।",
        )
        return

    # Call create_document directly — no HTTP overhead, no auth needed
    logger.info("Calling create_document for PSID %s, content length=%d", psid, len(text))
    try:
        result = admin_services.create_document(
            chunk_id=None,          # let the service decide or raise if required
            content=text,
            doc_type="notices",     # Messenger messages → notices table (auto chunk_id)
            source_file="messenger_bot",
        )
    except Exception:
        logger.error(
            "create_document raised an exception for PSID %s:\n%s",
            psid,
            traceback.format_exc(),
        )
        _send_message(psid, "❌ মেসেজ প্রসেস করা যায়নি। আবার চেষ্টা করুন।")
        return

    if "error" in result:
        logger.error(
            "create_document returned error for PSID %s: %s", psid, result["error"]
        )
        _send_message(psid, "❌ মেসেজ প্রসেস করা যায়নি। আবার চেষ্টা করুন।")
        return

    # Build success reply
    doc_id = result.get("doc_id", "")
    notice_id = result.get("notice_id", "")
    extra = ""
    if doc_id:
        extra += f" (doc_id: {doc_id})"
    if notice_id:
        extra += f" (notice_id: {notice_id})"

    _send_message(psid, f"✅ আপনার মেসেজ সফলভাবে সেভ হয়েছে।{extra}")
    logger.info("Successfully processed message for PSID %s%s", psid, extra)


def _handle_payload(body: dict[str, Any]) -> None:
    """
    Parse the webhook payload and dispatch each valid messaging event to
    _process_messaging_event.  Called inside a daemon background thread.
    """
    allowed_psids_raw = _get_setting("FB_ALLOWED_PSIDS")
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

            # Authorization check
            if sender_id not in allowed_psids:
                logger.info("Unauthorized PSID: %s", sender_id)
                continue

            mid: str = message.get("mid", "")

            # Duplicate guard
            if mid:
                _, created = ProcessedMessage.objects.get_or_create(
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
def webhook_view(request: HttpRequest) -> HttpResponse:
    """Single view handling both GET (verification) and POST (events)."""

    # ------------------------------------------------------------------ GET
    if request.method == "GET":
        mode = request.GET.get("hub.mode", "")
        token = request.GET.get("hub.verify_token", "")
        challenge = request.GET.get("hub.challenge", "")

        expected_token = _get_setting("FB_VERIFY_TOKEN")

        logger.info(
            "Webhook GET — path=%s mode=%r has_token=%s has_challenge=%s",
            request.path,
            mode,
            bool(token),
            bool(challenge),
        )

        if mode == "subscribe" and token == expected_token and expected_token:
            logger.info("Webhook verification successful")
            return HttpResponse(challenge, content_type="text/plain", status=200)

        logger.warning(
            "Webhook verification failed — mode=%r token_match=%s expected_len=%d got_len=%d",
            mode,
            token == expected_token,
            len(expected_token),
            len(token),
        )
        return HttpResponse("Forbidden", status=403)

    # ------------------------------------------------------------------ POST
    if request.method == "POST":
        raw_body: bytes = request.body
        signature_header: str = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")

        logger.info(
            "Webhook POST — path=%s sig_present=%s body_len=%d",
            request.path,
            bool(signature_header),
            len(raw_body),
        )

        if not _verify_signature(raw_body, signature_header):
            logger.warning("Webhook signature verification failed")
            return HttpResponse("Forbidden", status=403)

        # Parse JSON
        try:
            payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            logger.warning("Webhook received invalid JSON body")
            return HttpResponse("Bad Request", status=400)

        # Immediately return 200 — process in background
        thread = threading.Thread(
            target=_handle_payload,
            args=(payload,),
            daemon=True,
            name="messenger-webhook-handler",
        )
        thread.start()

        return HttpResponse("EVENT_RECEIVED", content_type="text/plain", status=200)

    # ------------------------------------------------------------------ Other
    return HttpResponse("Method Not Allowed", status=405)
