# Answer Bot - RAG-Powered Q&A Messenger Bot

**Answer Bot** হলো একটি Facebook Messenger bot যা CNPI Hybrid RAG API ব্যবহার করে প্রশ্নের উত্তর দেয়।

## Features

✅ **RAG-powered answers** — সম্পূর্ণ knowledge base থেকে উত্তর খুঁজে বের করে  
✅ **Session-based chat** — multi-turn conversation support (প্রতি user-এর জন্য আলাদা session)  
✅ **Typing indicator** — উত্তর খুঁজার সময় "typing..." দেখায়  
✅ **Duplicate guard** — একই message দুইবার process হয় না  
✅ **HMAC signature verification** — Meta webhook security  
✅ **Background processing** — Meta-কে instant 200 OK দেয়, তারপর background-এ process করে  

## Differences from `messenger_bot`

| Feature | `messenger_bot` (Document Saver) | `answer_bot` (Q&A) |
|---------|----------------------------------|-------------------|
| Purpose | Save messages to database | Answer questions using RAG |
| Document saving | ✅ Yes | ❌ No |
| RAG API calls | ❌ No | ✅ Yes |
| Image support | ✅ OCR + caption | ❌ Text only |
| Commands | `/help`, `/priority`, `/stats` | None (pure Q&A) |
| Session management | No session | Per-user session ID |
| Webhook URL | `/webhook/` | `/answer-webhook/` |

## Setup

### 1. Create Facebook Page & App

1. Create a new Facebook Page for Answer Bot
2. Create a new Facebook App (or use existing)
3. Add Messenger Product to your app
4. Generate Page Access Token
5. Get App Secret from App Settings > Basic

### 2. Configure Environment Variables

Edit `G:\CNPI_Hybrid_RAG\.env`:

```bash
# Answer Bot Webhook (RAG-powered Q&A Bot)
ANSWER_BOT_VERIFY_TOKEN=your_unique_verify_token_here
ANSWER_BOT_APP_SECRET=your_facebook_app_secret_here
ANSWER_BOT_PAGE_ACCESS_TOKEN=your_page_access_token_here
ANSWER_BOT_ALLOWED_PSIDS=  # Leave empty to allow ALL users (no whitelist)
RAG_API_URL=https://cnpi-hybrid-rag-1.onrender.com/api/chat/
```

**Generate verify token:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### 3. Deploy & Configure Webhook

#### Local Testing (ngrok)
```bash
# Terminal 1: Start Django server
cd cnpi_api
python manage.py runserver

# Terminal 2: Start ngrok
ngrok http 8000
```

#### Production (Render)
```
Webhook URL: https://cnpi-hybrid-rag-1.onrender.com/answer-webhook/
```

#### Meta Webhook Configuration
1. Go to Meta App Dashboard > Messenger > Settings
2. **Callback URL:** `https://your-domain.com/answer-webhook/`
3. **Verify Token:** (same as `ANSWER_BOT_VERIFY_TOKEN`)
4. **Subscribed Fields:** Select `messages`, `messaging_postbacks`
5. Click "Verify and Save"

### 4. Test the Bot

Send a message to your Facebook Page:

```
User: CST department er CI ke?
Bot: CST Department-এর Chief Instructor হলেন মোঃ আব্দুল কাদের...
```

## API Flow

```
Facebook User
    ↓ sends message
Meta Webhook
    ↓ POST /answer-webhook/
answer_bot/views.py
    ↓ verify signature
    ↓ duplicate check (ProcessedAnswerMessage)
    ↓ extract text
    ↓ send typing_on
    ↓ call RAG API
RAG API (rag_api/views.py)
    ↓ run_rag(question, session_id)
Gemini LLM
    ↓ generate answer
answer_bot/views.py
    ↓ _send_message(answer)
Facebook User receives answer
```

## Session Management

- **Session ID format:** `answer_bot_{psid}`
- **Storage:** In-memory (chat_store.py in rag_api)
- **Expiry:** 1 hour of inactivity
- **Multi-turn support:** Yes (previous messages remembered)

