# Backend URL Update Checklist
## New URL: https://cnpi-hybrid-rag-7hvz.onrender.com

## ✅ DONE (Already Updated in Code)

### Configuration Files
- [x] `.env.render` - RENDER_PUBLIC_URL & HEARTBEAT_TARGET_URL
- [x] `RENDER_ENV_VARIABLES.txt` - RAG_API_URL
- [x] All Python upload scripts
- [x] Frontend Next.js config (netlify.toml)
- [x] All bot documentation

---

## 🔴 ACTION REQUIRED: Render Dashboard Setup

### Step 1: Go to Render Dashboard
1. Open: https://dashboard.render.com/
2. Find your service: `cnpi-hybrid-rag-7hvz` or create new service
3. Go to **Environment** tab

### Step 2: Update These Environment Variables

**CRITICAL - Update these 3 variables:**

```bash
# 1. Public URL
RENDER_PUBLIC_URL=https://cnpi-hybrid-rag-7hvz.onrender.com

# 2. Heartbeat Target
HEARTBEAT_TARGET_URL=https://cnpi-hybrid-rag-7hvz.onrender.com/api/ping/

# 3. RAG API URL (for Answer Bot)
RAG_API_URL=https://cnpi-hybrid-rag-7hvz.onrender.com/api/chat/
```

**Keep All Other Variables Same** (from `.env.render`):
- Database credentials (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT)
- API keys (GEMINI_API_KEY, HF_TOKEN)
- Django settings (DJANGO_SECRET_KEY, DEBUG=False)
- Bot tokens (FB_*, ANSWER_BOT_*, TELEGRAM_*)
- Performance settings (GUNICORN_*, CONN_MAX_AGE)

### Step 3: Save and Deploy
1. Click **"Save Changes"**
2. Service will automatically restart
3. Wait 2-3 minutes for deployment

---

## 🧪 TESTING: Verify Backend is Working

### Test 1: Health Check
```bash
curl https://cnpi-hybrid-rag-7hvz.onrender.com/api/ping/
```

**Expected Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-11-19T12:55:00Z"
}
```

### Test 2: RAG API Test
```bash
curl -X POST https://cnpi-hybrid-rag-7hvz.onrender.com/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is CNPI?",
    "session_id": "test-123"
  }'
```

**Expected:** JSON response with answer

### Test 3: Check Render Logs
1. Go to Render Dashboard → Your Service → **Logs** tab
2. Look for:
   - ✅ `Listening at: http://0.0.0.0:10000`
   - ✅ `Booting worker with pid: XXX`
   - ❌ No connection errors

---

## 📱 UPDATE WEBHOOKS (If Using Bots)

### Facebook Messenger (Document Saver Bot)
1. Meta App Dashboard → Webhooks
2. Update Callback URL to:
   ```
   https://cnpi-hybrid-rag-7hvz.onrender.com/webhook/
   ```

### Facebook Answer Bot (RAG Q&A)
1. Meta App Dashboard → Webhooks
2. Update Callback URL to:
   ```
   https://cnpi-hybrid-rag-7hvz.onrender.com/answer-webhook/
   ```

### Telegram Bot
Run this command with your bot token:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://cnpi-hybrid-rag-7hvz.onrender.com/telegram-webhook/<YOUR_SECRET_TOKEN>/",
    "secret_token": "<YOUR_WEBHOOK_SECRET>"
  }'
```

**PowerShell Version:**
```powershell
$botToken = "8639620113:AAEDo2ZIO0z88le3EMvwa1T_njSDR_V3acY"
$secretToken = "SGxoL0knDxVPxRXsp1_63Wdf92qblAwxxgMcLkb5Ijw"
$webhookUrl = "https://cnpi-hybrid-rag-7hvz.onrender.com/telegram-webhook/$secretToken/"

Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{
    url = $webhookUrl
    secret_token = $secretToken
  } | ConvertTo-Json)
```

---

## 🌐 FRONTEND UPDATE (Next.js)

### Netlify (Already configured in code)
File: `cnpichat-next/netlify.toml` already has:
```toml
NEXT_PUBLIC_API_URL = "https://cnpi-hybrid-rag-7hvz.onrender.com"
```

**Action:** Redeploy frontend on Netlify to pick up new URL

### Vercel (If using)
Add environment variable:
```
NEXT_PUBLIC_API_URL=https://cnpi-hybrid-rag-7hvz.onrender.com
```

---

## 🔍 TROUBLESHOOTING

### Issue: "Connection refused" or timeout
**Solution:**
1. Check Render service is running (not sleeping)
2. Wake it up: `curl https://cnpi-hybrid-rag-7hvz.onrender.com/`
3. Wait 30-60 seconds for cold start

### Issue: "404 Not Found"
**Solution:**
1. Verify service name matches: `cnpi-hybrid-rag-7hvz`
2. Check Render gave you this exact URL
3. Try base URL: `https://cnpi-hybrid-rag-7hvz.onrender.com/`

### Issue: Database connection error
**Solution:**
1. Check all DB_* environment variables are set in Render
2. Verify Neon database is not paused
3. Test connection from Render Shell

### Issue: Bots not responding
**Solution:**
1. Verify webhook URLs are updated in Meta/Telegram dashboard
2. Check bot tokens are set in Render environment variables
3. Look for webhook POST requests in Render logs

---

## 📋 QUICK COMMAND REFERENCE

```bash
# Health check
curl https://cnpi-hybrid-rag-7hvz.onrender.com/api/ping/

# Wake up service
curl https://cnpi-hybrid-rag-7hvz.onrender.com/

# Test RAG API
curl -X POST https://cnpi-hybrid-rag-7hvz.onrender.com/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question":"Test","session_id":"test"}'

# Check Telegram webhook
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

---

## ✅ FINAL CHECKLIST

- [ ] Updated environment variables in Render Dashboard
- [ ] Saved changes and service restarted
- [ ] Health check returns 200 OK
- [ ] RAG API responds correctly
- [ ] Updated Facebook webhook URLs (if using)
- [ ] Updated Telegram webhook URL (if using)
- [ ] Redeployed frontend on Netlify/Vercel
- [ ] Tested end-to-end: Frontend → Backend → Database
- [ ] Set up heartbeat/keep-alive cron job

---

## 📞 SUPPORT

If issues persist:
1. Check Render logs for errors
2. Verify all environment variables match `.env.render`
3. Ensure service has 4GB RAM plan (required for RAG)
4. Contact dev team with error logs

---

**Last Updated:** 2026-11-19  
**Backend URL:** https://cnpi-hybrid-rag-7hvz.onrender.com  
**Status:** ✅ Code updated, ⏳ Render setup pending
