"""
Tests for Fiwano Bot Integration
=================================
"""

import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.utils import timezone

from .models import FiwanoInboundMessage, FiwanoConversation


class FiwanoWebhookTestCase(TestCase):
    """Test cases for Fiwano webhook endpoint."""
    
    def setUp(self):
        """Set up test client and mock configuration."""
        self.client = Client()
        self.webhook_secret = "test_webhook_secret_12345"
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'FIWANO_API_KEY': 'mip_live_test_key',
            'FIWANO_WEBHOOK_SECRET': self.webhook_secret,
            'FIWANO_API_BASE_URL': 'https://fiwano.com/api/v1',
        })
        self.env_patcher.start()
        
        # Reload settings to pick up new env vars
        from django.conf import settings
        settings.FIWANO_WEBHOOK_SECRET = self.webhook_secret
    
    def tearDown(self):
        """Clean up patches."""
        self.env_patcher.stop()
    
    def _create_signature(self, body: bytes) -> str:
        """Create valid HMAC signature for testing."""
        signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def test_invalid_signature(self):
        """Test that invalid signature returns 401."""
        payload = {
            "event": "message.received",
            "channel_id": "test_channel",
            "channel_type": "facebook",
            "data": {
                "message_id": "test_msg_1",
                "from": "test_user_123",
                "type": "text",
                "text": "Hello"
            }
        }
        body = json.dumps(payload).encode('utf-8')
        
        response = self.client.post(
            '/api/fiwano/webhook/',
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE='sha256=invalid_signature'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_missing_signature(self):
        """Test that missing signature returns 401."""
        payload = {
            "event": "message.received",
            "channel_id": "test_channel",
            "channel_type": "facebook",
            "data": {
                "message_id": "test_msg_2",
                "from": "test_user_123",
                "type": "text",
                "text": "Hello"
            }
        }
        body = json.dumps(payload).encode('utf-8')
        
        response = self.client.post(
            '/api/fiwano/webhook/',
            data=body,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    @patch('fiwano_bot.tasks.start_background_processing')
    def test_valid_text_message(self, mock_bg_processing):
        """Test valid text message creates record and returns 200."""
        payload = {
            "event": "message.received",
            "channel_id": "test_channel_123",
            "channel_type": "facebook",
            "timestamp": "2026-10-08T15:30:00Z",
            "data": {
                "message_id": "test_msg_valid_1",
                "from": "test_user_psid_123",
                "from_name": None,
                "type": "text",
                "text": "CST department er CI ke?"
            }
        }
        body = json.dumps(payload).encode('utf-8')
        signature = self._create_signature(body)
        
        response = self.client.post(
            '/api/fiwano/webhook/',
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        
        # Check message was saved
        msg = FiwanoInboundMessage.objects.get(message_id='test_msg_valid_1')
        self.assertEqual(msg.sender_id, 'test_user_psid_123')
        self.assertEqual(msg.message_text, 'CST department er CI ke?')
        self.assertEqual(msg.status, 'received')
        
        # Check background processing was started
        mock_bg_processing.assert_called_once()
    
    @patch('fiwano_bot.tasks.start_background_processing')
    def test_duplicate_message(self, mock_bg_processing):
        """Test duplicate message_id is handled correctly."""
        # Create existing message
        FiwanoInboundMessage.objects.create(
            message_id='duplicate_msg_123',
            channel_id='test_channel',
            channel_type='facebook',
            sender_id='test_user',
            message_type='text',
            message_text='First message',
            status='completed'
        )
        
        # Send duplicate
        payload = {
            "event": "message.received",
            "channel_id": "test_channel",
            "channel_type": "facebook",
            "data": {
                "message_id": "duplicate_msg_123",
                "from": "test_user",
                "type": "text",
                "text": "Duplicate message"
            }
        }
        body = json.dumps(payload).encode('utf-8')
        signature = self._create_signature(body)
        
        response = self.client.post(
            '/api/fiwano/webhook/',
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], 'duplicate')
        
        # Background processing should not be called
        mock_bg_processing.assert_not_called()
        
        # Original message should be unchanged
        msg = FiwanoInboundMessage.objects.get(message_id='duplicate_msg_123')
        self.assertEqual(msg.message_text, 'First message')
    
    def test_unsupported_event_type(self):
        """Test unsupported event types are ignored."""
        payload = {
            "event": "message.delivered",
            "channel_id": "test_channel",
            "channel_type": "facebook",
            "data": {
                "message_id": "test_msg_delivered",
                "status": "delivered"
            }
        }
        body = json.dumps(payload).encode('utf-8')
        signature = self._create_signature(body)
        
        response = self.client.post(
            '/api/fiwano/webhook/',
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ignored')
    
    @patch('fiwano_bot.tasks.start_background_processing')
    def test_unsupported_message_type(self, mock_bg_processing):
        """Test unsupported message types get fallback response."""
        payload = {
            "event": "message.received",
            "channel_id": "test_channel",
            "channel_type": "facebook",
            "data": {
                "message_id": "test_msg_image_1",
                "from": "test_user",
                "type": "image",
                "caption": "Check this photo"
            }
        }
        body = json.dumps(payload).encode('utf-8')
        signature = self._create_signature(body)
        
        response = self.client.post(
            '/api/fiwano/webhook/',
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Should create message record
        msg = FiwanoInboundMessage.objects.get(message_id='test_msg_image_1')
        self.assertEqual(msg.message_type, 'image')
        self.assertEqual(msg.status, 'completed')
        
        # Background processing called for sending fallback
        mock_bg_processing.assert_called_once()


class FiwanoServiceTestCase(TestCase):
    """Test cases for Fiwano service layer."""
    
    @patch('fiwano_bot.fiwano_service.requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message send."""
        from fiwano_bot.fiwano_service import send_message
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'message_id': 'fiwano_msg_123',
            'status': 'sent'
        }
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {'FIWANO_API_KEY': 'mip_live_test'}):
            result = send_message(
                channel_id='test_channel',
                recipient='test_user_psid',
                text='Test response'
            )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'fiwano_msg_123')
    
    @patch('fiwano_bot.fiwano_service.requests.post')
    def test_send_message_truncates_long_text(self, mock_post):
        """Test that long messages are truncated."""
        from fiwano_bot.fiwano_service import send_message
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'message_id': 'msg_123'}
        mock_post.return_value = mock_response
        
        long_text = "এটি একটি দীর্ঘ উত্তর।" * 300  # Over 2000 chars
        
        with patch.dict('os.environ', {'FIWANO_API_KEY': 'mip_live_test'}):
            result = send_message(
                channel_id='test_channel',
                recipient='test_user',
                text=long_text
            )
        
        # Check that sent text was truncated
        call_args = mock_post.call_args
        sent_text = call_args[1]['json']['text']
        self.assertLessEqual(len(sent_text), 2001)
        self.assertTrue(sent_text.endswith('…'))


class FiwanoConversationTestCase(TestCase):
    """Test cases for conversation management."""
    
    def test_add_message_to_conversation(self):
        """Test adding messages to conversation history."""
        conv = FiwanoConversation.objects.create(
            channel_id='test_channel',
            sender_id='test_user'
        )
        
        conv.add_message('human', 'Hello')
        conv.add_message('ai', 'Hi there!')
        
        self.assertEqual(conv.message_count, 2)
        self.assertEqual(len(conv.chat_history), 2)
        self.assertEqual(conv.chat_history[0]['role'], 'human')
        self.assertEqual(conv.chat_history[1]['role'], 'ai')
    
    def test_get_history_for_rag(self):
        """Test converting history to RAG format."""
        conv = FiwanoConversation.objects.create(
            channel_id='test_channel',
            sender_id='test_user'
        )
        
        conv.add_message('human', 'First question')
        conv.add_message('ai', 'First answer')
        conv.add_message('human', 'Second question')
        
        messages = conv.get_history_for_rag()
        
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0].content, 'First question')
        self.assertEqual(messages[1].content, 'First answer')
