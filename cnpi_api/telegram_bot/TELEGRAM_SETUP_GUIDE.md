# Telegram Bot Setup Guide - ধাপে ধাপে সম্পূর্ণ গাইড

এই গাইড অনুসরণ করে আপনি একটি professional Telegram bot তৈরি করতে পারবেন যা CNPI Hybrid RAG ব্যবহার করে প্রশ্নের উত্তর দেবে।

---

## ধাপ ১: Telegram Bot তৈরি করুন

### 1.1 BotFather-এর সাথে যোগাযোগ করুন

1. Telegram app খুলুন
2. Search করুন: **@BotFather**
3. "Start" button ক্লিক করুন

### 1.2 নতুন Bot তৈরি করুন

BotFather-কে পাঠান:
```
/newbot
```

BotFather জিজ্ঞাসা করবে:

**প্রশ্ন 1: Bot-এর নাম কি হবে?**
```
CNPI RAG Bot
```
_(যেকোনো নাম দিতে পারেন, এটা display name)_

**প্রশ্ন 2: Bot-এর username কি হবে?**
```
cnpi_rag_bot
```
_(অবশ্যই "bot" দিয়ে শেষ হতে হবে এবং unique হতে হবে)_

### 1.3 Bot Token সংরক্ষণ করুন

BotFather একটি message পাঠাবে:
```
Done! Congratulations on your new bot...
Use this token to access the HTTP API:
123456789:ABCdefGHIjklMNOpqrsTUVwxyz

Keep your token secure...
```

**⚠️ এই token টা copy করে নিরাপদ জায়গায় রাখুন। এটা আপনার bot-এর password।**

### 1.4 Bot Description সেট করুন (Optional)

```
/setdescription
```

তারপর পাঠান:
```
CNPI RAG Bot - আমি CNPI সম্পর্কিত যেকোনো প্রশ্নের উত্তর দিতে পারি। I can answer questions about CNPI.
```

### 1.5 Bot About Text সেট করুন (Optional)

```
/setabouttext
```

তারপর পাঠান:
```
RAG-powered Q&A bot for CNPI
```

### 1.6 Bot Commands সেট করুন (Optional)

```
/setcommands
```

তারপর পাঠান:
```
start - Start the bot and see welcome message
```

---

## ধাপ ২: Environment Variables Configure করুন

### 2.1 .env File খুলুন

```
G:\CNPI_Hybrid_RAG\.env
```

### 2.2 Telegram Bot Configuration যোগ করুন

File-এর যেকোনো জায়গায় (নিচের দিকে ভালো হয়) এই lines যোগ করুন:

```bash
# Telegram Bot Configuration
# ==========================
# Bot token from @BotFather
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Webhook secret token (generate below)
TELEGRAM_WEBHOOK_SECRET_TOKEN=your_random_secret_token_here

# User whitelist - comma-separated user IDs (leave empty to allow all)
TELEGRAM_BOT_ALLOWED_USERS=
```

### 2.3 Bot Token বসান

BotFather থেকে পাওয়া token টা `TELEGRAM_BOT_TOKEN`-এ বসান:
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 2.4 Webhook Secret Token Generate করুন

**Windows PowerShell-এ চালান:**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Output example:**
```
Xk29fLq7tN8pRv5Yw3Qz2Hm6Jc4Ub9Kg1Fa7
```

এই random token টা `TELEGRAM_WEBHOOK_SECRET_TOKEN`-এ বসান:
```bash
TELEGRAM_WEBHOOK_SECRET_TOKEN=Xk29fLq7tN8pRv5Yw3Qz2Hm6Jc4Ub9Kg1Fa7
```

### 2.5 User Whitelist সেট করুন (Optional)

**সবাইকে access দিতে চান?** — খালি রাখুন:
```bash
TELEGRAM_BOT_ALLOWED_USERS=
```

**শুধু নির্দিষ্ট users-দের access দিতে চান?**

1. আপনার Telegram user ID জানুন:
   - Telegram-এ **@userinfobot** খুঁজুন
   - "Start" করুন
   - Bot আপনার user ID দেখাবে (e.g., `123456789`)

2. User IDs comma-separated format-এ লিখুন:
```bash
TELEGRAM_BOT_ALLOWED_USERS=123456789,987654321,555666777
```

### 2.6 RAG API URL যাচাই করুন

`.env` file-এ নিচের line আছে কিনা check করুন:
```bash
RAG_API_URL=http://127.0.0.1:8000/api/chat/
```

---

## ধাপ ৩: Database Migration চালান

### 3.1 Terminal খুলুন

PowerShell বা CMD খুলুন:
```powershell
cd G:\CNPI_Hybrid_RAG\cnpi_api
```

