# 🔑 WhatsApp Bot Credentials - কোথায় কি পাবেন

এই guide টি follow করে WhatsApp bot এর সব credentials সংগ্রহ করুন।

---

## 📋 যা যা লাগবে (Checklist)

- [ ] WhatsApp API Token
- [ ] Phone Number ID
- [ ] Webhook Verify Token (নিজে তৈরি করবেন)
- [ ] App Secret (Webhook Secret)

---

## 🚀 Step-by-Step Guide

### ✅ Step 1: Meta Business Manager Account তৈরি করুন

**URL:** https://business.facebook.com

1. Facebook account দিয়ে login করুন
2. "Create Account" button এ click করুন
3. Business name এবং information দিন
4. Account তৈরি হয়ে গেলে এগিয়ে যান

---

### ✅ Step 2: WhatsApp Business App তৈরি করুন

**URL:** https://developers.facebook.com/apps/

#### 2.1 Create New App
1. "Create App" button এ click করুন
2. App type: **"Business"** select করুন
3. App name দিন (যেমন: "CNPI WhatsApp Bot")
4. Business Account select করুন
5. "Create App" এ click করুন

#### 2.2 WhatsApp Product Add করুন
1. Dashboard এ "Add Products" section দেখুন
2. **"WhatsApp"** খুঁজুন
3. "Set Up" button এ click করুন

---

### 🔐 Step 3: API Token সংগ্রহ করুন

**URL:** https://business.facebook.com/settings/system-users

#### Steps:
1. Meta Business Manager এ যান
2. Left sidebar → **"System Users"** এ click করুন
3. "Add" button এ click করুন (নতুন System User তৈরি করতে)
4. Name দিন: "WhatsApp Bot Service"
5. Role: **"Admin"** select করুন
6. "Create System User" এ click করুন

#### Token Generate করুন:
1. আপনার System User এর পাশে **"Generate New Token"** button এ click করুন
2. App select করুন: আপনার WhatsApp App
3. **Permissions select করুন:**
   - ✅ `whatsapp_business_management`
   - ✅ `whatsapp_business_messaging`
4. "Generate Token" এ click করুন
5. **Token copy করুন** (এটি শুধুমাত্র একবার দেখাবে!)
   - Token format: `EAABsbCS1iHg...` (অনেক লম্বা)
6. এই token টি `.env` file এ `WHATSAPP_API_TOKEN` এ paste করুন

```bash
WHATSAPP_API_TOKEN=EAABsbCS1iHgBO7ZCwqwHfM8ZBGxqX9l3N2V...
```

---

### 📱 Step 4: Phone Number ID সংগ্রহ করুন

**URL:** https://developers.facebook.com/apps/ → Your App

#### Steps:
1. Developer Console এ যান
2. আপনার WhatsApp App select করুন
3. Left sidebar → **"WhatsApp"** → **"API Setup"** এ click করুন
4. "From" section দেখুন
5. আপনার phone number এর নিচে **"Phone number ID"** থাকবে
   - এটি দেখতে: `123456789012345` (15-digit number)
6. Copy করুন এবং `.env` এ paste করুন

```bash
WHATSAPP_PHONE_NUMBER_ID=123456789012345
```

**নোট:** Test number ব্যবহার করতে পারবেন প্রথমে, পরে production number add করতে পারবেন।

---

### 🔒 Step 5: Webhook Verify Token তৈরি করুন

এটি **আপনি নিজে তৈরি করবেন** - যেকোনো secure random string।

#### Option 1: Manual
```bash
WHATSAPP_WEBHOOK_VERIFY_TOKEN=cnpi_whatsapp_2026_secure_verify_token_abc123
```

#### Option 2: Random Generate করুন
PowerShell এ run করুন:
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

এই token টি:
- `.env` file এ রাখুন
- পরে webhook setup করার সময়ও এই same token দিতে হবে

```bash
WHATSAPP_WEBHOOK_VERIFY_TOKEN=আপনার_তৈরি_করা_secure_token
```

---

