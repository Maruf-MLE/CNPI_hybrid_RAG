"""
ManyChat webhook endpoint for RAG integration.
"""

import asyncio
import hmac
import json
import logging
import os
import time
from collections import defaultdict
from functools import wraps
from threading import Lock

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment variables validation
# ---------------------------------------------------------------------------

def validate_env_variables():
    """Validate required environment variables at module load time."""
    if not os.getenv("MANYCHAT_API_KEY"):
        raise RuntimeError(
            "MANYCHAT_API_KEY environment variable is required but not set. "
            "Please set it before starting the application."
        )

# Validate on import (will crash at startup if missing)
validate_env_variables()

# Configuration
MANYCHAT_API_KEY = os.getenv("MANYCHAT_API_KEY")
RAG_TIMEOUT_SECONDS = int(os.getenv("RAG_TIMEOUT_SECONDS", "8"))
MAX_REPLY_CHARS = int(os.getenv("MAX_REPLY_CHARS", "2000"))
LOG_MANYCHAT_BODY = int(os.getenv("LOG_MANYCHAT_BODY", "0"))

# Debug logging counter
_debug_request_count = 0
_debug_lock = Lock()

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class SimpleRateLimiter:
    """In-memory rate limiter per user_id."""
    
    def __init__(self, max_requests=10, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = Lock()
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if request is allowed for this user_id."""
        now = time.time()
        with self.lock:
            # Clean old requests
            self.requests[user_id] = [
                ts for ts in self.requests[user_id]
                if now - ts < self.window_seconds
            ]
            
            # Check limit
            if len(self.requests[user_id]) >= self.max_requests:
                return False
            
            # Record this request
            self.requests[user_id].append(now)
            return True

rate_limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)

# ---------------------------------------------------------------------------
# Authentication helper
# ---------------------------------------------------------------------------

def verify_api_key(request):
    """Verify X-API-Key header using constant-time comparison."""
    provided_key = request.headers.get("X-API-Key", "")
    
    if not provided_key or not hmac.compare_digest(provided_key, MANYCHAT_API_KEY):
        return False
    return True

# ---------------------------------------------------------------------------
# Response formatter
# ---------------------------------------------------------------------------

def manychat_response(text: str) -> JsonResponse:
    """Format text as ManyChat v2 JSON response."""
    response_data = {
        "version": "v2",
        "content": {
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }
    }
    
    # Use ensure_ascii=False to preserve Bengali characters
    return JsonResponse(
        response_data,
        status=200,
        json_dumps_params={"ensure_ascii": False},
        content_type="application/json; charset=utf-8"
    )

# ---------------------------------------------------------------------------
# Text truncation helper
# ---------------------------------------------------------------------------

def truncate_text(text: str, max_chars: int) -> str:
    """
    Truncate text at sentence boundary if it exceeds max_chars.
    Adds '…' at the end if truncated.
    """
    if len(text) <= max_chars:
        return text
    
    # Try to find sentence ending near the limit
    truncated = text[:max_chars]
    
    # Look for sentence endings (। or . or newline)
    sentence_endings = ["।", ".", "\n"]
    last_sentence_pos = -1
    
    for ending in sentence_endings:
        pos = truncated.rfind(ending)
        if pos > last_sentence_pos:
            last_sentence_pos = pos
    
    if last_sentence_pos > 0:
        # Truncate at sentence boundary
        return truncated[:last_sentence_pos + 1] + "…"
    else:
        # No sentence boundary found, truncate at word boundary
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return truncated[:last_space] + "…"
        return truncated + "…"

# ---------------------------------------------------------------------------
# RAG caller with timeout
# ---------------------------------------------------------------------------

def call_rag_with_timeout(question: str, timeout_seconds: int) -> str:
    """
    Call the RAG pipeline with a timeout.
    Returns the answer or raises exception.
    """
    from rag_api.rag_engine import run_rag
    
    # Check if we need async approach
    # For Django sync views, we'll use a simple timeout wrapper
    try:
        # Import the compiled graph to check if it's ready
        from rag_api.rag_engine import _get_compiled_graph
        _get_compiled_graph()  # Ensure graph is compiled
        
        # Run RAG (this is synchronous)
        result = run_rag(user_input=question, chat_history=None)
        return result.get("final_answer", "")
    
    except Exception as e:
        logger.exception("RAG call failed")
        raise

# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(["POST"])
def manychat_webhook(request):
    """
    POST /manychat/webhook
    
    ManyChat Dynamic Block webhook that receives user messages and returns
    RAG answers in ManyChat v2 format.
    """
    global _debug_request_count
    
    # ---- Authentication ----
    if not verify_api_key(request):
        return JsonResponse(
            {"error": "unauthorized"},
            status=401
        )
    
    # ---- Parse JSON body ----
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Invalid JSON body: %s", str(e))
        return manychat_response(
            "আপনার প্রশ্নটা বুঝতে পারিনি, আবার লিখে পাঠান।"
        )
    
    # ---- Debug logging (first 5 requests only) ----
    if LOG_MANYCHAT_BODY:
        with _debug_lock:
            _debug_request_count += 1
            if _debug_request_count <= 5:
                # Truncate body for logging
                body_str = json.dumps(body, ensure_ascii=False)[:500]
                logger.info(
                    "ManyChat request #%d body (truncated): %s",
                    _debug_request_count,
                    body_str
                )
    
    # ---- Extract question from multiple possible fields ----
    question = (
        body.get("text") or
        body.get("last_input_text") or
        body.get("last_text_input") or
        ""
    ).strip()
    
    # ---- Extract user_id ----
    user_id = body.get("user_id") or body.get("id") or "unknown"
    
    # ---- Empty question check ----
    if not question:
        logger.info("Empty question from user %s", user_id)
        return manychat_response(
            "আপনার প্রশ্নটা বুঝতে পারিনি, আবার লিখে পাঠান।"
        )
    
    # ---- Rate limiting ----
    if not rate_limiter.is_allowed(user_id):
        logger.warning("Rate limit exceeded for user %s", user_id)
        return manychat_response(
            "একটু ধীরে, কিছুক্ষণ পরে আবার জিজ্ঞেস করুন।"
        )
    
    # ---- Call RAG with timeout ----
    logger.info("Processing question from user %s: %s", user_id, question[:100])
    
    try:
        # Use a simple threading approach for timeout
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(call_rag_with_timeout, question, RAG_TIMEOUT_SECONDS)
            
            try:
                answer = future.result(timeout=RAG_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                logger.warning(
                    "RAG timeout (%ds) for user %s",
                    RAG_TIMEOUT_SECONDS,
                    user_id
                )
                return manychat_response(
                    "দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করুন।"
                )
        
        # ---- Handle empty answer ----
        if not answer or not answer.strip():
            logger.warning("Empty answer from RAG for user %s", user_id)
            return manychat_response(
                "দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করুন।"
            )
        
        # ---- Truncate if needed ----
        answer = truncate_text(answer.strip(), MAX_REPLY_CHARS)
        
        logger.info("Sending answer to user %s (length: %d)", user_id, len(answer))
        return manychat_response(answer)
    
    except Exception as e:
        # Log the error but don't expose internals to user
        logger.exception("RAG pipeline error for user %s", user_id)
        return manychat_response(
            "দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করুন।"
        )

# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def health_check(request):
    """
    GET /health
    
    Simple health check endpoint for Render and uptime monitoring.
    No authentication required, does not touch RAG or database.
    """
    return JsonResponse({"status": "ok"}, status=200)
