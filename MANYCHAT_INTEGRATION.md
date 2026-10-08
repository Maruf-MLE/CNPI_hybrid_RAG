# ManyChat Integration Guide

## Overview

This guide explains how to integrate the CNPI RAG chatbot with ManyChat (Facebook Messenger) using Dynamic Blocks.

## Architecture

```
ManyChat Dynamic Block
    ↓ (POST request with user message)
    ↓
/manychat/webhook (this server)
    ↓ (calls RAG pipeline with 8s timeout)
    ↓
ManyChat v2 JSON Response
    ↓
User receives answer in Messenger
```

## Endpoints

### POST /manychat/webhook

ManyChat Dynamic Block webhook that receives user messages and returns RAG answers.

**Authentication**: Required `X-API-Key` header

**Request Body**:
```json
{
  "user_id": "123456",
  "text": "CST department er CI ke?",
  "last_input_text": "fallback field",
  "last_text_input": "another fallback field"
}
```

**Response** (ManyChat v2 format):
```json
{
  "version": "v2",
  "content": {
    "messages": [
      {
        "type": "text",
        "text": "CST Department-এর Chief Instructor হলেন..."
      }
    ]
  }
}
```

**Features**:
- Constant-time API key verification (HMAC)
- Multiple text field fallbacks (text → last_input_text → last_text_input)
- 8-second RAG timeout (configurable)
- Automatic answer truncation at 2000 characters (configurable)
- In-memory rate limiting (10 requests/minute per user)
- Bengali Unicode preservation
- Graceful error handling (always returns 200 except auth failures)
- Debug logging for first 5 requests (optional)

### GET /health

Simple health check endpoint for Render and uptime monitoring.

**Authentication**: None required

**Response**:
```json
{
  "status": "ok"
}
```

## Environment Variables

Add these to your `.env` file:

```bash
# Required
MANYCHAT_API_KEY=your_secure_api_key_here

# Optional
RAG_TIMEOUT_SECONDS=8        # RAG call timeout (default: 8)
MAX_REPLY_CHARS=2000         # Maximum reply length (default: 2000)
LOG_MANYCHAT_BODY=0          # Log first 5 request bodies (default: 0)
```

### Generate Secure API Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## ManyChat Setup

### 1. Create Dynamic Block

1. Go to your ManyChat flow
2. Add a "Dynamic Block" action
3. Configure the block:
   - **URL**: `https://your-app.onrender.com/manychat/webhook`
   - **Method**: POST
   - **Headers**: Add `X-API-Key: your_manychat_api_key`
   - **Body**: Select "User Input" or use custom JSON:
     ```json
     {
       "user_id": "{{user_id}}",
       "text": "{{last user input}}"
     }
     ```

### 2. Map Response

In ManyChat Dynamic Block settings:
- Response Type: JSON
- Message Path: `content.messages[0].text`

### 3. Test

Send a test message to your ManyChat bot and verify the response.

## Deployment to Render

### 1. Environment Variables

In Render Dashboard → Environment:

```
MANYCHAT_API_KEY=<your_secure_key>
RAG_TIMEOUT_SECONDS=8
MAX_REPLY_CHARS=2000
LOG_MANYCHAT_BODY=0

# Also ensure all other required env vars are set:
DATABASE_URL=<your_neon_postgres_url>
GROQ_API_KEY=<your_groq_key>
HF_TOKEN=<your_huggingface_token>
# ... etc (see .env.example for full list)
```

### 2. Build & Start Commands

**Build Command**:
```bash
cd cnpi_api && pip install -r requirements.txt
```

**Start Command**:
```bash
cd cnpi_api && gunicorn cnpi_api.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

### 3. Health Check

In Render Dashboard → Settings:
- Health Check Path: `/health`
- Health Check HTTP Method: GET

This ensures Render can monitor your service without authentication.

### 4. Startup Optimization

The RAG graph is compiled once at startup (not per request) to avoid cold start delays. Ensure:
- Worker count is appropriate for your RAM (2-4 workers recommended)
- Timeout is set to 120s to allow graph compilation
- Embedding model is loaded via HF API (not local) to save RAM

## Testing

### Run Tests Locally

```bash
cd cnpi_api
python manage.py test manychat_api.tests
```

### Test with curl

Replace `YOUR_API_KEY` and `YOUR_DOMAIN` with actual values:

```bash
# Test webhook (should return Bengali answer)
curl -X POST https://YOUR_DOMAIN/manychat/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"user_id":"test_user","text":"CST department er CI ke?"}'

