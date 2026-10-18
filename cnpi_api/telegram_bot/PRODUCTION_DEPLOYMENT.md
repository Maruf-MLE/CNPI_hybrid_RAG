# Production Deployment Guide - Render-এ Telegram Bot চালান

## 📋 Prerequisites

- ✅ Render account আছে
- ✅ Project already deployed: `https://cnpi-hybrid-rag-1.onrender.com`
- ✅ Bot token আছে: `8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY`
- ✅ Secret token আছে: `SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw`

---

## ধাপ ১: Render Environment Variables সেট করুন

### 1.1 Render Dashboard খুলুন

1. https://dashboard.render.com/ এ যান
2. আপনার service **"cnpi-hybrid-rag-1"** select করুন
3. Left sidebar থেকে **"Environment"** click করুন

### 1.2 Telegram Bot Variables যোগ করুন

**"Add Environment Variable" button click করুন এবং এই variables যোগ করুন:**

```
Key: TELEGRAM_BOT_TOKEN
Value: 8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY
```

```
Key: TELEGRAM_WEBHOOK_SECRET_TOKEN
Value: SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw
```

```
Key: TELEGRAM_BOT_ALLOWED_USERS
Value: (leave empty to allow all users)
```

### 1.3 RAG_API_URL Verify করুন

যদি `RAG_API_URL` variable না থাকে, তাহলে যোগ করুন:

```
Key: RAG_API_URL
Value: https://cnpi-hybrid-rag-1.onrender.com/api/chat/
```

### 1.4 Save করুন

**"Save Changes"** button click করুন। Render automatically redeploy শুরু করবে।

---

## ধাপ ২: Deployment সম্পূর্ণ হওয়ার জন্য অপেক্ষা করুন

### 2.1 Deploy Status দেখুন

Render Dashboard-এ **"Logs"** tab-এ যান এবং দেখুন:

```
==> Build successful 🎉
==> Deploying...
==> Your service is live 🎉
```

**সাধারণত 2-5 মিনিট লাগে।**

### 2.2 Service Live Check করুন

Browser-এ খুলুন:
```
https://cnpi-hybrid-rag-1.onrender.com/
```

যদি page load হয়, তাহলে service live আছে।

---

## ধাপ ৩: Telegram Webhook সেট করুন

### 3.1 Webhook URL তৈরি করুন

**Format:**
```
https://cnpi-hybrid-rag-1.onrender.com/telegram-webhook/<SECRET_TOKEN>/
```

**আপনার URL:**
```
https://cnpi-hybrid-rag-1.onrender.com/telegram-webhook/SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw/
```

### 3.2 PowerShell দিয়ে Webhook সেট করুন

**PowerShell খুলে এই commands চালান:**

```powershell
# Variables সেট করুন
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
$secretToken = "SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw"
$productionUrl = "https://cnpi-hybrid-rag-1.onrender.com"
$webhookUrl = "$productionUrl/telegram-webhook/$secretToken/"

Write-Host "Setting webhook to: $webhookUrl" -ForegroundColor Cyan

# Webhook সেট করুন
$response = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{url=$webhookUrl} | ConvertTo-Json)

# Response দেখান
Write-Host "`nResponse:" -ForegroundColor Green
$response | ConvertTo-Json

if ($response.ok) {
    Write-Host "`n✅ Webhook set successfully!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Webhook setup failed!" -ForegroundColor Red
}
```

**Expected Response:**
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

### 3.3 Alternative: Browser দিয়ে সেট করুন

Browser-এ এই URL খুলুন:
```
https://api.telegram.org/bot8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY/setWebhook?url=https://cnpi-hybrid-rag-1.onrender.com/telegram-webhook/SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw/
```

---

## ধাপ ৪: Webhook Verification

### 4.1 Webhook Info Check করুন

```powershell
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
$webhookInfo = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getWebhookInfo"

Write-Host "Webhook Info:" -ForegroundColor Cyan
$webhookInfo.result | Format-List

