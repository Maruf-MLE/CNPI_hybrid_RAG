# Answer Bot - Facebook Credentials Setup Guide

এই guide অনুসরণ করে Answer Bot এর জন্য Facebook credentials পাবেন।

---

## 📋 Step-by-Step Setup

### Step 1: Facebook Page তৈরি করুন

1. **Facebook-এ যান:** https://facebook.com
2. **Create Page** ক্লিক করুন (বা existing page ব্যবহার করুন)
3. Page name দিন: `CNPI Answer Bot` (বা যেকোনো নাম)
4. Category: `Education` বা `Science & Technology`
5. Page তৈরি হলে, Page ID নোট করুন

---

### Step 2: Meta Developer App তৈরি করুন

1. **Meta for Developers-এ যান:** https://developers.facebook.com/
2. **My Apps** > **Create App** ক্লিক করুন
3. **App Type:** `Business` (or `Other`) সিলেক্ট করুন
4. **App Name:** `CNPI Answer Bot App`
5. **App Contact Email:** আপনার email
6. **Create App** ক্লিক করুন

---

### Step 3: Messenger Product যোগ করুন

1. App Dashboard-এ **Add Product** সেকশনে যান
2. **Messenger** খুঁজে **Set Up** ক্লিক করুন
3. Messenger Settings page খুলবে

---

## 🔑 Credentials সংগ্রহ করুন

### 1️⃣ ANSWER_BOT_APP_SECRET

**কোথায় পাবেন:**
```
App Dashboard > Settings > Basic > App Secret
```

**Steps:**
1. Left sidebar-এ **Settings** > **Basic** ক্লিক করুন
2. **App Secret** field খুঁজুন (লুকানো থাকবে)
3. **Show** button ক্লিক করুন
4. Facebook password দিয়ে verify করুন
5. App Secret কপি করুন (এটা গোপন রাখবেন!)

**Example:**
```bash
ANSWER_BOT_APP_SECRET=c305f2981fc7d328db653e91d93ba5fe
```

---

### 2️⃣ ANSWER_BOT_PAGE_ACCESS_TOKEN

**কোথায় পাবেন:**
```
App Dashboard > Messenger > Settings > Access Tokens
```

**Steps:**
1. Left sidebar-এ **Messenger** > **Settings** যান
2. **Access Tokens** section খুঁজুন
3. **Add or Remove Pages** ক্লিক করুন
4. আপনার Page সিলেক্ট করুন এবং **Continue** ক্লিক করুন
5. Permissions দিন: `pages_messaging`, `pages_read_engagement`, `pages_manage_metadata`
6. **Done** ক্লিক করুন
7. Page এর পাশে **Generate Token** ক্লিক করুন
8. Token কপি করুন (দীর্ঘ string, শুরু হয় `EAA...`)

**Important:** 
- এটা **Page Access Token**, User Access Token নয়!
- Token expire হয় না (never expires) — এটা নিশ্চিত করুন

**Example:**
```bash
ANSWER_BOT_PAGE_ACCESS_TOKEN=EAAWc3pczaFIBSgpwIVgq2zCmSZCfSqyRJjSYnDiRCcOP55bcxTv2mKSZB7EZBZCp1dciZBsU70hQslPdrcAOtBYCz4cUxRS5GmrcpYvcMB7bxcBwlSC9sSZAGTIDE66B939FMKry2wJjtr7wF7dvZA3ZBwh9qPRNOkozuZCqbDXa6EGZCPRhUWhAZCQBycMllZAWZBpHSDmTBUw3dKwZDZD
```

---

### 3️⃣ ANSWER_BOT_VERIFY_TOKEN

**কোথায় পাবেন:**
এটা আপনি নিজে তৈরি করবেন! Facebook দেয় না।

**Generate করুন:**

