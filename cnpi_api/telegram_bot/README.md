# Telegram Bot - RAG-Powered Q&A Bot

**Telegram Bot** হলো একটি professional Telegram bot যা CNPI Hybrid RAG API ব্যবহার করে প্রশ্নের উত্তর দেয়।

## Features

✅ **RAG-powered answers** — সম্পূর্ণ knowledge base থেকে উত্তর খুঁজে বের করে  
✅ **Session-based chat** — multi-turn conversation support (প্রতি user-এর জন্য আলাদা session)  
✅ **Typing indicator** — উত্তর খুঁজার সময় "typing..." দেখায়  
✅ **Duplicate guard** — একই message দুইবার process হয় না  
✅ **Token-based security** — webhook URL-এ secret token দিয়ে secure  
✅ **Background processing** — Telegram-কে instant 200 OK দেয়, তারপর background-এ process করে  
✅ **/start command** — welcome message with bot introduction  
✅ **User whitelist** — শুধু allowed users-এর message process করা (optional)  

## Architecture

```
Telegram User
    ↓ sends message
Telegram Bot API
    ↓ POST /telegram-webhook/<secret-token>/
telegram_bot/views.py
    ↓ verify token
    ↓ duplicate check (ProcessedTelegramMessage)
    ↓ extract text
    ↓ send typing action
    ↓ call RAG API
RAG API (rag_api/views.py)
    ↓ run_rag(question, session_id)
Gemini LLM
    ↓ generate answer
telegram_bot/views.py
    ↓ _send_message(answer)
Telegram User receives answer
```

## Differences from Other Bots

| Feature | `messenger_bot` | `answer_bot` | `whatsapp_bot` | `telegram_bot` |
|---------|----------------|--------------|----------------|----------------|
| Platform | Facebook | Facebook | WhatsApp | Telegram |
| Purpose | Save docs | Q&A | Q&A | Q&A |
| RAG API | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Webhook Auth | HMAC signature | HMAC signature | Token verify | URL token |
| Session ID | No | Per PSID | Per phone | Per user_id |
| Commands | `/help`, `/stats` | None | None | `/start` |

## Quick Start

### 1. Create Telegram Bot with BotFather

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow instructions:
   - Enter bot name (e.g., "CNPI RAG Bot")
   - Enter bot username (e.g., "cnpi_rag_bot")
4. **Copy the bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Keep this token secure — you'll need it for `.env` configuration

### 2. Configure Environment Variables

Edit `G:\CNPI_Hybrid_RAG\.env`:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET_TOKEN=your_random_secret_token_here
TELEGRAM_BOT_ALLOWED_USERS=  # Leave empty to allow ALL users

RAG_API_URL=http://127.0.0.1:8000/api/chat/
```

**Generate secret token:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Find your Telegram user ID** (for whitelist):
- Message **@userinfobot** on Telegram
- It will reply with your user ID (e.g., `123456789`)
- Add to `TELEGRAM_BOT_ALLOWED_USERS` if you want to restrict access

### 3. Run Database Migration

```bash
cd G:\CNPI_Hybrid_RAG\cnpi_api
python manage.py makemigrations telegram_bot
python manage.py migrate telegram_bot
```

### 4. Set Up Webhook

#### Local Testing with ngrok

```bash
# Terminal 1: Start Django server
cd cnpi_api
python manage.py runserver

# Terminal 2: Start ngrok
ngrok http 8000
# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

#### Set Telegram Webhook

Replace values with your own:

```bash
# Set webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/telegram-webhook/<YOUR_SECRET_TOKEN>/"
  }'

# Example with ngrok:
curl -X POST "https://api.telegram.org/bot123456789:ABCdefGHI/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://abc123.ngrok.io/telegram-webhook/your_secret_token/"
  }'
```

**PowerShell command:**
```powershell
$botToken = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
$secretToken = "your_random_secret_token_here"
$webhookUrl = "https://abc123.ngrok.io/telegram-webhook/$secretToken/"

Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{url=$webhookUrl} | ConvertTo-Json)
```

#### Verify Webhook

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

**Expected response:**
```json
{
  "ok": true,
  "result": {
    "url": "https://your-domain.com/telegram-webhook/your_secret_token/",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### 5. Test the Bot

1. Open Telegram and search for your bot username (e.g., `@cnpi_rag_bot`)
2. Click "Start" or send `/start`
3. Bot should reply with welcome message
4. Ask a question:

```
User: CST department er CI ke?
Bot: CST Department-এর Chief Instructor হলেন মোঃ আব্দুল কাদের...
```

## Production Deployment (Render)

### Environment Variables on Render

Add these in **Render Dashboard > Environment**:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET_TOKEN=your_random_secret_token_here
TELEGRAM_BOT_ALLOWED_USERS=
RAG_API_URL=https://cnpi-hybrid-rag-1.onrender.com/api/chat/
```

### Set Production Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://cnpi-hybrid-rag-1.onrender.com/telegram-webhook/<YOUR_SECRET_TOKEN>/"
  }'
