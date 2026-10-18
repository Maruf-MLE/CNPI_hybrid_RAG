# Telegram Bot Testing Guide - দ্রুত Test করুন

## ✅ Configuration Status

```
Bot Name: CNGPI_Chat
Bot Username: @cngpiBot
Bot ID: 8639620113
Status: ✅ ACTIVE এবং READY

Environment Variables: ✅ SET
- TELEGRAM_BOT_TOKEN: 8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY
- TELEGRAM_WEBHOOK_SECRET_TOKEN: SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw
- TELEGRAM_BOT_ALLOWED_USERS: (empty - all users allowed)

Database: ✅ MIGRATED
Django Server: ✅ RUNNING on http://127.0.0.1:8000
```

---

## 🚀 Method 1: Webhook দিয়ে Test (Production-like)

### Prerequisites: ngrok Install করুন

**Download:** https://ngrok.com/download

**Install করার পর:**
```powershell
# ngrok account signup করুন (free)
# Auth token সেট করুন
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### Step 1: ngrok চালান

**নতুন PowerShell window খুলুন:**
```powershell
ngrok http 8000
```

**Output থেকে HTTPS URL copy করুন:**
```
Forwarding  https://abc123xyz.ngrok.io -> http://localhost:8000
```

### Step 2: Webhook Set করুন

**PowerShell-এ চালান** (নিজের ngrok URL দিন):
```powershell
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
$secretToken = "SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw"
$ngrokUrl = "https://abc123xyz.ngrok.io"  # আপনার ngrok URL
$webhookUrl = "$ngrokUrl/telegram-webhook/$secretToken/"

Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{url=$webhookUrl} | ConvertTo-Json)
```

**Expected Response:**
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

### Step 3: Webhook Verify করুন

```powershell
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getWebhookInfo"
```

**Expected Response:**
```json
{
  "ok": true,
  "result": {
    "url": "https://abc123xyz.ngrok.io/telegram-webhook/SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw/",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### Step 4: Bot-কে Message পাঠান

1. Telegram app খুলুন
2. Search করুন: **@cngpiBot**
3. "Start" button ক্লিক করুন
4. Bot welcome message পাঠাবে
5. একটা প্রশ্ন করুন: **"CST department er CI ke?"**

### Step 5: Logs Monitor করুন

Django server চলছে যে terminal-এ সেখানে দেখবেন:
```
INFO telegram_bot: Telegram webhook update — update_id=...
INFO telegram_bot: Processing question from user ... (chat ...): CST department er CI ke?
INFO telegram_bot: Sent answer to user ... — status=found answer_len=...
```

---

## 🧪 Method 2: Manual Testing (ngrok ছাড়া)

ngrok install না থাকলে manual testing করতে পারেন।

### Step 1: Bot-কে Message পাঠান

1. Telegram-এ **@cngpiBot** খুলুন
2. `/start` বা যেকোনো message পাঠান

### Step 2: Updates Fetch করুন

```powershell
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
$updates = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getUpdates"
$updates | ConvertTo-Json -Depth 10
```

**প্রথম message দেখবেন:**
```json
{
  "update_id": 123456,
  "message": {
    "message_id": 1,
    "from": {
      "id": 123456789,
      "first_name": "Your Name",
      "username": "your_username"
    },
    "chat": {
      "id": 123456789,
      "type": "private"
    },
    "text": "/start"
  }
}
```

### Step 3: Manual Test Script চালান

Save this as `test_telegram_bot.ps1`:

```powershell
# Test Telegram Bot Manually
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
$secretToken = "SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw"

# Get updates
Write-Host "Fetching updates..." -ForegroundColor Cyan
$updates = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getUpdates"

if ($updates.result.Count -eq 0) {
    Write-Host "No messages found. Please send a message to @cngpiBot first." -ForegroundColor Yellow
    exit
}

# Get latest message
$latestUpdate = $updates.result[-1]
$chatId = $latestUpdate.message.chat.id
$messageText = $latestUpdate.message.text
$updateId = $latestUpdate.update_id

Write-Host "`nReceived message:" -ForegroundColor Green
Write-Host "  Chat ID: $chatId"
Write-Host "  Text: $messageText"
Write-Host "  Update ID: $updateId"

# Simulate webhook call to Django
Write-Host "`nSending to Django webhook..." -ForegroundColor Cyan
$webhookUrl = "http://127.0.0.1:8000/telegram-webhook/$secretToken/"

$body = @{
    update_id = $updateId
    message = $latestUpdate.message
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri $webhookUrl `
        -Method Post `
        -ContentType "application/json" `
        -Body $body
    
    Write-Host "Django response:" -ForegroundColor Green
    $response | ConvertTo-Json
    
    # Clear this update
    Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getUpdates?offset=$($updateId + 1)" | Out-Null
    Write-Host "`nUpdate cleared. Check bot for reply!" -ForegroundColor Green
    
} catch {
    Write-Host "Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message
}
```

**চালান:**
```powershell
cd G:\CNPI_Hybrid_RAG\cnpi_api\telegram_bot
.\test_telegram_bot.ps1
```

---

## 🧹 Webhook Remove করুন (Manual Testing-এর জন্য)

Manual testing করার আগে webhook remove করতে হবে:

```powershell
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/deleteWebhook"
```

**Verify:**
```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getWebhookInfo"
```

Response-এ `"url": ""` দেখাবে।

---

## 📊 Quick Test Commands

### Bot Status চেক করুন
```powershell
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getMe"
```

### Webhook Info দেখুন
```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getWebhookInfo"
```

### Recent Messages দেখুন
```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getUpdates"
```

### Test Message পাঠান (Direct)
```powershell
$chatId = "YOUR_CHAT_ID"  # @userinfobot থেকে পান
$text = "Test message from script"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/sendMessage" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{chat_id=$chatId; text=$text} | ConvertTo-Json)
```

---

## 🔍 Troubleshooting

### Django Server Check করুন
```powershell
curl http://127.0.0.1:8000/
```

### Logs দেখুন
Django server terminal-এ `telegram_bot` filter করুন:
```
INFO telegram_bot: ...
ERROR telegram_bot: ...
```

### Database Check করুন
```powershell
cd G:\CNPI_Hybrid_RAG\cnpi_api
python manage.py shell

# Python shell-এ:
from telegram_bot.models import ProcessedTelegramMessage
print(ProcessedTelegramMessage.objects.count())
print(ProcessedTelegramMessage.objects.all()[:5])
```

### Configuration Verify করুন
```powershell
cd G:\CNPI_Hybrid_RAG\cnpi_api
python manage.py shell

# Python shell-এ:
from django.conf import settings
print("Bot Token:", settings.TELEGRAM_BOT_TOKEN[:20] + "...")
print("Secret Token:", settings.TELEGRAM_WEBHOOK_SECRET_TOKEN[:20] + "...")
print("Allowed Users:", settings.TELEGRAM_BOT_ALLOWED_USERS)
print("RAG API URL:", settings.RAG_API_URL)
```

---

## ✅ Expected Behavior

### When user sends `/start`:
```
Bot Reply:
🙏 স্বাগতম! CNPI RAG Bot এ আপনাকে স্বাগতম।

আমি CNPI সম্পর্কিত যেকোনো প্রশ্নের উত্তর দিতে পারি। 
আপনার প্রশ্ন লিখুন এবং আমি সেরা উত্তর খুঁজে দেওয়ার চেষ্টা করব।

Welcome! I'm CNPI RAG Bot.

I can answer questions about CNPI. 
Just type your question and I'll find the best answer.
```

### When user asks a question:
1. Bot shows "typing..." indicator
2. Bot processes question via RAG API (may take 10-30 seconds)
3. Bot sends answer

### Example:
```
User: CST department er CI ke?
Bot: CST Department-এর Chief Instructor হলেন মোঃ আব্দুল কাদের...
```

---

## 🚀 Ready to Test!

**আপনার bot সম্পূর্ণ ready এবং configured।**

**Recommended Testing Method:**
1. ngrok install করুন (Method 1)
2. Webhook সেট করুন
3. Real-time messaging test করুন

**Alternative:**
1. Manual test script use করুন (Method 2)
2. Webhook ছাড়াই test করুন

**Production Deployment:**
- Render-এ deploy করার পর উপরের webhook commands-এ ngrok URL-এর জায়গায় Render URL ব্যবহার করুন
- Example: `https://cnpi-hybrid-rag-1.onrender.com/telegram-webhook/SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw/`

---

**Created:** 2026-10-18  
**Bot Username:** @cngpiBot  
**Status:** ✅ READY FOR TESTING