**Option A: Python দিয়ে (Recommended)**
```bash
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

**Output Example:**
```
cnpi_answer_Xk29fLq7
```

**Option B: Manual**
যেকোনো random string (a-z, A-Z, 0-9, dash, underscore):
```
answer_bot_secure_token_2026
```

**Example:**
```bash
ANSWER_BOT_VERIFY_TOKEN=cnpi_answer_Xk29fLq7
```

⚠️ **Important:** এই token Meta Dashboard-এ webhook setup করার সময় লাগবে (পরে দেখাবো)

---

### 4️⃣ ANSWER_BOT_ALLOWED_PSIDS

**কী এটা:**
Page-Scoped User IDs (PSID) — নির্দিষ্ট users-এর ID যারা bot ব্যবহার করতে পারবে।

**সবার জন্য allow করতে:**
```bash
ANSWER_BOT_ALLOWED_PSIDS=
```
(খালি রাখুন — already configured ✅)

**শুধু নির্দিষ্ট users (Optional):**
```bash
ANSWER_BOT_ALLOWED_PSIDS=123456789,987654321
```

**PSID কীভাবে পাবেন:**
1. কেউ bot-এ message পাঠালে log-এ দেখাবে:
   ```
   Processing message from PSID 7234567890123456 (all users allowed)
   ```
2. বা Messenger webhook test করলে payload-এ `sender.id` দেখাবে

---

## 🔧 .env File Update করুন

এখন সব credentials একসাথে `.env` file-এ যোগ করুন:

**Edit:** `G:\CNPI_Hybrid_RAG\.env`

```bash
# Answer Bot Webhook (RAG-powered Q&A Bot)
ANSWER_BOT_VERIFY_TOKEN=cnpi_answer_Xk29fLq7
ANSWER_BOT_APP_SECRET=7c3a6f1c5ee1ca42569fa51cc526fc84
ANSWER_BOT_PAGE_ACCESS_TOKEN=EAAW426IeNhIBSsgUuVXrwXA23oVpgtqyP3V00AcQuKMidGZAJnMMavcUTcblvKT2xEYfY17N8JmaqDWlStpZBQ3j0TMMhpR3fsEZACeL5lDD2uDq3yRdaED9VBcgMyA12C8l7EDrFhAotVmfY6ViTzXQ76xjXeVPMyf3VHOuHQdNeMVzco5fx6XSkoj4UqHSVNuGBZATXAZDZD
ANSWER_BOT_ALLOWED_PSIDS=
RAG_API_URL=https://cnpi-hybrid-rag-1.onrender.com/api/chat/
```

⚠️ **Note:** উপরের values শুধু example — আপনার actual credentials ব্যবহার করবেন!

---

## 🌐 Webhook Setup (Next Step)

Credentials পাওয়ার পর, webhook configure করতে হবে:

### Local Testing (ngrok)

1. **Start Django server:**
   ```bash
   cd cnpi_api
   python manage.py runserver
   ```

2. **Start ngrok:**
   ```bash
   ngrok http 8000
   ```
   
   Output:
   ```
   Forwarding: https://abc123.ngrok.io -> http://localhost:8000
   ```

3. **Meta Dashboard > Messenger > Settings > Webhooks:**
   - **Callback URL:** `https://abc123.ngrok.io/answer-webhook/`
   - **Verify Token:** `cnpi_answer_Xk29fLq7` (আপনার ANSWER_BOT_VERIFY_TOKEN)
   - **Subscribed Fields:** `messages`, `messaging_postbacks`
   - Click **Verify and Save**

### Production (Render)

1. **Render Dashboard > Environment Variables:**
   ```bash
   ANSWER_BOT_VERIFY_TOKEN=cnpi_answer_Xk29fLq7
   ANSWER_BOT_APP_SECRET=7c3a6f1c5ee1ca42569fa51cc526fc84
   ANSWER_BOT_PAGE_ACCESS_TOKEN=EAAWc3p...
   ANSWER_BOT_ALLOWED_PSIDS=
   RAG_API_URL=https://cnpi-hybrid-rag-1.onrender.com/api/chat/
   ```

2. **Meta Dashboard > Webhooks:**
   - **Callback URL:** `https://cnpi-hybrid-rag-1.onrender.com/answer-webhook/`
   - **Verify Token:** `cnpi_answer_Xk29fLq7`
   - Click **Verify and Save**

---

## ✅ Verification Checklist

প্রতিটা credential পাওয়ার পর check করুন:

- [ ] **ANSWER_BOT_APP_SECRET** — Settings > Basic > App Secret থেকে পাওয়া
- [ ] **ANSWER_BOT_PAGE_ACCESS_TOKEN** — Messenger > Settings > Generate Token থেকে পাওয়া
- [ ] **ANSWER_BOT_VERIFY_TOKEN** — নিজে generate করা (secrets.token_urlsafe)
- [ ] **ANSWER_BOT_ALLOWED_PSIDS** — খালি রাখা (all users allowed)
- [ ] `.env` file update করা
- [ ] Webhook URL configured করা Meta Dashboard-এ
- [ ] Test message পাঠিয়ে verify করা

---

## 🧪 Test করুন

1. **Server চালু করুন:**
   ```bash
   cd cnpi_api
   python manage.py runserver
   ```

2. **Facebook Page-এ message পাঠান:**
   ```
   CST er CI ke?
   ```

3. **Log check করুন:**
   ```
   INFO answer_bot: Processing message from PSID xxx (all users allowed)
   INFO answer_bot: Sent answer to PSID xxx — status=found answer_len=125
   ```

4. **Bot থেকে reply আসবে:**
   ```
   CST Department-এর Chief Instructor হলেন মোঃ আব্দুল কাদের...
   ```

---

## 🆘 Troubleshooting

### App Secret দেখতে পাচ্ছি না
- **Show** button ক্লিক করুন
- Facebook password দিয়ে verify করুন
- App Dashboard > Settings > Basic-এ আছে

### Page Access Token generate হচ্ছে না
- Page-কে App-এ connect করেছেন কিনা check করুন
- Permissions দিয়েছেন কিনা: `pages_messaging`, `pages_read_engagement`
- **Add or Remove Pages** button ক্লিক করে page add করুন

### Webhook verification failed
- **Verify Token** match করছে কিনা check করুন (.env এবং Meta Dashboard)
- URL শেষে `/` আছে কিনা: `/answer-webhook/`
- Server running আছে কিনা check করুন

---

## 📚 Reference Links

- **Meta for Developers:** https://developers.facebook.com/
- **Messenger Platform Docs:** https://developers.facebook.com/docs/messenger-platform
- **Webhook Setup Guide:** https://developers.facebook.com/docs/messenger-platform/webhooks
- **Access Tokens Guide:** https://developers.facebook.com/docs/facebook-login/guides/access-tokens

---

**Updated:** 2026-10-07  
**Guide Version:** 1.0