if ($webhookInfo.result.url -ne "") {
    Write-Host "✅ Webhook is active!" -ForegroundColor Green
} else {
    Write-Host "❌ Webhook is not set!" -ForegroundColor Red
}
```

**Expected Output:**
```
url                      : https://cnpi-hybrid-rag-1.onrender.com/telegram-webhook/SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw/
has_custom_certificate   : False
pending_update_count     : 0
max_connections          : 40
ip_address               : <Render IP>
```

### 4.2 যদি Error থাকে

**Common errors:**

**"Wrong response from the webhook":**
- Render deployment সম্পূর্ণ হয়নি — আরো 2-3 মিনিট wait করুন
- Service sleeping থেকে জেগে উঠছে — আবার চেষ্টা করুন

**"Can't parse URL":**
- URL-এ শেষে "/" আছে কিনা check করুন
- Secret token ঠিক আছে কিনা verify করুন

---

## ধাপ ৫: Bot Test করুন

### 5.1 Telegram App খুলুন

1. Telegram app খুলুন (mobile বা desktop)
2. Search করুন: **@cngpiBot**
3. "Start" button click করুন

### 5.2 Welcome Message দেখুন

Bot এই message পাঠাবে:
```
🙏 স্বাগতম! CNPI RAG Bot এ আপনাকে স্বাগতম।

আমি CNPI সম্পর্কিত যেকোনো প্রশ্নের উত্তর দিতে পারি। 
আপনার প্রশ্ন লিখুন এবং আমি সেরা উত্তর খুঁজে দেওয়ার চেষ্টা করব।

Welcome! I'm CNPI RAG Bot.

I can answer questions about CNPI. 
Just type your question and I'll find the best answer.
```

### 5.3 প্রশ্ন করুন

**Test প্রশ্ন:**
```
CST department er CI ke?
```

**Bot:**
- "typing..." indicator দেখাবে (10-30 seconds)
- উত্তর পাঠাবে: `"CST Department-এর Chief Instructor হলেন মোঃ আব্দুল কাদের..."`

### 5.4 Multi-turn Test করুন

```
User: tar contact number ki?
```

Bot context মনে রেখে উত্তর দেবে।

---

## ধাপ ৬: Logs Monitor করুন

### 6.1 Render Logs দেখুন

1. Render Dashboard → Your Service
2. **"Logs"** tab click করুন
3. Filter করুন: `telegram_bot`

**Expected logs:**
```
INFO telegram_bot: Telegram webhook update — update_id=123456789
INFO telegram_bot: Processing question from user 123456789 (chat 123456789): CST department er CI ke?
INFO telegram_bot: Sent answer to user 123456789 — status=found answer_len=156
```

### 6.2 Error Logs Check করুন

যদি error দেখেন:
```
ERROR telegram_bot: RAG API error — status 500
ERROR telegram_bot: Telegram sendMessage exception
```

---

## ধাপ ৭: Production Checklist ✅

- [ ] Render environment variables সেট করেছি
- [ ] Deployment সফল হয়েছে
- [ ] Webhook সেট করেছি
- [ ] `getWebhookInfo` দিয়ে verify করেছি
- [ ] Bot-কে `/start` পাঠিয়ে welcome message পেয়েছি
- [ ] একটা প্রশ্ন করে উত্তর পেয়েছি
- [ ] Render logs-এ "telegram_bot" logs দেখেছি
- [ ] Multi-turn conversation test করেছি

---

## 🔧 Troubleshooting

### Problem 1: Webhook সেট হচ্ছে না

**Solution:**
```powershell
# Current webhook delete করুন
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/deleteWebhook"

# 30 seconds wait করুন
Start-Sleep -Seconds 30

# আবার সেট করুন
$webhookUrl = "https://cnpi-hybrid-rag-1.onrender.com/telegram-webhook/SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw/"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
  -Method Post -ContentType "application/json" `
  -Body (@{url=$webhookUrl} | ConvertTo-Json)
```

### Problem 2: Bot responding নাই

**Check করুন:**

1. **Service live আছে কিনা:**
   ```powershell
   curl https://cnpi-hybrid-rag-1.onrender.com/
   ```

2. **Webhook active আছে কিনা:**
   ```powershell
   $botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
   Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getWebhookInfo"
   ```

3. **Environment variables ঠিক আছে কিনা:**
   - Render Dashboard → Environment
   - `TELEGRAM_BOT_TOKEN` check করুন
   - `TELEGRAM_WEBHOOK_SECRET_TOKEN` check করুন

4. **Render logs check করুন:**
   - Dashboard → Logs
   - "telegram_bot" search করুন
   - Error messages দেখুন

### Problem 3: Service sleeping

Render free tier-এ service 15 minutes inactive থাকলে sleep হয়ে যায়।

**Solution:**

1. **Service wake up করুন:**
   ```powershell
   curl https://cnpi-hybrid-rag-1.onrender.com/
   ```

