"""
Tests for ManyChat webhook integration.
"""

import json
import time
from unittest.mock import patch, MagicMock

import pytest
from django.test import TestCase, Client
from django.conf import settings


class ManyChatWebhookTestCase(TestCase):
    """Test cases for ManyChat webhook endpoint."""
    
    def setUp(self):
        """Set up test client and mock API key."""
        self.client = Client()
        self.api_key = "test_api_key_12345"
        
        # Mock the environment variable
        self.env_patcher = patch.dict('os.environ', {
            'MANYCHAT_API_KEY': self.api_key,
            'RAG_TIMEOUT_SECONDS': '8',
            'MAX_REPLY_CHARS': '2000',
            'LOG_MANYCHAT_BODY': '0',
        })
        self.env_patcher.start()
        
        # Reload the module to pick up new env vars
        import manychat_api.views
        from importlib import reload
        reload(manychat_api.views)
    
    def tearDown(self):
        """Clean up patches."""
        self.env_patcher.stop()
    
    def test_missing_api_key(self):
        """Test that request without X-API-Key returns 401."""
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({"text": "test question"}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['error'], 'unauthorized')
    
    def test_invalid_api_key(self):
        """Test that request with wrong X-API-Key returns 401."""
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({"text": "test question"}),
            content_type='application/json',
            HTTP_X_API_KEY='wrong_key'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['error'], 'unauthorized')
    
    @patch('manychat_api.views.call_rag_with_timeout')
    def test_valid_request_with_text_field(self, mock_rag):
        """Test valid request with 'text' field returns 200 and correct format."""
        mock_rag.return_value = "এটি একটি টেস্ট উত্তর।"
        
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({
                "user_id": "test_user_123",
                "text": "CST department er CI ke?"
            }),
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check ManyChat v2 format
        self.assertEqual(data['version'], 'v2')
        self.assertIn('content', data)
        self.assertIn('messages', data['content'])
        self.assertEqual(len(data['content']['messages']), 1)
        self.assertEqual(data['content']['messages'][0]['type'], 'text')
        self.assertEqual(data['content']['messages'][0]['text'], "এটি একটি টেস্ট উত্তর।")
    
    @patch('manychat_api.views.call_rag_with_timeout')
    def test_valid_request_with_last_input_text(self, mock_rag):
        """Test that 'last_input_text' field is also recognized."""
        mock_rag.return_value = "উত্তর পাওয়া গেছে।"
        
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({
                "user_id": "test_user_456",
                "last_input_text": "কলেজ কখন খুলবে?"
            }),
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['content']['messages'][0]['text'], "উত্তর পাওয়া গেছে।")
    
    @patch('manychat_api.views.call_rag_with_timeout')
    def test_valid_request_with_last_text_input(self, mock_rag):
        """Test that 'last_text_input' field is also recognized."""
        mock_rag.return_value = "শিক্ষকদের তালিকা পাওয়া গেছে।"
        
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({
                "id": "test_user_789",
                "last_text_input": "শিক্ষকদের নাম কি?"
            }),
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['content']['messages'][0]['text'], "শিক্ষকদের তালিকা পাওয়া গেছে।")
    
    def test_empty_question(self):
        """Test that empty question returns fallback message."""
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({
                "user_id": "test_user_empty",
                "text": ""
            }),
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("বুঝতে পারিনি", data['content']['messages'][0]['text'])
    
    def test_invalid_json(self):
        """Test that invalid JSON returns fallback message without crash."""
        response = self.client.post(
            '/manychat/webhook',
            data="not valid json",
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("বুঝতে পারিনি", data['content']['messages'][0]['text'])
    
    @patch('manychat_api.views.call_rag_with_timeout')
    def test_rag_timeout(self, mock_rag):
        """Test that RAG timeout returns fallback message."""
        # Simulate timeout by raising TimeoutError
        import concurrent.futures
        mock_rag.side_effect = concurrent.futures.TimeoutError()
        
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({
                "user_id": "test_timeout",
                "text": "slow question"
            }),
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("দুঃখিত", data['content']['messages'][0]['text'])
        self.assertIn("একটু পরে", data['content']['messages'][0]['text'])
    
    @patch('manychat_api.views.call_rag_with_timeout')
    def test_rag_exception(self, mock_rag):
        """Test that RAG exception returns fallback message without exposing trace."""
        mock_rag.side_effect = Exception("Internal RAG error")
        
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({
                "user_id": "test_error",
                "text": "error question"
            }),
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("দুঃখিত", data['content']['messages'][0]['text'])
        # Ensure no stack trace in response
        response_text = data['content']['messages'][0]['text']
        self.assertNotIn("Exception", response_text)
        self.assertNotIn("Traceback", response_text)
    
    @patch('manychat_api.views.call_rag_with_timeout')
    def test_long_answer_truncation(self, mock_rag):
        """Test that answers over 2000 chars are truncated at sentence boundary."""
        # Create a long answer
        long_answer = "এটি একটি দীর্ঘ উত্তর।" * 200  # Will exceed 2000 chars
        mock_rag.return_value = long_answer
        
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({
                "user_id": "test_long",
                "text": "long answer question"
            }),
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        answer = data['content']['messages'][0]['text']
        
        # Check that it's truncated
        self.assertLessEqual(len(answer), 2001)  # Allow 1 char for ellipsis
        # Check that ellipsis was added
        self.assertTrue(answer.endswith("…"))
    
    @patch('manychat_api.views.call_rag_with_timeout')
    def test_bengali_unicode_preserved(self, mock_rag):
        """Test that Bengali Unicode characters are preserved correctly."""
        bengali_answer = "আসসালামু আলাইকুম। কলেজটি ঢাকার মিরপুরে অবস্থিত।"
        mock_rag.return_value = bengali_answer
        
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({
                "user_id": "test_unicode",
                "text": "কলেজ কোথায়?"
            }),
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        # Check Content-Type header
        self.assertIn('application/json', response['Content-Type'])
        self.assertIn('charset=utf-8', response['Content-Type'])
        
        data = response.json()
        answer = data['content']['messages'][0]['text']
        
        # Verify Bengali characters are intact
        self.assertEqual(answer, bengali_answer)
        self.assertIn("আসসালামু", answer)
        self.assertIn("অবস্থিত", answer)
    
    @patch('manychat_api.views.call_rag_with_timeout')
    def test_rate_limiting(self, mock_rag):
        """Test that rate limiting works (10 requests per minute per user)."""
        mock_rag.return_value = "উত্তর"
        
        user_id = "test_rate_limit_user"
        
        # Make 10 successful requests
        for i in range(10):
            response = self.client.post(
                '/manychat/webhook',
                data=json.dumps({
                    "user_id": user_id,
                    "text": f"question {i}"
                }),
                content_type='application/json',
                HTTP_X_API_KEY=self.api_key
            )
            self.assertEqual(response.status_code, 200)
        
        # 11th request should be rate limited
        response = self.client.post(
            '/manychat/webhook',
            data=json.dumps({
                "user_id": user_id,
                "text": "question 11"
            }),
            content_type='application/json',
            HTTP_X_API_KEY=self.api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("একটু ধীরে", data['content']['messages'][0]['text'])


class HealthCheckTestCase(TestCase):
    """Test cases for health check endpoint."""
    
    def test_health_check_no_auth(self):
        """Test that health check works without authentication."""
        response = self.client.get('/health')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