```

## Session Management

- **Session ID format:** `telegram_bot_{user_id}`
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

✅ **URL token authentication** — শুধু valid secret token দিয়ে webhook call করা যায়  
✅ **User whitelist (optional)** — শুধু allowed user IDs-এর message process হয়  
✅ **Duplicate guard** — একই message দুইবার process হয় না  
✅ **Timeout protection** — RAG API call 60s timeout  
✅ **4096 character limit** — Telegram message limit automatically enforced  

## Commands

- `/start` — Welcome message and bot introduction

## Logging

All logs go to console with `telegram_bot` logger:

```python
logger.info("Processing question from user %s (chat %s): %s", user_id, chat_id, text[:50])
logger.info("Sent answer to user %s — status=%s answer_len=%d", user_id, answer_status, len(answer))
logger.error("RAG API error — status %s: %s", resp.status_code, resp.text)
```

Check logs in Render:
```
Dashboard > Logs > Filter: "telegram_bot"
```

## Troubleshooting

### Bot not responding

1. **Check webhook status:**
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```
   
2. **Check Django logs:**
   ```
   Telegram webhook update — update_id=...
   Processing question from user...
   ```

3. **Check RAG API:**
   ```bash
   curl -X POST http://127.0.0.1:8000/api/chat/ \
     -H "Content-Type: application/json" \
     -d '{"message":"test"}'
   ```

### Invalid token error

- Check `TELEGRAM_BOT_TOKEN` in `.env` matches the token from BotFather
- Token format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### Webhook forbidden (403)

- Check `TELEGRAM_WEBHOOK_SECRET_TOKEN` in `.env`
- Verify webhook URL includes correct secret token:
  ```
  https://your-domain.com/telegram-webhook/<SECRET_TOKEN>/
  ```

### Unauthorized user

- Add user ID to `.env`:
  ```
  TELEGRAM_BOT_ALLOWED_USERS=123456789,987654321
  ```
- Or leave empty to allow all:
  ```
  TELEGRAM_BOT_ALLOWED_USERS=
  ```

### RAG API timeout

- Increase timeout in `views.py`: `timeout=60` → `timeout=120`
- Check RAG API is running:
  ```bash
  curl http://127.0.0.1:8000/api/health/
  ```

### Message too long

- Telegram has 4096 character limit per message
- Bot automatically truncates to 4093 chars + "..."

## Bot Commands for BotFather

To set bot description and commands in BotFather:

```
/setdescription
CNPI RAG Bot - আমি CNPI সম্পর্কিত যেকোনো প্রশ্নের উত্তর দিতে পারি। I can answer questions about CNPI.

/setabouttext
RAG-powered Q&A bot for CNPI

/setcommands
start - Start the bot and see welcome message
```

## File Structure

```
cnpi_api/telegram_bot/
├── __init__.py                  # Django app initialization
├── apps.py                      # Django app config
├── models.py                    # ProcessedTelegramMessage model
├── views.py                     # Webhook handler + RAG integration
├── urls.py                      # /telegram-webhook/<token>/ route
├── README.md                    # This file
├── TELEGRAM_SETUP_GUIDE.md      # Step-by-step setup guide
└── migrations/
    └── 0001_initial.py          # Database schema
```

## Related Files

- **RAG API:** `cnpi_api/rag_api/views.py` (POST `/api/chat/`)
- **RAG Engine:** `Cnpi_RAG/graph.py` (LangGraph pipeline)
- **Settings:** `cnpi_api/cnpi_api/settings.py` (env vars + logging)
- **URL routing:** `cnpi_api/cnpi_api/urls.py` (includes telegram_bot.urls)

## Comparison with Other Bots

| Bot Type | Platform | Webhook URL | Auth Method | Purpose |
|----------|----------|-------------|-------------|---------|
| **messenger_bot** | Facebook | `/webhook/` | HMAC-SHA256 | Save documents |
| **answer_bot** | Facebook | `/answer-webhook/` | HMAC-SHA256 | Q&A (RAG) |
| **whatsapp_bot** | WhatsApp | `/api/whatsapp/webhook/` | Token verify | Q&A (RAG) |
| **telegram_bot** | Telegram | `/telegram-webhook/<token>/` | URL token | Q&A (RAG) |

## Best Practices

1. **Never commit tokens** — always use `.env` file (add to `.gitignore`)
2. **Use strong secret tokens** — generate with `secrets.token_urlsafe(32)`
3. **Monitor logs** — check for errors and unauthorized access attempts
4. **Test locally first** — use ngrok before deploying to production
5. **Set user whitelist** — for production, limit to authorized users
6. **Regular backups** — backup database with processed message records

## API Reference

### Telegram Bot API

- **Documentation:** https://core.telegram.org/bots/api
- **setWebhook:** https://core.telegram.org/bots/api#setwebhook
- **sendMessage:** https://core.telegram.org/bots/api#sendmessage
- **sendChatAction:** https://core.telegram.org/bots/api#sendchataction

### RAG API

**Endpoint:** `POST /api/chat/`

**Request:**
```json
{
  "message": "CST department er CI ke?",
  "session_id": "telegram_bot_123456789"
}
```

**Response:**
```json
{
  "answer": "CST Department-এর Chief Instructor হলেন মোঃ আব্দুল কাদের...",
  "answer_status": "found",
  "session_id": "telegram_bot_123456789"
}
```

---

**Created:** 2026-10-18  
**Version:** 1.0  
**Author:** CNPI RAG Team
