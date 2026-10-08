# Debug Checklist - Answer Bot Not Working

## ✅ Done
- [x] Environment variables added to Render
- [x] Service restarted
- [x] Webhook verification successful (GET request worked)

## ❌ Problem
- [ ] POST request not coming (user messages not reaching webhook)
- [ ] No logs when sending message to page

## 🔍 Root Cause: Page NOT Subscribed to Webhook

### This is the CRITICAL step you're missing:

In Meta Dashboard, you need to **SUBSCRIBE YOUR PAGE** to the webhook.

Webhook verification (GET) ≠ Page subscription (POST)

---

## 🚀 SOLUTION: Subscribe Page to Webhook

### Step 1: Go to Webhooks Section

```
Meta Dashboard → CNGPIchat App → Messenger → Settings → Webhooks
```

You should see:
```
✅ Callback URL: https://cnpi-hybrid-rag-1.onrender.com/answer-webhook/
✅ Verify Token: Verified
⚠️ No pages subscribed OR wrong page subscribed
```

### Step 2: Check Current Page Subscriptions

Look for a section that says:
- **"Subscribed Pages"** or
- **"Add Page Subscription"** or
- **"Select Page"**

**Screenshot location in Meta Dashboard:**
```
Messenger Settings
  └─ Webhooks
      ├─ Callback URL ✅
      ├─ Verify Token ✅
      └─ Page Subscriptions ⚠️ ← THIS IS THE PROBLEM
```

### Step 3: Add Your Page

Click **"Add Subscriptions"** or **"Select a Page"**

You'll see a modal with:
```
┌──────────────────────────────────────┐
│ Edit Page Subscriptions              │
│                                      │
│ Your Page Name                       │
│ 714316161776174                      │
│                                      │
│ ☐ messages                           │
│ ☐ messaging_postbacks                │
│ ☐ messaging_optins                   │
│ ☐ message_deliveries                 │
│ ... (more fields)                    │
│                                      │
│         [Cancel]  [Confirm]          │
└──────────────────────────────────────┘
```

### Step 4: Check These 3 Fields

**MUST CHECK:**
```
☑️ messages
☑️ messaging_postbacks
☑️ messaging_optins
```

**Optional but recommended:**
```
☑️ message_deliveries
☑️ message_reads
```

### Step 5: Click Confirm

After clicking Confirm, you should see:
```
Subscribed Pages:
✅ Your Page Name (714316161776174)
   Fields: messages, messaging_postbacks, messaging_optins
```

---

## 🧪 Test Again

### 1. Send Test Message
```
Message to page: "test"
```

### 2. Check Render Logs
You should NOW see:
```
INFO answer_bot: Answer Bot Webhook POST — path=/answer-webhook/ sig_present=True body_len=xxx
INFO answer_bot: Processing message from PSID xxx (all users allowed)
```

### 3. If Still No Logs
Check these:

#### A. Wrong Webhook URL?
```
Meta Dashboard → Messenger → Settings → Webhooks → Callback URL

Should be: https://cnpi-hybrid-rag-1.onrender.com/answer-webhook/
NOT: https://cnpi-hybrid-rag-1.onrender.com/webhook/
```

#### B. Page Subscribed to OLD Webhook?
```
If you have TWO webhooks configured:
- /webhook/ (old)
- /answer-webhook/ (new)

The page might be subscribed to the OLD one.

Fix:
1. Remove page subscription from /webhook/
2. Add page subscription to /answer-webhook/
```

#### C. App in Development Mode + You're Not a Tester?
```
Check:
1. App Dashboard → Roles → Roles
2. Add yourself as "Tester" or "Admin"
3. Accept the invitation on Facebook
```

---

## 📸 Screenshot Guide

### Where to Find Page Subscription:

**Path 1: Via Messenger Settings**
```
Meta Developer Dashboard
  └─ Your App (CNGPIchat)
      └─ Products
          └─ Messenger
              └─ Settings
                  └─ Webhooks
                      └─ Edit Page Subscriptions ← CLICK HERE
```

**Path 2: Via Webhooks**
```
App Dashboard
  └─ App Settings
      └─ Webhooks
          └─ (Select "Page" from dropdown)
              └─ Edit Subscriptions ← CLICK HERE
```

---

## 🔧 Alternative Method: Use Graph API Explorer

If you can't find the Page Subscription UI:

### 1. Go to Graph API Explorer
```
https://developers.facebook.com/tools/explorer/
```

### 2. Select Your App
```
Top-right dropdown → CNGPIchat
```

### 3. Get Page Access Token
```
User or Page → Select your page → Get Token
```

### 4. Subscribe Page to Webhook
```
Method: POST
Endpoint: /{page-id}/subscribed_apps

Click "Submit"
```

### 5. Verify Subscription
```
Method: GET
Endpoint: /{page-id}/subscribed_apps

Response should show:
{
  "data": [
    {
      "id": "your_app_id",
      "subscribed_fields": ["messages", "messaging_postbacks", ...]
    }
  ]
}
```

---

## ⚡ Quick Test Command

Test webhook directly from command line:

### Test GET (Verification) - Should work ✅
```bash
curl "https://cnpi-hybrid-rag-1.onrender.com/answer-webhook/?hub.mode=subscribe&hub.verify_token=cnpi_bot_Xk29fLq7&hub.challenge=test123"
```

**Expected:** Returns `test123`

### Test POST (Message) - Test locally
```bash
# This won't work from curl (needs valid signature)
# Only Meta can send valid POST requests
```

---

## 📋 Final Checklist

- [ ] Render environment variables correct ✅ (you did this)
- [ ] Service restarted ✅
- [ ] Webhook URL verified ✅ (GET request worked)
- [ ] **PAGE SUBSCRIBED TO WEBHOOK** ⚠️ ← DO THIS NOW
- [ ] Subscribed fields include "messages" ⚠️
- [ ] You are added as Tester/Admin in app
- [ ] Test message sent to correct page

---

## 🆘 If Still Not Working

Send me:

1. **Screenshot of Meta Dashboard → Messenger → Settings → Webhooks section**
   - Show Callback URL
   - Show Subscribed Pages
   - Show Subscribed Fields

2. **Render logs** after sending test message

3. **Confirm:**
   - Which page are you sending message to?
   - Page ID: 714316161776174?
   - App ID: 1381144998410514?
   - Are you an Admin/Tester of the app?

---

**Most Common Issue:** Page not subscribed to webhook!

Go to Meta Dashboard NOW and find "Edit Page Subscriptions" button! 🚀
