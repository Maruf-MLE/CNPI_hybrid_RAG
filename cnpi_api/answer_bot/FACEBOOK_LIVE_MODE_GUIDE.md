# Facebook App Review - Live Mode Setup Guide

## ✅ Privacy Policy & Terms Created

Privacy Policy এবং Terms of Service pages successfully deployed হয়েছে!

### URLs:
- **Privacy Policy:** https://cnpichat.netlify.app/privacy
- **Terms of Service:** https://cnpichat.netlify.app/terms

---

## 📋 Meta Dashboard Setup Steps

### Step 1: Add Privacy Policy URL

1. **Go to Meta for Developers:** https://developers.facebook.com/
2. **Select CNGPIchat App**
3. **Settings → Basic**
4. Scroll to **Privacy Policy URL** field
5. **Enter:**
   ```
   https://cnpichat.netlify.app/privacy
   ```
6. **Terms of Service URL** (Optional but recommended):
   ```
   https://cnpichat.netlify.app/terms
   ```
7. Click **Save Changes**

---

### Step 2: Request Advanced Access for `pages_messaging`

1. **Go to:** App Dashboard → App Review → Permissions and Features
2. **Find:** `pages_messaging`
3. **Click:** Request Advanced Access

**You'll need to provide:**

#### A. App Information
```
App Name: CNGPIchat
App Purpose: Educational chatbot for Cumilla Polytechnic Institute (CNPI) students
Use Case: AI-powered Q&A bot to answer questions about departments, teachers, classes, labs
```

#### B. Tell us how your app uses this permission
```
CNGPIchat is an AI-powered chatbot that helps students, faculty, and staff of 
Cumilla Polytechnic Institute (CNPI) get instant answers about:

- Department information (CST, Civil, Electrical, etc.)
- Teacher contact details and office hours
- Class routines and schedules
- Lab information and equipment
- Admission requirements and fees
- Campus facilities

The bot uses Retrieval-Augmented Generation (RAG) technology with Google Gemini 
AI to provide accurate, context-aware responses. All conversations are session-based 
and automatically deleted after 1 hour.

We need pages_messaging permission to:
1. Receive user questions via Facebook Messenger
2. Send AI-generated answers back to users
3. Maintain conversation context for multi-turn interactions

Privacy: We do NOT store personal user information. Only message IDs are temporarily 
stored for duplicate prevention (30 days). See our privacy policy at:
https://cnpichat.netlify.app/privacy
```

#### C. Screenshots/Video

**Screenshot 1: Conversation Example**
Take a screenshot showing:
```
User: CST er CI ke?
Bot: CST Department-এর Chief Instructor হলেন মোঃ আব্দুল কাদের...
```

**Screenshot 2: Web Interface**
Screenshot of https://cnpichat.netlify.app

**Optional Video:**
Record a 30-second screen recording showing:
1. User opens Facebook Messenger
2. Sends question to CNGPIchat page
3. Bot responds with answer
4. User asks follow-up question
5. Bot maintains context and answers

---

### Step 3: Submit for Review

1. **Review your submission:**
   - ✅ Privacy Policy URL added
   - ✅ App description clear
   - ✅ Screenshots uploaded
   - ✅ Use case explained

2. **Click:** Submit for Review

3. **Wait:** 1-3 business days for approval

---

## 🎯 After Approval

When Facebook approves `pages_messaging`:

### Switch to Live Mode

1. **App Dashboard → Top-right corner**
2. **Click:** Mode toggle (Development → Live)
3. **Confirm:** Switch to Live Mode

**Your bot will now be public!** 🎉

---

## 📊 Current Status

| Task | Status |
|------|--------|
| Privacy Policy created | ✅ Done |
| Terms of Service created | ✅ Done |
| Footer links added | ✅ Done |
| Deployed to Netlify | ✅ Done |
| Privacy URL: https://cnpichat.netlify.app/privacy | ✅ Live |
| Terms URL: https://cnpichat.netlify.app/terms | ✅ Live |
| Meta Dashboard - Add Privacy URL | ⏳ Pending |
| Request pages_messaging permission | ⏳ Pending |
| Submit for App Review | ⏳ Pending |
| Switch to Live Mode | ⏳ After approval |

---

## 🚀 Quick Actions (Do Now)

### 1. Verify URLs Work
```bash
# Open in browser:
https://cnpichat.netlify.app/privacy
https://cnpichat.netlify.app/terms
```

### 2. Add to Meta Dashboard
```
Settings → Basic → Privacy Policy URL
https://cnpichat.netlify.app/privacy

Settings → Basic → Terms of Service URL (optional)
https://cnpichat.netlify.app/terms
```

### 3. Request pages_messaging
```
App Review → Permissions and Features → pages_messaging → Request Advanced Access
```

### 4. Test Bot (Development Mode)
```
1. Add yourself as Tester: App Dashboard → Roles → Add Testers
2. Send test message to CNGPIchat page
3. Verify bot responds correctly
```

---

## 📝 Sample App Review Submission

**App Category:** Education  
**Platform:** Facebook Messenger  

**Description:**
```
CNGPIchat is an educational chatbot for Cumilla Polytechnic Institute (CNPI) 
in Bangladesh. It helps 5000+ students and faculty members access institutional 
information instantly through natural language Q&A.

Features:
- 24/7 availability for student queries
- Multi-language support (Bengali & English)
- Department, teacher, and facility information
- Class schedules and academic calendar
- AI-powered with RAG technology

Privacy: Session-based, no personal data storage. GDPR-compliant.
```

**Website:** https://cnpichat.netlify.app  
**Privacy Policy:** https://cnpichat.netlify.app/privacy  
**Support Email:** hmaruf291@gmail.com

---

## ✅ Final Checklist

Before submitting:

- [ ] Privacy Policy URL added to Meta Dashboard
- [ ] Terms URL added (optional)
- [ ] App icon uploaded (1024x1024 PNG)
- [ ] App description written
- [ ] Screenshots prepared (2-3 images)
- [ ] Test bot working in Development Mode
- [ ] All webhook fields subscribed (messages, messaging_postbacks)
- [ ] Webhook URL verified

---

## 🆘 Troubleshooting

### Privacy Policy not loading?
- Check Netlify deploy status: https://app.netlify.com/
- Wait 2-3 minutes for DNS propagation
- Clear browser cache

### App Review rejected?
Common reasons:
- Privacy Policy incomplete → We have complete policy ✅
- App purpose unclear → Add more detail
- Screenshots missing → Upload clear images
- Webhook not working → Test first

### Still in Development Mode?
- pages_messaging requires Advanced Access for Live Mode
- Submit App Review first
- Wait for approval (1-3 business days)
- Then switch to Live

---

**Created:** 2026-10-07  
**Deploy Status:** ✅ Live  
**Next Step:** Add Privacy URL to Meta Dashboard
