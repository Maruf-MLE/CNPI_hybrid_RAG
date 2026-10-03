"""
messenger_bot/tests.py
======================
Unit tests for the /webhook/ view.

Run locally (uses SQLite in-memory, no Postgres needed):
    python manage.py test messenger_bot --settings=messenger_bot.test_settings

Run on Render / CI (real DB available):
    python manage.py test messenger_bot
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings

from messenger_bot.views import webhook_view

# ---------------------------------------------------------------------------
# Common test settings
# ---------------------------------------------------------------------------

FAKE_VERIFY_TOKEN = "test_verify_token_abc"
FAKE_APP_SECRET = "test_app_secret_xyz"
FAKE_PAGE_TOKEN = "test_page_access_token_123"
FAKE_ALLOWED_PSIDS = "111111111,222222222"


def _make_signature(body: bytes, secret: str = FAKE_APP_SECRET) -> str:
    """Compute a valid X-Hub-Signature-256 header value."""
    digest = hmac.new(
        secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def _page_payload(psid: str, text: str | None, mid: str = "mid_001") -> dict:
    """Build a minimal Facebook page webhook payload."""
    message: dict = {"mid": mid}
    if text is not None:
        message["text"] = text
    return {
        "object": "page",
        "entry": [
            {
                "id": "PAGE_ID",
                "time": 1609459200,
                "messaging": [
                    {
                        "sender": {"id": psid},
                        "recipient": {"id": "PAGE_ID"},
                        "timestamp": 1609459200,
                        "message": message,
                    }
                ],
            }
        ],
    }


COMMON_SETTINGS = {
    "FB_VERIFY_TOKEN": FAKE_VERIFY_TOKEN,
    "FB_APP_SECRET": FAKE_APP_SECRET,
    "FB_PAGE_ACCESS_TOKEN": FAKE_PAGE_TOKEN,
    "FB_ALLOWED_PSIDS": FAKE_ALLOWED_PSIDS,
}


# ---------------------------------------------------------------------------
# GET verification tests
# ---------------------------------------------------------------------------


@override_settings(**COMMON_SETTINGS)
class WebhookVerificationTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def _get(self, mode: str, token: str, challenge: str = "CHALLENGE_CODE"):
        request = self.factory.get(
            "/webhook/",
            {
                "hub.mode": mode,
                "hub.verify_token": token,
                "hub.challenge": challenge,
            },
        )
        return webhook_view(request)

    def test_valid_verification_returns_challenge(self):
        response = self._get("subscribe", FAKE_VERIFY_TOKEN, "MY_CHALLENGE")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "MY_CHALLENGE")

    def test_wrong_token_returns_403(self):
        response = self._get("subscribe", "wrong_token", "MY_CHALLENGE")
        self.assertEqual(response.status_code, 403)

    def test_wrong_mode_returns_403(self):
        response = self._get("unsubscribe", FAKE_VERIFY_TOKEN, "MY_CHALLENGE")
        self.assertEqual(response.status_code, 403)

    def test_empty_token_returns_403(self):
        response = self._get("subscribe", "", "MY_CHALLENGE")
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# POST signature tests
# ---------------------------------------------------------------------------


@override_settings(**COMMON_SETTINGS)
class WebhookSignatureTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def _post(self, body: bytes, signature: str):
        request = self.factory.post(
            "/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        return webhook_view(request)

    def test_missing_signature_returns_403(self):
        body = b'{"object":"page","entry":[]}'
        request = self.factory.post(
            "/webhook/", data=body, content_type="application/json"
        )
        response = webhook_view(request)
        self.assertEqual(response.status_code, 403)

    def test_wrong_signature_returns_403(self):
        body = b'{"object":"page","entry":[]}'
        response = self._post(body, "sha256=badhash")
        self.assertEqual(response.status_code, 403)

    def test_valid_signature_returns_200(self):
        body = b'{"object":"page","entry":[]}'
        sig = _make_signature(body)
        response = self._post(body, sig)
        self.assertEqual(response.status_code, 200)

    def test_signature_without_prefix_returns_403(self):
        body = b'{"object":"page","entry":[]}'
        digest = hmac.new(
            FAKE_APP_SECRET.encode(), msg=body, digestmod=hashlib.sha256
        ).hexdigest()
        response = self._post(body, digest)  # no "sha256=" prefix
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# POST payload processing tests
# ---------------------------------------------------------------------------


@override_settings(**COMMON_SETTINGS)
class WebhookPayloadTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def _post_payload(self, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        sig = _make_signature(body)
        request = self.factory.post(
            "/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig,
        )
        return webhook_view(request)

    # -- Echo filter ---------------------------------------------------------

    @patch("messenger_bot.views._handle_payload")
    def test_returns_200_immediately(self, mock_handle):
        """POST always returns 200 quickly (background thread runs handle)."""
        payload = _page_payload("111111111", "Hello")
        response = self._post_payload(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "EVENT_RECEIVED")

    # The remaining tests patch _handle_payload to inspect what reaches it,
    # and also directly unit-test _handle_payload in isolation.

    def _run_handle_directly(self, payload: dict, mock_create=None, mock_send=None):
        """Run _handle_payload synchronously (bypasses thread) for unit testing."""
        from messenger_bot import views

        with patch.object(views, "_process_messaging_event") as mock_proc:
            views._handle_payload(payload)
            return mock_proc

    # -- Unauthorized PSID ---------------------------------------------------

    def test_unauthorized_psid_not_processed(self):
        payload = _page_payload("999999999", "Hello")  # not in allowed list
        from messenger_bot import views

        with patch.object(views, "_process_messaging_event") as mock_proc:
            views._handle_payload(payload)
            mock_proc.assert_not_called()

    # -- Echo event ----------------------------------------------------------

    def test_echo_event_not_processed(self):
        payload = {
            "object": "page",
            "entry": [
                {
                    "messaging": [
                        {
                            "sender": {"id": "111111111"},
                            "message": {
                                "mid": "mid_echo",
                                "is_echo": True,
                                "text": "echo text",
                            },
                        }
                    ]
                }
            ],
        }
        from messenger_bot import views

        with patch.object(views, "_process_messaging_event") as mock_proc:
            views._handle_payload(payload)
            mock_proc.assert_not_called()

    # -- Non-message event (delivery receipt) --------------------------------

    def test_delivery_event_not_processed(self):
        payload = {
            "object": "page",
            "entry": [
                {
                    "messaging": [
                        {
                            "sender": {"id": "111111111"},
                            "delivery": {"watermark": 1234567890},
                            # no "message" key
                        }
                    ]
                }
            ],
        }
        from messenger_bot import views

        with patch.object(views, "_process_messaging_event") as mock_proc:
            views._handle_payload(payload)
            mock_proc.assert_not_called()

    # -- Non-text message ----------------------------------------------------

    @patch("messenger_bot.views._send_message")
    @patch("messenger_bot.views.ProcessedMessage")
    def test_non_text_message_sends_info_reply(self, mock_model, mock_send):
        """Image/sticker messages (no 'text') should get an info reply."""
        mock_model.objects.get_or_create.return_value = (MagicMock(), True)
        from messenger_bot import views

        views._process_messaging_event("111111111", {"mid": "mid_img"})
        mock_send.assert_called_once()
        reply_text: str = mock_send.call_args[0][1]
        self.assertIn("টেক্সট", reply_text)

    # -- Duplicate mid -------------------------------------------------------

    def test_duplicate_mid_skipped(self):
        # First call: creates the DB record
        from messenger_bot import views

        payload = _page_payload("111111111", "first message", mid="mid_dup")
        with patch.object(views, "_process_messaging_event") as mock_proc:
            with patch(
                "messenger_bot.views.ProcessedMessage.objects.get_or_create"
            ) as mock_goc:
                # Simulate first call: created=True
                mock_goc.return_value = (MagicMock(), True)
                views._handle_payload(payload)
                self.assertEqual(mock_proc.call_count, 1)

                # Simulate second call: created=False (already exists)
                mock_goc.return_value = (MagicMock(), False)
                views._handle_payload(payload)
                self.assertEqual(mock_proc.call_count, 1)  # still 1

    # -- Authorized PSID, text message, endpoint success --------------------

    @patch("messenger_bot.views._send_message")
    @patch("messenger_bot.views.admin_services.create_document")
    def test_authorized_text_message_success(self, mock_create, mock_send):
        mock_create.return_value = {"doc_id": 42, "notice_id": 7}
        from messenger_bot import views

        views._process_messaging_event("111111111", {"mid": "mid_ok", "text": "Test document content here"})

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["content"], "Test document content here")

        mock_send.assert_called_once()
        reply: str = mock_send.call_args[0][1]
        self.assertIn("✅", reply)
        self.assertIn("42", reply)

    # -- Authorized PSID, text message, endpoint failure --------------------

    @patch("messenger_bot.views._send_message")
    @patch("messenger_bot.views.admin_services.create_document")
    def test_authorized_text_message_failure(self, mock_create, mock_send):
        mock_create.return_value = {"error": "DB write failed"}
        from messenger_bot import views

        views._process_messaging_event("111111111", {"mid": "mid_fail", "text": "Some text"})

        mock_send.assert_called_once()
        reply: str = mock_send.call_args[0][1]
        self.assertIn("❌", reply)

    # -- create_document raises an exception --------------------------------

    @patch("messenger_bot.views._send_message")
    @patch("messenger_bot.views.admin_services.create_document")
    def test_endpoint_exception_sends_failure_reply(self, mock_create, mock_send):
        mock_create.side_effect = RuntimeError("DB unavailable")
        from messenger_bot import views

        views._process_messaging_event("222222222", {"mid": "mid_exc", "text": "Some content"})

        mock_send.assert_called_once()
        reply: str = mock_send.call_args[0][1]
        self.assertIn("❌", reply)

    # -- Other HTTP methods --------------------------------------------------

    def test_put_method_returns_405(self):
        request = self.factory.put("/webhook/")
        response = webhook_view(request)
        self.assertEqual(response.status_code, 405)

    def test_delete_method_returns_405(self):
        request = self.factory.delete("/webhook/")
        response = webhook_view(request)
        self.assertEqual(response.status_code, 405)
