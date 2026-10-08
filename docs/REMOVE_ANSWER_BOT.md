# Facebook Messenger Integration - Complete Guide

এই গাইড আপনাকে দেখাবে কীভাবে:
1. Answer Bot remove করবেন Django থেকে
2. Meta Developer App থেকে disconnect করবেন
3. Facebook Page থেকে remove করবেন

---

## 🗑️ Part 1: Django থেকে Answer Bot Remove

### ✅ সম্পন্ন হয়েছে:

1. **settings.py** - INSTALLED_APPS থেকে 'answer_bot' comment করা হয়েছে
2. **urls.py** - answer_bot routes comment করা হয়েছে
3. **logging** - answer_bot logger comment করা হয়েছে

### Deploy করুন:

```bash
# Render automatically deploy করবে
# অথবা local test করুন:
cd cnpi_api
python manage.py check
python manage.py runserver
```

---

## 🔌 Part 2: Meta Developer App থেকে Disconnect

### Option A: Meta Developer Dashboard (Recommended)

1. **Meta for Developers** এ যান:
   - https://developers.facebook.com/

2. **Your Apps** → আপনার Answer Bot app select করুন

3. **Settings** → **Basic** এ যান

4. **দুটি উপায়:**

   **A. Webhook URL মুছে দিন:**
   - Messenger → Settings → Webhooks
   - Callback URL field খালি করে দিন
   - Verify Token মুছে দিন
   - Save করুন

   **B. App সম্পূর্ণ Delete করুন:**
   - Settings → Basic
   - একদম নিচে scroll করুন
   - **Delete App** button
   - App name type করে confirm করুন

### Option B: Facebook Page Settings

যদি শুধু Page থেকে disconnect করতে চান:

1. **Facebook Page Settings** এ যান
2. **Advanced Messaging** বা **Messaging** tab
3. **Connected Apps** দেখুন
4. Answer Bot app খুঁজে বের করুন
5. **Remove** বা **Disconnect** click করুন

---

## 📱 Part 3: Facebook Page থেকে Permissions Remove

### Step 1: Page Settings

1. আপনার **Facebook Page** এ যান
2. **Settings** → **Privacy and Safety** (বা **Advanced Settings**)
3. **Apps and Websites** section
4. Answer Bot app খুঁজুন
5. **Remove** click করুন

### Step 2: Personal Facebook Account Settings

যদি আপনার personal account-এ Answer Bot connected থাকে:

1. Facebook → **Settings & Privacy** → **Settings**
2. **Security and Login** → **Apps and Websites**
3. Answer Bot খুঁজুন
4. **Remove** button click করুন

### Step 3: Meta Business Suite (যদি ব্যবহার করেন)

1. **Meta Business Suite** (business.facebook.com) এ যান
2. **Settings** → **Integrations**
3. Answer Bot app খুঁজুন
4. **Disconnect** করুন

---

## ✅ Verification - সব ঠিক আছে কিনা Check করুন

### 1. Django Check:

```bash
cd cnpi_api
python manage.py check
```

Expected output:
```
System check identified no issues (0 silenced).
```

### 2. No More Answer Bot Errors:

এখন logs-এ আর এই error দেখা যাবে না:
```
ERROR answer_bot.views: Missing required setting: ANSWER_BOT_APP_SECRET
```

### 3. Fiwano Still Working:

Facebook Messenger থেকে message পাঠান। Fiwano bot ঠিকমতো কাজ করবে।

---

## 🎯 এখন শুধু Fiwano ব্যবহার করবেন

### Active Integration:

✅ **Fiwano Bot** (নতুন)
- Endpoint: `/api/fiwano/webhook/`
- No Meta Developer App needed
- No 50-user limit
- Working perfectly!

### Removed:

❌ **Answer Bot** (পুরনো)
- Endpoint: `/answer-webhook` (disabled)
- Required Meta Developer App
- 50-user tester limit
- Now removed

---

## 🔐 Environment Variables Clean Up

আপনার `.env` file থেকে এগুলো **optional** করে দিতে পারেন (মুছবেন না, কারণ code এখনো আছে):

```bash
# Answer Bot - NO LONGER USED (can be empty)
ANSWER_BOT_VERIFY_TOKEN=
ANSWER_BOT_APP_SECRET=
ANSWER_BOT_PAGE_ACCESS_TOKEN=
ANSWER_BOT_ALLOWED_PSIDS=
```

### Keep these (Active):

```bash
# Fiwano - ACTIVE
FIWANO_API_KEY=mip_live_xxxxxxxxx
FIWANO_WEBHOOK_SECRET=your_secret
FIWANO_API_BASE_URL=https://fiwano.com/api/v1
```

---

## 📊 সারসংক্ষেপ

### Django থেকে removed:
- ✅ INSTALLED_APPS থেকে comment
- ✅ URLs থেকে comment
- ✅ Logging থেকে comment

### Meta/Facebook থেকে remove করতে হবে:
1. ⏳ Meta Developer Dashboard → Webhook URL মুছুন বা App delete করুন
2. ⏳ Facebook Page Settings → Connected Apps থেকে remove করুন
3. ⏳ Personal Facebook → Apps and Websites থেকে remove করুন

### Active System:
- ✅ **Fiwano Integration** working perfectly
- ✅ No 50-user limit
- ✅ No Meta App Review needed
- ✅ Production ready!

---

## 🎉 Congratulations!

আপনি এখন:
- ✅ পুরনো Answer Bot system সম্পূর্ণ remove করেছেন
- ✅ নতুন Fiwano system ব্যবহার করছেন
- ✅ Unlimited users support করতে পারবেন
- ✅ No Meta complications!

**Questions?** Documentation দেখুন: `docs/fiwano-facebook-messenger.md`