Example:
```
User: CST er CI ke?
Bot: মোঃ আব্দুল কাদের

User: tar contact number ki?  ← Context retained
Bot: 01734567890
```

## Security

✅ **HMAC-SHA256 signature verification** — প্রতিটা request Meta থেকে এসেছে কিনা verify করে  
✅ **PSID whitelist** — শুধু allowed PSIDs-এর message process হয়  
✅ **Duplicate guard** — একই mid দুইবার process হয় না  
✅ **Timeout protection** — RAG API call 60s timeout  

## Logging

All logs go to console with `answer_bot` logger:

```python
logger.info("Processing question from PSID %s: %s", psid, text[:50])
logger.info("Sent answer to PSID %s — status=%s answer_len=%d", psid, answer_status, len(answer))
logger.error("RAG API error — status %s: %s", resp.status_code, resp.text)
```

Check logs in Render:
```
Dashboard > Logs > Filter: "answer_bot"
```

## Troubleshooting

### Bot not responding
1. Check webhook verification: GET `/answer-webhook/?hub.mode=subscribe&hub.verify_token=...&hub.challenge=123`
2. Check logs: `logger.info("Answer Bot Webhook POST — ...")`
3. Check RAG API: `curl -X POST http://127.0.0.1:8000/api/chat/ -H "Content-Type: application/json" -d '{"message":"test"}'`

### Signature verification failed
- Check `ANSWER_BOT_APP_SECRET` matches Meta App Settings > Basic > App Secret
- Check request has `X-Hub-Signature-256` header

### RAG API timeout
- Increase timeout in views.py: `timeout=60` → `timeout=120`
- Check RAG API is running: `curl http://127.0.0.1:8000/api/health/`

### Unauthorized PSID
- Add PSID to `.env`: `ANSWER_BOT_ALLOWED_PSIDS=123456789`
- Or leave empty to allow all: `ANSWER_BOT_ALLOWED_PSIDS=`

## Production Deployment

### Render Environment Variables
Add these in Render Dashboard > Environment:
```
ANSWER_BOT_VERIFY_TOKEN=...
ANSWER_BOT_APP_SECRET=...
ANSWER_BOT_PAGE_ACCESS_TOKEN=...
ANSWER_BOT_ALLOWED_PSIDS=
RAG_API_URL=https://cnpi-hybrid-rag-1.onrender.com/api/chat/
```

### Database Migration
```bash
python manage.py makemigrations answer_bot
python manage.py migrate answer_bot
```

### Test Webhook
```bash
curl -X GET "https://cnpi-hybrid-rag-1.onrender.com/answer-webhook/?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=123"
# Should return: 123
```

## File Structure

```
cnpi_api/answer_bot/
├── __init__.py
├── apps.py              # Django app config
├── models.py            # ProcessedAnswerMessage model
├── views.py             # Webhook handler + RAG API caller
├── urls.py              # /answer-webhook/ route
├── README.md            # This file
└── migrations/
    └── 0001_initial.py  # Database schema
```

## Related Files

- **RAG API:** `cnpi_api/rag_api/views.py` (POST `/api/chat/`)
- **RAG Engine:** `Cnpi_RAG/graph.py` (LangGraph pipeline)
- **Settings:** `cnpi_api/cnpi_api/settings.py` (env vars)
- **URL routing:** `cnpi_api/cnpi_api/urls.py` (includes answer_bot.urls)

## Comparison Table

| Bot Type | URL | Purpose | Storage | Commands |
|----------|-----|---------|---------|----------|
| **messenger_bot** | `/webhook/` | Save documents | PostgreSQL | `/help`, `/priority`, `/stats` |
| **answer_bot** | `/answer-webhook/` | Answer questions | Memory (session) | None |

---

**Created:** 2026-10-07  
**Version:** 1.0  
**Author:** CNPI RAG Team