2. **Webhook আবার সেট করুন:**
   ```powershell
   $botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
   $webhookUrl = "https://cnpi-hybrid-rag-1.onrender.com/telegram-webhook/SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw/"
   Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
     -Method Post -ContentType "application/json" `
     -Body (@{url=$webhookUrl} | ConvertTo-Json)
   ```

### Problem 4: 403 Forbidden error

**Webhook URL-এ secret token ভুল আছে।**

**Solution:**
1. `.env` file check করুন — `TELEGRAM_WEBHOOK_SECRET_TOKEN`
2. Render environment variables check করুন
3. দুটো match করে কিনা verify করুন
4. Webhook আবার সেট করুন

### Problem 5: Unauthorized user message

**User whitelist enabled আছে।**

**Solution:**

1. **Your user ID জানুন:**
   - Telegram-এ @userinfobot message করুন
   - User ID copy করুন (e.g., `123456789`)

2. **Render environment variables update করুন:**
   ```
   TELEGRAM_BOT_ALLOWED_USERS=123456789
   ```

3. **অথবা সবাইকে access দিন:**
   ```
   TELEGRAM_BOT_ALLOWED_USERS=
   ```

---

## 🎯 Quick Production Setup Commands

**সব commands একসাথে চালান:**

```powershell
# Variables
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
$secretToken = "SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw"
$productionUrl = "https://cnpi-hybrid-rag-1.onrender.com"
$webhookUrl = "$productionUrl/telegram-webhook/$secretToken/"

Write-Host "=== Telegram Bot Production Setup ===" -ForegroundColor Cyan

# Step 1: Wake up service
Write-Host "`n1. Waking up service..." -ForegroundColor Yellow
curl $productionUrl -TimeoutSec 30 | Out-Null
Start-Sleep -Seconds 5

# Step 2: Delete old webhook
Write-Host "`n2. Deleting old webhook..." -ForegroundColor Yellow
Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/deleteWebhook" | Out-Null
Start-Sleep -Seconds 2

# Step 3: Set new webhook
Write-Host "`n3. Setting webhook to: $webhookUrl" -ForegroundColor Yellow
$setResult = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
  -Method Post -ContentType "application/json" `
  -Body (@{url=$webhookUrl} | ConvertTo-Json)

if ($setResult.ok) {
    Write-Host "   ✅ Webhook set successfully!" -ForegroundColor Green
} else {
    Write-Host "   ❌ Failed to set webhook!" -ForegroundColor Red
    exit
}

Start-Sleep -Seconds 2

# Step 4: Verify webhook
Write-Host "`n4. Verifying webhook..." -ForegroundColor Yellow
$info = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getWebhookInfo"

Write-Host "`nWebhook Info:" -ForegroundColor Cyan
Write-Host "  URL: $($info.result.url)" -ForegroundColor White
Write-Host "  Pending Updates: $($info.result.pending_update_count)" -ForegroundColor White
Write-Host "  Last Error: $($info.result.last_error_message)" -ForegroundColor White

if ($info.result.url -eq $webhookUrl) {
    Write-Host "`n✅ Production setup complete!" -ForegroundColor Green
    Write-Host "`nBot is ready at: @cngpiBot" -ForegroundColor Cyan
    Write-Host "Send /start to test!" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ Webhook URL mismatch!" -ForegroundColor Red
    Write-Host "Expected: $webhookUrl" -ForegroundColor Yellow
    Write-Host "Got: $($info.result.url)" -ForegroundColor Yellow
}
```

---

## 📱 Final Test

1. **Telegram খুলুন**
2. **@cngpiBot** search করুন
3. **"Start"** button click করুন
4. **Message পাঠান:** "CST department er CI ke?"
5. **Bot উত্তর দেবে!**

---

## 🎉 সফল! Production-এ Bot চলছে

আপনার Telegram bot এখন production-এ live এবং যে কেউ ব্যবহার করতে পারবে।

**Bot URL:** https://t.me/cngpiBot

### Bot Share করুন:

```
আমাদের CNPI RAG Bot ব্যবহার করুন!
Telegram: @cngpiBot

CNPI সম্পর্কিত যেকোনো প্রশ্নের উত্তর পাবেন instantly!
```

---

## 📊 Monitoring

**Daily monitoring করুন:**

1. **Render Dashboard → Logs** — error check করুন
2. **Bot test করুন** — daily একবার message পাঠান
3. **Database check করুন** — processed message count দেখুন

**Weekly tasks:**
- Logs review করুন
- User feedback নিন
- Bot description update করুন (যদি দরকার হয়)

---

**Production deployment complete!** 🚀

**Created:** 2026-10-18  
**Service:** https://cnpi-hybrid-rag-1.onrender.com  
**Bot:** @cngpiBot  
**Status:** ✅ LIVE