### 3.2 Migration Files তৈরি করুন

```powershell
python manage.py makemigrations telegram_bot
```

**Expected output:**
```
Migrations for 'telegram_bot':
  telegram_bot\migrations\0001_initial.py
    - Create model ProcessedTelegramMessage
```

### 3.3 Migration চালান

```powershell
python manage.py migrate telegram_bot
```

**Expected output:**
```
Operations to perform:
  Apply all migrations: telegram_bot
Running migrations:
  Applying telegram_bot.0001_initial... OK
```

---

## ধাপ ৪: Local Testing Setup (ngrok দিয়ে)

### 4.1 Django Server চালান

**Terminal 1:**
```powershell
cd G:\CNPI_Hybrid_RAG\cnpi_api
python manage.py runserver
```

**Expected output:**
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### 4.2 ngrok চালান

**Terminal 2 (নতুন terminal খুলুন):**
```powershell
ngrok http 8000
```

**Expected output:**
```
Forwarding  https://abc123xyz.ngrok.io -> http://localhost:8000
```

**⚠️ এই HTTPS URL টা copy করে রাখুন** (e.g., `https://abc123xyz.ngrok.io`)

---

## ধাপ ৫: Telegram Webhook সেট করুন

### 5.1 Webhook URL তৈরি করুন

Format:
```
https://your-ngrok-url.ngrok.io/telegram-webhook/<YOUR_SECRET_TOKEN>/
```

Example:
```
https://abc123xyz.ngrok.io/telegram-webhook/Xk29fLq7tN8pRv5Yw3Qz2Hm6Jc4Ub9Kg1Fa7/
```

**⚠️ শেষে "/" দিতে ভুলবেন না!**

### 5.2 Webhook Set করুন

**Method 1: PowerShell দিয়ে**

```powershell
$botToken = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
$secretToken = "Xk29fLq7tN8pRv5Yw3Qz2Hm6Jc4Ub9Kg1Fa7"
$ngrokUrl = "https://abc123xyz.ngrok.io"
$webhookUrl = "$ngrokUrl/telegram-webhook/$secretToken/"

Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{url=$webhookUrl} | ConvertTo-Json)
```

**Method 2: Browser দিয়ে**

Browser-এ এই URL খুলুন (replace করে নিজের values দিন):
```
https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook?url=https://abc123xyz.ngrok.io/telegram-webhook/Xk29fLq7tN8pRv5Yw3Qz2Hm6Jc4Ub9Kg1Fa7/
```

### 5.3 Webhook Status যাচাই করুন

**PowerShell:**
```powershell
$botToken = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getWebhookInfo"
```

**Browser:**
```
https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/getWebhookInfo
```

**Expected response:**
```json
{
  "ok": true,
  "result": {
    "url": "https://abc123xyz.ngrok.io/telegram-webhook/Xk29fLq7tN8pRv5Yw3Qz2Hm6Jc4Ub9Kg1Fa7/",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "max_connections": 40
  }
}
```

---

## ধাপ ৬: Bot Test করুন

### 6.1 Bot খুঁজুন

1. Telegram app খুলুন
2. Search করুন: আপনার bot username (e.g., `@cnpi_rag_bot`)
3. "Start" button ক্লিক করুন

### 6.2 Welcome Message যাচাই করুন

Bot একটা welcome message পাঠাবে:
```
🙏 স্বাগতম! CNPI RAG Bot এ আপনাকে স্বাগতম।

আমি CNPI সম্পর্কিত যেকোনো প্রশ্নের উত্তর দিতে পারি। 
আপনার প্রশ্ন লিখুন এবং আমি সেরা উত্তর খুঁজে দেওয়ার চেষ্টা করব।

Welcome! I'm CNPI RAG Bot.

I can answer questions about CNPI. 
Just type your question and I'll find the best answer.
```

### 6.3 প্রশ্ন করুন

```
User: CST department er CI ke?
```

Bot "typing..." দেখাবে, তারপর উত্তর দেবে:
```
Bot: CST Department-এর Chief Instructor হলেন মোঃ আব্দুল কাদের...
```

### 6.4 Multi-turn Conversation Test করুন

```
User: tar contact number ki?
```

Bot context মনে রেখে উত্তর দেবে:
```
Bot: 01734567890
```

---

## ধাপ ৭: Logs Monitor করুন

### 7.1 Django Logs দেখুন

Terminal 1 (যেখানে `runserver` চলছে) দেখুন:

```
INFO telegram_bot: Processing question from user 123456789 (chat 123456789): CST department er CI ke?
INFO telegram_bot: Sent answer to user 123456789 — status=found answer_len=156
```

### 7.2 Error Logs

