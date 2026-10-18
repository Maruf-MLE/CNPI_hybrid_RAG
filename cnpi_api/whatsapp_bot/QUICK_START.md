# 🎯 WhatsApp Bot - Quick Start Summary

## ✅ আপনার জন্য যা করা হয়েছে

### 1. **`.env` File Updated**
আপনার existing `.env` file এ WhatsApp bot এর সব required variables add করা হয়েছে:
- `WHATSAPP_API_TOKEN` - Meta থেকে নিতে হবে
- `WHATSAPP_PHONE_NUMBER_ID` - Meta থেকে নিতে হবে  
- `WHATSAPP_WEBHOOK_VERIFY_TOKEN` - আপনি নিজে তৈরি করবেন
- `WHATSAPP_WEBHOOK_SECRET` - Meta থেকে নিতে হবে
- `RAG_API_URL` - Already set (http://127.0.0.1:8000/api/chat/)

**File Location:** `G:\CNPI_Hybrid_RAG\cnpi_api\.env`

### 2. **Credentials Guide তৈরি করা হয়েছে**
Step-by-step guide যেখানে প্রতিটি credential কোথায় পাবেন তা বিস্তারিত আছে।

**File Location:** `G:\CNPI_Hybrid_RAG\cnpi_api\whatsapp_bot\CREDENTIALS_GUIDE.md`

---

## 🚀 এখন যা করতে হবে (Priority Order)

### 📍 Step 1: Meta Business Manager Setup (30 minutes)

#### 1a. Business Account তৈরি করুন
```
URL: https://business.facebook.com
- Facebook account দিয়ে login করুন
- "Create Account" → Business information দিন
```

#### 1b. WhatsApp App তৈরি করুন
```
URL: https://developers.facebook.com/apps/
- "Create App" → "Business" type → App name দিন
- "WhatsApp" product add করুন
```

#### 1c. API Token নিন
```
URL: https://business.facebook.com/settings/system-users
- System User তৈরি করুন
- "Generate New Token" click করুন
- Permissions: whatsapp_business_management, whatsapp_business_messaging
- Token copy করে .env এ WHATSAPP_API_TOKEN এ paste করুন
```

#### 1d. Phone Number ID নিন
```
URL: https://developers.facebook.com/apps/ → Your App → WhatsApp → API Setup
- "From" section এ Phone number ID পাবেন
- Copy করে .env এ WHATSAPP_PHONE_NUMBER_ID এ paste করুন
```

#### 1e. App Secret নিন
```
URL: https://developers.facebook.com/apps/ → Your App → Settings → Basic
- "App Secret" এর "Show" button click করুন
- Copy করে .env এ WHATSAPP_WEBHOOK_SECRET এ paste করুন
```

#### 1f. Verify Token তৈরি করুন
```powershell
# PowerShell এ run করুন random token তৈরি করতে:
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

# Output copy করে .env এ WHATSAPP_WEBHOOK_VERIFY_TOKEN এ দিন
```

---

### 📍 Step 2: Django Setup (10 minutes)

```bash
# 1. Dependencies install করুন
cd G:\CNPI_Hybrid_RAG\cnpi_api
pip install -r whatsapp_bot\requirements.txt

# 2. settings.py update করুন
# Add to INSTALLED_APPS:
'whatsapp_bot',

# 3. urls.py update করুন  
# Add to urlpatterns:
path('api/whatsapp/', include('whatsapp_bot.urls')),

# 4. Database migration
python manage.py makemigrations whatsapp_bot
python manage.py migrate whatsapp_bot

# 5. Server start করুন
python manage.py runserver 8000
```

---

### 📍 Step 3: Public URL Setup (Development)

#### Option A: Using ngrok (Recommended for testing)
```bash
# 1. ngrok download করুন: https://ngrok.com/download
# 2. Install and signup করুন
# 3. Run:
ngrok http 8000

# Output এ যে HTTPS URL পাবেন সেটা copy করুন
# Example: https://abc123.ngrok.io
```

#### Option B: Production Server
```
- Deploy to Heroku/AWS/DigitalOcean
- Ensure HTTPS is enabled
```

---

### 📍 Step 4: Webhook Setup (5 minutes)

```
URL: https://developers.facebook.com/apps/ → Your App → WhatsApp → Configuration

1. "Webhook" section এ "Edit" click করুন
2. Callback URL: https://your-domain.com/api/whatsapp/webhook/
3. Verify Token: আপনার WHATSAPP_WEBHOOK_VERIFY_TOKEN (from .env)
4. "Verify and Save" click করুন
5. Subscribe to webhook fields: ✅ messages
```

---

### 📍 Step 5: Test করুন (5 minutes)

```bash
# 1. Health check
curl http://localhost:8000/api/whatsapp/health/

# Expected response:
{
  "status": "healthy",
  "configuration": {
    "api_token_configured": true,
    "phone_number_configured": true,
    "webhook_secret_configured": true
  }
}

# 2. WhatsApp থেকে test message পাঠান
# Test number: Meta developer console এ test number পাবেন
# Message পাঠিয়ে response পান কিনা check করুন
```

---

## 📚 Important Files & Locations

```
G:\CNPI_Hybrid_RAG\cnpi_api\
├── .env                              ← Environment variables (credentials here)
├── whatsapp_bot\
│   ├── README.md                     ← Complete documentation
│   ├── CREDENTIALS_GUIDE.md          ← How to get credentials
│   ├── models.py                     ← Database models
│   ├── views.py                      ← Webhook handlers
│   ├── whatsapp_service.py           ← WhatsApp API integration
│   ├── tasks.py                      ← Background processing
│   ├── urls.py                       ← URL routes
│   ├── admin.py                      ← Django admin interface
│   └── requirements.txt              ← Dependencies
```

---

## 🔗 Important URLs

| Purpose | URL |
|---------|-----|
| **Meta Business Manager** | https://business.facebook.com |
| **Meta Developer Console** | https://developers.facebook.com/apps/ |
| **System Users (Token)** | https://business.facebook.com/settings/system-users |
| **WhatsApp Docs** | https://developers.facebook.com/docs/whatsapp |
| **Your Health Check** | http://localhost:8000/api/whatsapp/health/ |
| **Your Stats** | http://localhost:8000/api/whatsapp/stats/ |
| **Your Webhook** | https://your-domain.com/api/whatsapp/webhook/ |

---

## ⚡ Quick Commands Reference

```bash
# Install dependencies
pip install -r whatsapp_bot\requirements.txt

# Database migration
python manage.py makemigrations whatsapp_bot
python manage.py migrate whatsapp_bot

# Create admin user
python manage.py createsuperuser

# Run server
python manage.py runserver 8000

# Run with ngrok (separate terminal)
ngrok http 8000

# Check health
curl http://localhost:8000/api/whatsapp/health/

# View Django admin
http://localhost:8000/admin/

# Django shell test
python manage.py shell
>>> from whatsapp_bot.whatsapp_service import get_whatsapp_service
>>> service = get_whatsapp_service()
>>> print("Config OK" if service.api_token else "Config Missing")
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "api_token_configured": false
**Solution:** `.env` file এ `WHATSAPP_API_TOKEN` সঠিক আছে কিনা check করুন

### Issue 2: Webhook verification failed
**Solution:** 
- `WHATSAPP_WEBHOOK_VERIFY_TOKEN` same আছে কিনা check করুন (.env এবং Meta console এ)
- URL publicly accessible কিনা check করুন

### Issue 3: Database migration error
**Solution:**
```bash
python manage.py migrate --fake-initial
python manage.py migrate whatsapp_bot
```

### Issue 4: RAG API not responding
**Solution:**
- RAG API running আছে কিনা check করুন
- `.env` এ `RAG_API_URL` সঠিক আছে কিনা verify করুন

---

## 📞 Need Help?

1. **Complete Documentation:** `whatsapp_bot\README.md`
2. **Credentials Guide:** `whatsapp_bot\CREDENTIALS_GUIDE.md`
3. **WhatsApp Official Docs:** https://developers.facebook.com/docs/whatsapp
4. **Troubleshooting:** Check README.md → Troubleshooting section

---

## ✅ Final Checklist

Setup complete হলে এগুলো check করুন:

- [ ] Meta Business Manager account তৈরি হয়েছে
- [ ] WhatsApp App তৈরি হয়েছে
- [ ] `.env` file এ সব credentials দেওয়া হয়েছে
- [ ] Dependencies install হয়েছে
- [ ] Django settings.py updated হয়েছে
- [ ] Database migration complete হয়েছে
- [ ] Server running আছে
- [ ] ngrok/public URL setup হয়েছে
- [ ] Webhook verified হয়েছে
- [ ] Health check responding করছে
- [ ] Test message পাঠিয়ে response পেয়েছি

---

**সব কিছু সঠিকভাবে setup হলে আপনার WhatsApp bot live হয়ে যাবে!** 🎉

Good luck! 🚀