# Expected response:
# {"version":"v2","content":{"messages":[{"type":"text","text":"CST Department-এর..."}]}}

# Test health check (no auth needed)
curl https://YOUR_DOMAIN/health

# Expected response:
# {"status":"ok"}

# Test invalid API key (should return 401)
curl -X POST https://YOUR_DOMAIN/manychat/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: wrong_key" \
  -d '{"user_id":"test","text":"test"}'

# Expected response:
# {"error":"unauthorized"}
```

## Rate Limiting

The webhook implements simple in-memory rate limiting:
- **Limit**: 10 requests per minute per user_id
- **Response when exceeded**: "একটু ধীরে, কিছুক্ষণ পরে আবার জিজ্ঞেস করুন।"
- **Status code**: 200 (to avoid ManyChat showing error)

For production with multiple workers, consider using Redis-based rate limiting.

## Error Handling

All errors return HTTP 200 (except auth failures) with user-friendly Bengali messages:

| Scenario | Response |
|----------|----------|
| Missing/invalid API key | HTTP 401: `{"error":"unauthorized"}` |
| Empty question | "আপনার প্রশ্নটা বুঝতে পারিনি, আবার লিখে পাঠান।" |
| Invalid JSON | "আপনার প্রশ্নটা বুঝতে পারিনি, আবার লিখে পাঠান।" |
| RAG timeout (>8s) | "দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করুন।" |
| RAG exception | "দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করুন।" |
| Rate limit exceeded | "একটু ধীরে, কিছুক্ষণ পরে আবার জিজ্ঞেস করুন।" |

Stack traces are logged server-side but never exposed to users.

## Monitoring

### Debug Logging

To debug ManyChat request format, temporarily enable logging:

```bash
LOG_MANYCHAT_BODY=1
```

This logs the first 5 request bodies (truncated to 500 chars). Check logs:

```bash
# Render logs
render logs -f

# Local logs
python manage.py runserver
```

### Metrics to Monitor

- Request rate per user
- RAG timeout frequency
- Average response time
- Error rates by type
- Answer truncation frequency

## Troubleshooting

### "unauthorized" error
- Check `X-API-Key` header matches `MANYCHAT_API_KEY` env var
- Verify header is included in ManyChat Dynamic Block settings

### Timeout errors
- Increase `RAG_TIMEOUT_SECONDS` (max 10, ManyChat limit)
- Check RAG pipeline performance
- Verify database connection is fast

### Bengali characters broken
- Verify `Content-Type: application/json; charset=utf-8` in response
- Check ManyChat is not re-encoding the response
- Test with curl to isolate issue

### Empty responses
- Check RAG pipeline is returning non-empty answers
- Verify `final_answer` field is populated
- Enable debug logging to see RAG output

### Rate limit too strict/loose
- Adjust logic in `cnpi_api/manychat_api/views.py`
- Default: 10 requests/minute per user
- Consider Redis for distributed rate limiting

## Security Notes

1. **Never commit** `.env` or expose `MANYCHAT_API_KEY`
2. Use **constant-time comparison** for API key (implemented via `hmac.compare_digest`)
3. **Validate all input** before passing to RAG
4. **Never expose** stack traces or internal errors to users
5. **Rate limiting** prevents abuse
6. Use **HTTPS** in production (Render provides this)

## Performance Tips

1. **Startup**: Graph compiles once at import time (not per request)
2. **Workers**: Use 2-4 gunicorn workers depending on RAM
3. **Embedding**: Use HF API instead of local models to save RAM
4. **Timeout**: 8 seconds balances quality and ManyChat's 10s limit
5. **Connection pooling**: Django CONN_MAX_AGE=600 reuses DB connections

## Files Modified/Created

- `cnpi_api/manychat_api/__init__.py` (new)
- `cnpi_api/manychat_api/apps.py` (new)
- `cnpi_api/manychat_api/views.py` (new)
- `cnpi_api/manychat_api/urls.py` (new)
- `cnpi_api/manychat_api/tests.py` (new)
- `cnpi_api/cnpi_api/settings.py` (modified: added manychat_api to INSTALLED_APPS)
- `cnpi_api/cnpi_api/urls.py` (modified: added manychat_api routes)
- `.env.example` (modified: added ManyChat env vars)

## Support

For issues or questions:
- Check Render logs: `render logs -f`
- Test locally first: `python manage.py runserver`
- Verify env vars are set correctly
- Test RAG pipeline independently: `POST /api/chat/`