যদি কোনো সমস্যা হয়:
```
ERROR telegram_bot: RAG API error — status 500: Internal Server Error
ERROR telegram_bot: Telegram sendMessage exception for chat 123456789:
...
```

---

## ধাপ ৮: Production Deployment (Render)

### 8.1 Render Environment Variables সেট করুন

Render Dashboard → Your Service → Environment:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET_TOKEN=Xk29fLq7tN8pRv5Yw3Qz2Hm6Jc4Ub9Kg1Fa7
TELEGRAM_BOT_ALLOWED_USERS=
RAG_API_URL=https://cnpi-hybrid-rag-1.onrender.com/api/chat/
```

### 8.2 Deploy করুন

Render automatically deploy করবে।

### 8.3 Production Webhook সেট করুন

```powershell
$botToken = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
$secretToken = "Xk29fLq7tN8pRv5Yw3Qz2Hm6Jc4Ub9Kg1Fa7"
$productionUrl = "https://cnpi-hybrid-rag-1.onrender.com"
$webhookUrl = "$productionUrl/telegram-webhook/$secretToken/"

Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{url=$webhookUrl} | ConvertTo-Json)
```

### 8.4 Verify করুন

```powershell
$botToken = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getWebhookInfo"
```

---

## Common Issues এবং Solutions

### ❌ Problem: Bot responding নাই

**Solution 1: Webhook check করুন**
```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

**Solution 2: Django logs দেখুন**
```
Terminal 1 দেখুন — "telegram_bot" logs আসছে কিনা
```

**Solution 3: Server running check করুন**
```powershell
curl http://127.0.0.1:8000/api/health/
```

### ❌ Problem: "Unauthorized user" message

**Solution: User ID whitelist-এ যোগ করুন**

1. User ID জানুন (@userinfobot থেকে)
2. `.env` file update করুন:
```bash
TELEGRAM_BOT_ALLOWED_USERS=123456789
```
3. Server restart করুন

### ❌ Problem: Webhook forbidden (403)

**Solution: Secret token মিলছে কিনা check করুন**

1. `.env` file-এ `TELEGRAM_WEBHOOK_SECRET_TOKEN` check করুন
2. Webhook URL-এ same token আছে কিনা verify করুন
3. Webhook আবার সেট করুন

### ❌ Problem: RAG API timeout

**Solution 1: Timeout বাড়ান**

`telegram_bot/views.py` খুলুন, line 160:
```python
timeout=60,  # 60 থেকে 120 করুন
```

**Solution 2: RAG API running check করুন**
```powershell
curl -X POST http://127.0.0.1:8000/api/chat/ `
  -H "Content-Type: application/json" `
  -d '{"message":"test"}'
```

### ❌ Problem: Message too long (400 Bad Request)

**Solution: Bot automatically truncate করে 4096 characters-এ**

Code already implemented আছে `views.py`-তে:
```python
if len(text) > 4096:
    text = text[:4093] + "..."
```

---

## Checklist - সব কিছু ঠিক আছে কিনা

- [ ] BotFather থেকে bot token পেয়েছি
- [ ] `.env` file-এ `TELEGRAM_BOT_TOKEN` সেট করেছি
- [ ] Secret token generate করে `TELEGRAM_WEBHOOK_SECRET_TOKEN`-এ সেট করেছি
- [ ] `python manage.py migrate telegram_bot` চালিয়েছি
- [ ] Django server running আছে (`python manage.py runserver`)
- [ ] ngrok running আছে এবং HTTPS URL পেয়েছি
- [ ] Telegram webhook সেট করেছি
- [ ] `getWebhookInfo` দিয়ে verify করেছি
- [ ] Bot-কে `/start` পাঠিয়ে welcome message পেয়েছি
- [ ] একটা প্রশ্ন করে উত্তর পেয়েছি
- [ ] Django logs-এ "telegram_bot" logs দেখা যাচ্ছে

---

## সফল! 🎉

আপনার Telegram bot এখন কাজ করছে। Users এখন bot-কে CNPI সম্পর্কে প্রশ্ন করতে পারবে এবং RAG-powered উত্তর পাবে।

## Next Steps

1. **Bot profile picture সেট করুন** — BotFather থেকে `/setuserpic`
2. **Bot description customize করুন** — BotFather থেকে `/setdescription`
3. **User whitelist enable করুন** — production-এ শুধু authorized users-দের access দিন
4. **Logs monitor করুন** — regular basis-এ error logs check করুন
5. **Backup setup করুন** — database backup নিয়মিত নিন

---

**Created:** 2026-10-18  
**Version:** 1.0  
**Support:** যদি কোনো সমস্যা হয়, README.md দেখুন বা logs check করুন