### 🔐 Step 6: App Secret (Webhook Secret) সংগ্রহ করুন

**URL:** https://developers.facebook.com/apps/ → Your App

#### Steps:
1. Developer Console এ যান
2. আপনার WhatsApp App select করুন
3. Left sidebar → **"Settings"** → **"Basic"** এ click করুন
4. "App Secret" field খুঁজুন
5. **"Show"** button এ click করুন
6. Facebook password দিয়ে verify করুন
7. **Secret copy করুন**
8. `.env` এ paste করুন

```bash
WHATSAPP_WEBHOOK_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

## 📝 Final `.env` File Example

এখন আপনার `.env` file এ সব values এরকম দেখাবে:

```bash
# WhatsApp Bot Configuration
WHATSAPP_API_TOKEN=EAABsbCS1iHgBO7ZCwqwHfM8ZBGxqX9l3N2VZAExample
WHATSAPP_PHONE_NUMBER_ID=109876543210123
WHATSAPP_WEBHOOK_VERIFY_TOKEN=cnpi_whatsapp_2026_secure_verify_token
WHATSAPP_WEBHOOK_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
WHATSAPP_API_VERSION=v18.0

# RAG API Configuration
RAG_API_URL=http://127.0.0.1:8000/api/chat/
RAG_API_TIMEOUT=60
```

---

## 🌐 Webhook Setup (পরবর্তী পদক্ষেপ)

Credentials সংগ্রহের পরে webhook setup করতে হবে:

### Prerequisites:
- আপনার Django app publicly accessible হতে হবে (HTTPS)
- Development এর জন্য **ngrok** ব্যবহার করতে পারেন

### Webhook URL:
```
https://your-domain.com/api/whatsapp/webhook/
```

### Setup Steps:
1. **Developer Console** → Your App → **WhatsApp** → **Configuration**
2. "Webhook" section এ "Edit" click করুন
3. **Callback URL:** আপনার webhook URL দিন
4. **Verify Token:** আপনার `WHATSAPP_WEBHOOK_VERIFY_TOKEN` দিন
5. "Verify and Save" click করুন
6. **Webhook Fields** subscribe করুন:
   - ✅ `messages`

---

## 🧪 Test করুন

Credentials setup হয়ে গেলে test করুন:

```bash
# 1. Health check করুন
curl http://localhost:8000/api/whatsapp/health/

# 2. Configuration check করুন
python manage.py shell
>>> from whatsapp_bot.whatsapp_service import get_whatsapp_service
>>> service = get_whatsapp_service()
>>> print("Token:", "✅ Set" if service.api_token else "❌ Missing")
>>> print("Phone ID:", "✅ Set" if service.phone_number_id else "❌ Missing")
>>> print("Verify Token:", "✅ Set" if service.webhook_verify_token else "❌ Missing")
>>> print("Secret:", "✅ Set" if service.webhook_secret else "❌ Missing")
```

---

## 📞 Support Resources

- **WhatsApp Business API Docs:** https://developers.facebook.com/docs/whatsapp
- **Getting Started Guide:** https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
- **Meta Business Help:** https://www.facebook.com/business/help

---

## ⚠️ Security Tips

1. ❌ **কখনো** `.env` file git এ commit করবেন না
2. ✅ `.gitignore` এ `.env` add করুন
3. ✅ Production এ strong tokens ব্যবহার করুন
4. ✅ Tokens কাউকে share করবেন না
5. ✅ Regular interval এ tokens rotate করুন

---

## ✅ Quick Checklist

সব setup complete হলে এগুলো check করুন:

- [ ] `.env` file এ সব variables আছে
- [ ] Health check endpoint respond করছে
- [ ] Database migration সম্পন্ন হয়েছে
- [ ] Django app running আছে
- [ ] Webhook publicly accessible (ngrok/production)
- [ ] Webhook verified হয়েছে Meta তে
- [ ] Test message পাঠিয়ে response পেয়েছি

---

**শুভকামনা!** 🎉 কোনো সমস্যা হলে README.md এর Troubleshooting section দেখুন।
