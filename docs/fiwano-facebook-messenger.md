# Fiwano Facebook Messenger Integration

এই ডকুমেন্টে Fiwano API ব্যবহার করে Facebook Messenger ইন্টিগ্রেশনের বিস্তারিত বর্ণনা আছে।

## সূচিপত্র

1. [আর্কিটেকচার](#আর্কিটেকচার)
2. [কীভাবে কাজ করে](#কীভাবে-কাজ-করে)
3. [সেটআপ ও কনফিগারেশন](#সেটআপ-ও-কনফিগারেশন)
4. [Fiwano চ্যানেল কানেক্ট করা](#fiwano-চ্যানেল-কানেক্ট-করা)
5. [ডিপ্লয়মেন্ট](#ডিপ্লয়মেন্ট)
6. [টেস্টিং](#টেস্টিং)
7. [ট্রাবলশুটিং](#ট্রাবলশুটিং)

---

## আর্কিটেকচার

```
Facebook User
    ↓
Facebook Page
    ↓
Fiwano Platform
    ↓
Django Webhook (POST /api/fiwano/webhook/)
    ↓
Signature Verification (HMAC-SHA256)
    ↓
Fast 200 Response (< 5 seconds)
    ↓
Background Thread Processing
    ↓
Existing RAG System (run_rag)
    ↓
Fiwano Send API
    ↓
Facebook Messenger
    ↓
Facebook User
```

### মূল বৈশিষ্ট্য

- **সম্পূর্ণ Webhook-ভিত্তিক**: Meta App নিজে তৈরি করার দরকার নেই
- **Signature Verification**: HMAC-SHA256 দিয়ে সুরক্ষিত
- **Background Processing**: Threading ব্যবহার করে দ্রুত acknowledgement
- **Idempotency**: Duplicate message protection
- **Conversation History**: প্রতিটি user-এর জন্য আলাদা chat history
- **বিদ্যমান RAG System**: কোনো পরিবর্তন ছাড়াই ব্যবহার

---

## কীভাবে কাজ করে

### 1. Webhook Request

যখন কোনো user আপনার Facebook Page-এ message পাঠায়:

1. Fiwano webhook event পাঠায় আপনার Django endpoint-এ
2. Signature verify করা হয় (HMAC-SHA256)
3. Message database-এ save হয়
4. তৎক্ষণাৎ 200 response দেওয়া হয় (5 seconds-এর মধ্যে)
5. Background thread শুরু হয়

### 2. Background Processing

Background thread-এ:

1. Conversation history load করা হয়
2. User message history-তে add হয়
3. RAG system call করা হয় (30-second timeout)
4. AI response generate হয়
5. Fiwano Send API দিয়ে user-কে পাঠানো হয়
6. AI response history-তে save হয়

### 3. Idempotency

Duplicate message handling:

- প্রতিটি message-এর unique `message_id` আছে
- Database-এ unique constraint দিয়ে duplicate block করা
- Retry করলে একই message আবার process হয় না

---

## সেটআপ ও কনফিগারেশন

### 1. Environment Variables

`.env` ফাইলে যোগ করুন:

```bash
# Fiwano API Configuration
FIWANO_API_KEY=mip_live_xxxxxxxxxxxxxxxxxxxxxxxxx
FIWANO_WEBHOOK_SECRET=your_webhook_secret_here
FIWANO_API_BASE_URL=https://fiwano.com/api/v1
```

**কোথায় পাবেন:**

- `FIWANO_API_KEY`: Fiwano Portal → API Keys → Create Key
  - শুরু হয় `mip_live_` দিয়ে
  - একবার দেখানো হয়, তাই সংরক্ষণ করুন
- `FIWANO_WEBHOOK_SECRET`: Channel configure করার সময় set করবেন
- `FIWANO_API_BASE_URL`: Default থাকলে ঠিক আছে

### 2. Database Migration

```bash
cd cnpi_api
python manage.py makemigrations fiwano_bot
python manage.py migrate
```

এটি তৈরি করবে:
- `FiwanoInboundMessage` - প্রতিটি incoming message
- `FiwanoConversation` - User-wise chat history

### 3. Dependencies

সব dependencies ইতিমধ্যে `requirements.txt`-এ আছে:

```bash
pip install -r requirements.txt
```

নতুন কিছু install করার দরকার নেই।

---

## Fiwano চ্যানেল কানেক্ট করা

### Step 1: Fiwano Portal-এ Login

1. https://fiwano.com এ যান
2. Account তৈরি করুন বা login করুন
3. 7-day free trial পাবেন, card লাগবে না

### Step 2: Facebook Page Connect করুন

1. Fiwano Portal → **Channels** → **Connect**
2. **Facebook Messenger** select করুন
3. Meta login করুন
4. আপনার Facebook Page select করুন
5. Permissions approve করুন
6. `channel_id` পাবেন

### Step 3: Webhook Configure করুন

1. আপনার Django deployment URL নোট করুন:
   ```
   https://your-app.onrender.com/api/fiwano/webhook/
   ```

2. Fiwano Portal-এ channel settings-এ যান:
   ```
   PATCH /api/v1/channels/{channel_id}
   ```

3. অথবা Portal UI ব্যবহার করুন:
   - Webhook URL: `https://your-app.onrender.com/api/fiwano/webhook/`
   - Webhook Events: `message.received` enable করুন
   - Webhook Secret: একটি secure random string set করুন

**Webhook Secret তৈরি করুন:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

এই secret আপনার `.env` ফাইলে `FIWANO_WEBHOOK_SECRET` হিসেবে রাখুন।

---

## ডিপ্লয়মেন্ট

### Render-এ Deploy

1. **Environment Variables** (Render Dashboard → Environment):

```bash
FIWANO_API_KEY=mip_live_xxxxxx
FIWANO_WEBHOOK_SECRET=xxxxxx
FIWANO_API_BASE_URL=https://fiwano.com/api/v1

# অন্যান্য বিদ্যমান env vars...
DATABASE_URL=...
GROQ_API_KEY=...
HF_TOKEN=...
```

2. **Build Command**:

```bash
cd cnpi_api && pip install -r requirements.txt
```

3. **Start Command**:

```bash
cd cnpi_api && python manage.py migrate && gunicorn cnpi_api.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

4. **Health Check**:

- Path: `/api/fiwano/health/`
- HTTP Method: GET

### Important Notes

- Webhook URL অবশ্যই **public HTTPS** হতে হবে
- `localhost` বা private IP কাজ করবে না
- Development-এর জন্য Cloudflare Tunnel বা ngrok ব্যবহার করতে পারেন

---

## টেস্টিং

### Step 1: Local Testing (Development)

1. Local server start করুন:

```bash
cd cnpi_api
python manage.py runserver
```

2. Cloudflare Tunnel/ngrok দিয়ে public URL তৈরি করুন:

```bash
# ngrok example
ngrok http 8000
```

3. Ngrok URL Fiwano channel-এ set করুন

### Step 2: API Connectivity Test

```bash
curl -X GET https://your-app.onrender.com/api/fiwano/test/ \
  -H "Content-Type: application/json"
```

এটি আপনার Fiwano channels list দেখাবে।

### Step 3: End-to-End Test

1. **Fixed Test Response দিয়ে শুরু করুন:**

`fiwano_bot/tasks.py` এর `process_message_background` function-এ temporarily:

```python
# Temporary test - comment out RAG call
# result = run_rag(...)
ai_response = "আপনার মেসেজ পেয়েছি। এটি একটি test response।"
```

2. **Facebook Page-এ message পাঠান:**

- আপনার connected Facebook Page-এ যান
- একটি test message পাঠান: "Hello test"
- দেখুন bot উত্তর দেয় কিনা

3. **Logs check করুন:**

```bash
# Render logs
render logs -f

# Local logs
python manage.py runserver  # Console output দেখুন
```

4. **Database check করুন:**

```bash
python manage.py shell

from fiwano_bot.models import FiwanoInboundMessage
FiwanoInboundMessage.objects.all()
```

### Step 4: Full RAG Integration Test

Test response সফল হলে RAG enable করুন:

1. `fiwano_bot/tasks.py` থেকে test code মুছুন
2. Deploy করুন
3. আবার Facebook Page-এ একটি real question পাঠান:
   ```
   "CST department er CI ke?"
   ```
4. Bot RAG থেকে উত্তর দেবে

### Step 5: Multiple User Test

দুটো আলাদা Facebook account দিয়ে test করুন:

1. প্রথম account থেকে message পাঠান
2. দ্বিতীয় account থেকে message পাঠান
3. Check করুন উভয়ের conversation আলাদা tracked হচ্ছে

---

## ট্রাবলশুটিং

### কোনো webhook আসছে না

**Check:**

1. Fiwano Portal-এ `message.received` event enabled আছে কিনা
2. Webhook URL সঠিক আছে কিনা (HTTPS, public)
3. Signature verification ঠিকমতো কাজ করছে কিনা
4. Render logs-এ কোনো error আছে কিনা

```bash
render logs -f | grep fiwano_bot
```

### Signature Verification Failed

**Check:**

1. `FIWANO_WEBHOOK_SECRET` সঠিক set করা আছে কিনা
2. Fiwano channel settings-এ same secret set করা আছে কিনা
3. Secret-এ কোনো extra space/newline নেই কিনা

### Bot উত্তর দিচ্ছে না

**Check:**

1. Background thread শুরু হচ্ছে কিনা (logs-এ দেখুন)
2. RAG system কাজ করছে কিনা:

```bash
curl -X POST https://your-app.onrender.com/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "test question"}'
```

3. Fiwano Send API সফল হচ্ছে কিনা (logs check করুন)
4. Database-এ message status check করুন:

```python
from fiwano_bot.models import FiwanoInboundMessage
msg = FiwanoInboundMessage.objects.last()
print(msg.status, msg.error_message)
```

### Duplicate Messages

এটি normal - Fiwano retry করে যদি 200 response না পায়।

**Solution:**

- Message database-এ unique constraint আছে
- Duplicate automatically skip হয়
- Logs-এ "duplicate" message দেখবেন

### RAG Timeout

যদি RAG response 30 seconds-এর বেশি সময় নেয়:

1. `fiwano_bot/tasks.py`-এ timeout বাড়ান (সাবধানে)
2. অথবা RAG system optimize করুন
3. 24-hour messaging window আছে তাই একটু বেশি সময় নিতে পারেন

### Fiwano API Errors

**Common errors:**

- **401 Unauthorized**: `FIWANO_API_KEY` ভুল বা missing
- **402 Payment Required**: Fiwano subscription expire হয়েছে
- **404 Not Found**: `channel_id` ভুল
- **422 Validation Error**: Invalid payload
- **429 Rate Limit**: Too many requests, retry করুন
- **5xx Server Error**: Fiwano-এর সমস্যা, retry করুন

---

## API Reference

### Webhook Endpoint

**POST /api/fiwano/webhook/**

Fiwano থেকে events receive করে।

**Headers:**
- `X-Webhook-Signature`: HMAC-SHA256 signature

**Request Body:**

```json
{
  "event": "message.received",
  "channel_id": "abc123",
  "channel_type": "facebook",
  "timestamp": "2026-10-08T15:30:00Z",
  "data": {
    "message_id": "mid.xxx",
    "from": "user_psid_123",
    "from_name": null,
    "type": "text",
    "text": "Hello!"
  }
}
```

**Response:**

```json
{
  "status": "ok"
}
```

### Health Check

**GET /api/fiwano/health/**

Simple health check, no authentication needed.

**Response:**

```json
{
  "status": "ok"
}
```

### Test Endpoint

**GET /api/fiwano/test/**

Fiwano API connectivity test (development only).

**Response:**

```json
{
  "status": "ok",
  "channels_count": 1,
  "channels": [
    {
      "id": "abc123",
      "type": "facebook",
      "is_active": true
    }
  ]
}
```

---

## Security Considerations

1. **Never commit secrets:**
   - `FIWANO_API_KEY` কখনো code-এ রাখবেন না
   - `.env` ফাইল `.gitignore`-এ রাখুন

2. **Signature verification:**
   - সবসময় enable রাখুন
   - Constant-time comparison ব্যবহার করা হয়েছে

3. **HTTPS only:**
   - Production-এ শুধুমাত্র HTTPS ব্যবহার করুন

4. **Rate limiting:**
   - Fiwano-এর rate limits মেনে চলুন
   - 429 error হলে retry করুন

5. **User data:**
   - Chat history encrypted database-এ store হয়
   - Privacy policy অনুযায়ী handle করুন

---

## Performance Tips

1. **Background Processing:**
   - Threading ব্যবহার করা হয়েছে
   - High-traffic-এর জন্য Celery recommend করা হয়

2. **Database Indexing:**
   - Message_id, channel_id, sender_id indexed
   - Query performance optimize করা

3. **Chat History Limit:**
   - শুধু শেষ 10 messages RAG-এ পাঠানো হয়
   - Memory-efficient

4. **Connection Pooling:**
   - Django `CONN_MAX_AGE=600` set করা আছে
   - Database connections reuse হয়

---

## Fiwano vs Direct Meta Integration

### Fiwano ব্যবহারের সুবিধা:

1. **No Meta App needed:**
   - Meta Developer App তৈরি করার দরকার নেই
   - App Review প্রয়োজন নেই
   - Business Verification প্রয়োজন নেই

2. **Simplified Setup:**
   - Portal-এ click করেই Facebook Page connect
   - Webhook instantly ready

3. **Single API:**
   - WhatsApp, Instagram, Messenger একই API
   - Unified payload format

4. **Maintained by Fiwano:**
   - Meta API changes automatically handled
   - No breaking changes

### সীমাবদ্ধতা:

1. **24-Hour Messaging Window:**
   - Meta-এর rule অনুযায়ী, user message পাঠানোর 24 ঘণ্টার মধ্যে reply করতে হবে
   - Proactive messaging-এর জন্য WhatsApp Template দরকার (Fiwano supports)

2. **Fiwano Subscription:**
   - 7-day free trial
   - Paid plan required for production

3. **Dependency:**
   - Fiwano platform-এর উপর নির্ভরশীল
   - Downtime হলে service affected হবে

---

## যোগাযোগ ও Support

- **Fiwano Documentation**: https://fiwano.com/documentation
- **Fiwano Support**: contact@fiwano.com
- **Status Page**: https://status.fiwano.com

---

## Changelog

### v1.0 (2026-10-08)

- Initial Fiwano Facebook Messenger integration
- Webhook signature verification (HMAC-SHA256)
- Background processing with threading
- Idempotency support
- Conversation history tracking
- Integration with existing RAG system
- Django admin interface
- Comprehensive tests
- Full documentation

---

## পরবর্তী উন্নতি

ভবিষ্যতে যোগ করা যেতে পারে:

1. **Celery Integration:**
   - High-traffic handling
   - Better background processing
   - Retry mechanisms

2. **Redis Caching:**
   - Faster conversation history
   - Distributed rate limiting

3. **Media Support:**
   - Image, audio, video handling
   - Fiwano Pro license দিয়ে

4. **WhatsApp & Instagram:**
   - Same codebase দিয়ে
   - Additional channels

5. **Analytics:**
   - Message volume tracking
   - Response time monitoring
   - User engagement metrics

6. **Advanced Features:**
   - Button templates
   - Quick replies
   - Rich media responses
