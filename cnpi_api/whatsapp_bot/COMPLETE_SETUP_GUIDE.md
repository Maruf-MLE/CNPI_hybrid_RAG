# 🚀 WhatsApp Business API - শুরু থেকে Complete Setup Guide

একদম beginner friendly guide - প্রতিটি step বিস্তারিত ভাবে বোঝানো হয়েছে।

---

## 📋 Table of Contents

1. [Prerequisites (যা লাগবে)](#prerequisites)
2. [Part 1: Meta Business Account তৈরি](#part-1-meta-business-account)
3. [Part 2: Meta Developer Account Setup](#part-2-meta-developer-account)
4. [Part 3: WhatsApp App তৈরি](#part-3-whatsapp-app)
5. [Part 4: Phone Number Setup](#part-4-phone-number)
6. [Part 5: API Token নেওয়া](#part-5-api-token)
7. [Part 6: Phone Number ID নেওয়া](#part-6-phone-number-id)
8. [Part 7: App Secret নেওয়া](#part-7-app-secret)
9. [Part 8: Webhook Setup (ngrok সহ)](#part-8-webhook-setup)
10. [Part 9: Testing](#part-9-testing)

---

## <a name="prerequisites"></a>📦 Prerequisites (যা লাগবে)

### ✅ Check করুন আপনার কাছে আছে কিনা:

1. **Facebook Account**
   - Active Facebook account প্রয়োজন
   - Account টি verified হতে হবে (phone/email verified)

2. **Phone Number**
   - যেকোনো phone number (যেটা WhatsApp এ use করা নেই)
   - অথবা Meta test number ব্যবহার করতে পারবেন

3. **Email Address**
   - Business account এর জন্য

4. **Computer/Laptop**
   - Internet connection
   - Modern web browser (Chrome/Firefox recommended)

---

## <a name="part-1-meta-business-account"></a>🏢 Part 1: Meta Business Account তৈরি

### Step 1.1: Meta Business Suite এ যান

```
🌐 URL: https://business.facebook.com
```

1. Browser এ URL open করুন
2. আপনার **Facebook account** দিয়ে login করুন
3. যদি already logged in থাকেন তাহলে direct dashboard দেখাবে

---

### Step 1.2: Business Account তৈরি বা Select করুন

#### যদি আগে থেকে Business Account থাকে:
- Dashboard এ আপনার business account দেখতে পাবেন
- সেটা select করুন

#### যদি নতুন Business Account তৈরি করতে হয়:

1. **"Create Account"** button এ click করুন (top-right corner এ)

2. **Business Name দিন:**
   ```
   Example: CNPI Solutions
   Your Name: আপনার নাম
   Business Email: আপনার email
   ```

3. **Business Details:**
   - Business Category: Technology অথবা যা applicable
   - Website: (optional) আপনার website থাকলে দিন
   - Address: (optional)

4. **"Submit"** button এ click করুন

5. **Email Verification:**
   - আপনার email এ verification link যাবে
   - Email check করে verify করুন

✅ **Checkpoint:** এখন আপনার Meta Business Account ready!

---

## <a name="part-2-meta-developer-account"></a>👨💻 Part 2: Meta Developer Account Setup

### Step 2.1: Meta for Developers এ যান

```
🌐 URL: https://developers.facebook.com
```

1. URL open করুন
2. Top-right corner এ **"My Apps"** এ click করুন
3. যদি first time হয়, তাহলে **"Get Started"** button দেখাবে
4. **"Get Started"** এ click করুন

---

### Step 2.2: Developer Account Registration

1. **Choose Your Role:**
   - ✅ Select করুন: **"Developer"**

2. **Account Information:**
   - আপনার phone number দিন (verification এর জন্য)
   - Country select করুন
   - ✅ Agree to terms checkbox

3. **Phone Verification:**
   - SMS এ verification code পাঠাবে
   - Code enter করুন

4. **"Complete Registration"** click করুন

✅ **Checkpoint:** Meta Developer Account ready!

---

## <a name="part-3-whatsapp-app"></a>📱 Part 3: WhatsApp App তৈরি

### Step 3.1: New App তৈরি করুন

```
🌐 URL: https://developers.facebook.com/apps/
```

1. **"Create App"** button এ click করুন (green button, top-right)

---

### Step 3.2: Select Use Case

Screen এ বিভিন্ন options আসবে:

```
Options দেখাবে:
- Consumer
- Business  ← এটা select করুন ✅
- Gaming
- Other
```

**✅ Select করুন: "Business"**

**"Next"** button এ click করুন

---

### Step 3.3: Add App Details

1. **App Display Name:**
   ```
   Example: CNPI WhatsApp Bot
   ```
   - যেকোনো meaningful name দিন

2. **App Contact Email:**
   ```
   Example: your-email@example.com
   ```
   - আপনার email address

3. **Business Account:**
   - Dropdown থেকে আপনার business account select করুন
   - আগের step এ যেটা তৈরি করেছেন

4. **"Create App"** button এ click করুন

---

### Step 3.4: Security Check (যদি থাকে)

কখনো কখনো Meta security check করে:

1. Facebook password দিয়ে confirm করতে বলবে
2. Password দিন এবং confirm করুন

✅ **Checkpoint:** App তৈরি হয়ে গেছে! Dashboard দেখাবে।

---

### Step 3.5: WhatsApp Product Add করুন

App Dashboard এ আসার পরে:

1. **"Add Products"** section খুঁজুন (left sidebar অথবা main dashboard)

2. Product list এ **"WhatsApp"** খুঁজুন

3. WhatsApp এর পাশে **"Set Up"** button এ click করুন

4. Loading হবে কিছুক্ষণ...

5. WhatsApp setup screen আসবে

✅ **Checkpoint:** WhatsApp product added!

---

## <a name="part-4-phone-number"></a>☎️ Part 4: Phone Number Setup

### Step 4.1: Test Phone Number (Meta Provided)

WhatsApp setup screen এ আসার পরে:

1. **"API Setup"** tab এ যান (left sidebar → WhatsApp → API Setup)

2. **Test Number দেখাবে:**
   ```
   From: +1 555 XXX XXXX (Meta test number)
   Phone number ID: 123456789012345
   ```

3. এই test number দিয়ে প্রথমে testing করতে পারবেন
   - Limitations: শুধু 5টি number এ message পাঠাতে পারবেন

---

### Step 4.2: Test Recipients Add করুন

Test number ব্যবহার করতে হলে:

1. **"To"** section দেখুন
2. **"Add recipient phone number"** এ click করুন
3. আপনার WhatsApp number দিন (with country code)
   ```
   Example: +8801712345678
   ```
4. **"Send code via SMS"** button এ click করুন
5. SMS এ verification code পাবেন
6. Code enter করুন এবং verify করুন

✅ এখন এই number এ test message পাঠাতে পারবেন!

---

### Step 4.3: Production Phone Number Add (Later)

**Note:** Production এ যেতে হলে নিজের business phone number add করতে হবে।

এটা পরে করবেন, এখন test number দিয়ে continue করুন।

---

## <a name="part-5-api-token"></a>🔑 Part 5: API Token নেওয়া

এটা সবচেয়ে গুরুত্বপূর্ণ part! Carefully follow করুন।

### Step 5.1: Meta Business Manager এ যান

```
🌐 URL: https://business.facebook.com
```

1. আপনার business account select করুন
2. Left sidebar এ scroll করুন

---

### Step 5.2: System Users এ যান

Left sidebar এ:

```
Settings (gear icon) → System Users
```

**Full path:**
```
Business Settings → Users → System Users
```

---

### Step 5.3: New System User তৈরি করুন

1. **"Add"** button এ click করুন (top-right, blue button)

2. **System User Details:**
   ```
   System Username: whatsapp_bot_service
   System User Role: Admin ✅ (recommended)
   ```

3. **"Create System User"** button এ click করুন

---

### Step 5.4: Generate Access Token

এখন আপনার new system user দেখাবে list এ।

1. আপনার system user এর row এ **"Generate New Token"** button খুঁজুন

2. **"Generate New Token"** এ click করুন

---

### Step 5.5: Configure Token

Modal/popup window আসবে:

1. **App Select করুন:**
   - Dropdown থেকে আপনার WhatsApp app select করুন
   - যেটা আগে তৈরি করেছেন (CNPI WhatsApp Bot)

2. **Permissions Select করুন:**
   
   ⚠️ **Important:** দুটো permissions অবশ্যই দিতে হবে:
   
   ```
   ✅ whatsapp_business_management
   ✅ whatsapp_business_messaging
   ```
   
   Checkbox গুলো দেখুন এবং এই দুটো select করুন।

3. **Token Expiration:**
   - Options থাকবে: 60 days, Never expire
   - **Recommended:** 60 days (security জন্য)

4. **"Generate Token"** button এ click করুন

---

### Step 5.6: Copy Token (⚠️ CRITICAL)

⚠️ **খুবই গুরুত্বপূর্ণ:**

1. Screen এ একটি **long token** দেখাবে
   ```
   Format: EAABsbCS1iHgBO7ZCwqw...
   ```

2. **Token টি copy করুন** (copy icon এ click করুন)

3. ⚠️ **এই token শুধুমাত্র একবার দেখাবে!**
   - পরে আর দেখতে পারবেন না
   - এখনই একটি safe জায়গায় save করুন

4. Token টি আপনার `.env` file এ paste করুন:
   ```bash
   WHATSAPP_API_TOKEN=EAABsbCS1iHgBO7ZCwqw...
   ```

5. **"OK"** বা **"Done"** button এ click করুন

✅ **Checkpoint:** API Token পেয়ে গেছেন এবং `.env` এ save করেছেন!

---

## <a name="part-6-phone-number-id"></a>📞 Part 6: Phone Number ID নেওয়া

এটা খুবই সহজ!

### Step 6.1: Developer Console এ ফিরে যান

```
🌐 URL: https://developers.facebook.com/apps/
```

1. আপনার app select করুন (CNPI WhatsApp Bot)

---

### Step 6.2: API Setup Page এ যান

Left sidebar:
```
WhatsApp → API Setup
```

---

### Step 6.3: Phone Number ID Copy করুন

Screen এ দেখবেন:

```
┌─────────────────────────────────────┐
│ API Setup                            │
│                                      │
│ Step 1: Select phone number          │
│                                      │
│ From:  +1 555 XXX XXXX              │
│        Phone number ID: 123456...    │  ← এটা copy করুন!
│        [Copy icon]                   │
└─────────────────────────────────────┘
```

1. **"Phone number ID"** এর পাশে যে number আছে সেটা copy করুন
   - এটা একটা 15-digit number
   - Example: `109876543210123`

2. `.env` file এ paste করুন:
   ```bash
   WHATSAPP_PHONE_NUMBER_ID=109876543210123
   ```

✅ **Checkpoint:** Phone Number ID পেয়ে গেছেন!

---

## <a name="part-7-app-secret"></a>🔐 Part 7: App Secret নেওয়া

### Step 7.1: App Settings এ যান

Developer Console এ:

Left sidebar:
```
Settings → Basic
```

---

### Step 7.2: App Secret দেখুন

Page scroll করে **"App Secret"** field খুঁজুন:

```
┌────────────────────────────────┐
│ App Secret:  ••••••••••••••••  │
│              [Show] [Reset]    │
└────────────────────────────────┘
```

1. **"Show"** button এ click করুন

2. Facebook password দিয়ে verify করতে বলবে
   - আপনার Facebook password দিন
   - **"Submit"** click করুন

3. Secret দেখাবে:
   ```
   a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ```

4. Copy করুন (copy icon এ click করুন অথবা manually select করে copy)

5. `.env` file এ paste করুন:
   ```bash
   WHATSAPP_WEBHOOK_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ```

✅ **Checkpoint:** App Secret পেয়ে গেছেন!

---

## <a name="part-8-webhook-setup"></a>🌐 Part 8: Webhook Setup

এটা একটু technical, কিন্তু step-by-step follow করলে সহজ হবে।

### Step 8.1: Django Server Start করুন

প্রথমে আপনার local server ready করুন:

```bash
# Terminal/PowerShell open করুন
cd G:\CNPI_Hybrid_RAG\cnpi_api

# Server start করুন
python manage.py runserver 8000
```

Server চলতে থাকবে। **এই terminal বন্ধ করবেন না!**

---

### Step 8.2: ngrok Install করুন

Webhook এর জন্য public URL প্রয়োজন। Development এ ngrok ব্যবহার করবো।

#### Install Steps:

1. **Download ngrok:**
   ```
   🌐 URL: https://ngrok.com/download
   ```

2. **Windows এর জন্য:**
   - Download the ZIP file
   - Extract করুন যেকোনো folder এ
   - `ngrok.exe` file পাবেন

3. **Signup করুন (Free):**
   ```
   🌐 URL: https://dashboard.ngrok.com/signup
   ```

4. **Auth Token নিন:**
   - Login করার পরে: https://dashboard.ngrok.com/get-started/your-authtoken
   - Token copy করুন

5. **Auth Token Configure করুন:**
   ```bash
   # ngrok.exe যে folder এ আছে সেখানে terminal open করুন
   .\ngrok.exe config add-authtoken YOUR_TOKEN_HERE
   ```

---

### Step 8.3: ngrok Start করুন

**নতুন terminal/PowerShell** open করুন (আগেরটা চলতে দিন):

```bash
# ngrok folder এ যান
cd path\to\ngrok

# Port 8000 forward করুন
.\ngrok.exe http 8000
```

**Output দেখাবে:**

```
ngrok                                                                              

Session Status    online
Account           Your Name (Plan: Free)
Version           3.x.x
Region            United States (us)
Latency           -
Web Interface     http://127.0.0.1:4040
Forwarding        https://abc123def456.ngrok-free.app -> http://localhost:8000  ← এটা copy করুন!

Connections       ttl     opn     rt1     rt5     p50     p90
                  0       0       0.00    0.00    0.00    0.00
```

**Important:** `Forwarding` এর পাশে যে HTTPS URL আছে সেটা copy করুন:
```
https://abc123def456.ngrok-free.app
```

⚠️ **Note:** 
- এই terminal ও চলতে দিন (বন্ধ করবেন না!)
- Free plan এ URL random হয়, প্রতিবার change হয়
- Paid plan এ permanent URL পাবেন

---

### Step 8.4: Verify Token তৈরি করুন

একটি secure random string তৈরি করুন:

**PowerShell এ run করুন (নতুন terminal):**

```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

**Output:**
```
cK8nQ2xP9mL4sT6vW1yZ3bN5hJ7fR0eD
```

এই token:
1. Copy করুন
2. `.env` file এ paste করুন:
   ```bash
   WHATSAPP_WEBHOOK_VERIFY_TOKEN=cK8nQ2xP9mL4sT6vW1yZ3bN5hJ7fR0eD
   ```
3. একটি safe place এ save করুন (পরে webhook setup এ লাগবে)

---

### Step 8.5: Meta তে Webhook Configure করুন

এখন Meta Developer Console এ webhook setup করবো।

#### Step A: Configuration Page এ যান

```
🌐 URL: https://developers.facebook.com/apps/
```

1. আপনার app select করুন
2. Left sidebar: **WhatsApp → Configuration**

---

#### Step B: Edit Webhook

"Webhook" section দেখবেন:

```
┌──────────────────────────────────┐
│ Webhook                          │
│                                  │
│ Callback URL: Not configured     │
│ Verify token: Not configured     │
│                                  │
│ [Edit]                           │
└──────────────────────────────────┘
```

1. **"Edit"** button এ click করুন

---

#### Step C: Enter Webhook Details

Modal/popup আসবে:

1. **Callback URL:**
   ```
   https://abc123def456.ngrok-free.app/api/whatsapp/webhook/
   ```
   
   ⚠️ **Important:**
   - আপনার ngrok URL use করুন
   - শেষে অবশ্যই `/api/whatsapp/webhook/` add করুন
   - Full example: `https://your-ngrok-url.ngrok-free.app/api/whatsapp/webhook/`

2. **Verify Token:**
   ```
   cK8nQ2xP9mL4sT6vW1yZ3bN5hJ7fR0eD
   ```
   - আপনার `.env` file এ যে token দিয়েছেন সেটা paste করুন
   - ⚠️ Exactly same হতে হবে!

3. **"Verify and Save"** button এ click করুন

---

#### Step D: Verification Process

Meta এখন আপনার webhook verify করবে:

**Loading দেখাবে:** "Verifying..."

**যদি success হয়:**
```
✅ Webhook verified successfully!
```

**যদি error হয়:**
```
❌ Verification failed
```

**Error হলে check করুন:**
- [ ] Django server চলছে কিনা (`python manage.py runserver 8000`)
- [ ] ngrok চলছে কিনা
- [ ] Callback URL সঠিক আছে কিনা (শেষে `/webhook/` আছে?)
- [ ] Verify token exactly match করছে কিনা (.env এবং Meta console এ)
- [ ] `.env` file এ সব variables আছে কিনা

---

#### Step E: Subscribe to Webhook Fields

Verification success হলে:

1. "Webhook fields" section দেখবেন

2. Available fields list আসবে:
   ```
   ☐ messages          ← এটা select করুন ✅
   ☐ messaging_postbacks
   ☐ message_deliveries
   ☐ message_reads
   ```

3. **"messages"** checkbox টি check করুন ✅

4. **"Subscribe"** button এ click করুন (যদি থাকে)

✅ **Checkpoint:** Webhook setup complete!

---

## <a name="part-9-testing"></a>🧪 Part 9: Testing

এখন সব setup complete! Test করার সময়।

### Test 9.1: Health Check করুন

Browser open করুন:

```
🌐 URL: http://localhost:8000/api/whatsapp/health/
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "whatsapp_bot",
  "configuration": {
    "api_token_configured": true,
    "phone_number_configured": true,
    "webhook_secret_configured": true
  },
  "database": {
    "status": "connected",
    "total_messages": 0
  }
}
```

✅ যদি এরকম দেখায় তাহলে configuration সঠিক আছে!

❌ যদি `false` দেখায় তাহলে `.env` file check করুন।

---

### Test 9.2: Send Test Message from Meta

Developer Console এ:

1. **WhatsApp → API Setup** এ যান

2. **"Send a test message"** section দেখুন:

```
┌────────────────────────────────────┐
│ Step 2: Send messages with the API │
│                                    │
│ To: +8801712345678 (verified)      │
│                                    │
│ Message: Hello, this is a test     │
│                                    │
│ [Send Message]                     │
└────────────────────────────────────┘
```

3. Message লিখুন: "Test message"

4. **"Send Message"** click করুন

5. আপনার WhatsApp number এ message আসবে Meta থেকে

✅ **Success:** Message received!

---

### Test 9.3: Reply to Test Message

এখন আপনার WhatsApp থেকে reply করুন:

1. WhatsApp open করুন
2. Meta এর message এ reply করুন: "Hello bot"

3. আপনার Django terminal check করুন - log দেখাবে:
   ```
   Received webhook event: {...}
   Processing message...
   RAG API called...
   Response sent...
   ```

4. কিছুক্ষণ পরে bot থেকে reply আসবে!

✅ **Success:** Bot is working!

---

## 🎉 Congratulations!

আপনার WhatsApp bot সম্পূর্ণভাবে setup এবং working!

---

## 📊 Summary - আপনি কি কি করেছেন

✅ Meta Business Account তৈরি করেছেন  
✅ Meta Developer Account তৈরি করেছেন  
✅ WhatsApp App তৈরি করেছেন  
✅ API Token পেয়েছেন  
✅ Phone Number ID পেয়েছেন  
✅ App Secret পেয়েছেন  
✅ Verify Token তৈরি করেছেন  
✅ Webhook setup করেছেন (ngrok দিয়ে)  
✅ Test করেছেন এবং working পেয়েছেন!

---

## 🔄 Next Steps

### Development Phase:
- Continue testing with ngrok
- Add more features to your bot
- Test different scenarios

### Production Phase:
1. Deploy to production server (Heroku/AWS/DigitalOcean)
2. Setup permanent domain with HTTPS
3. Update webhook URL to production URL
4. Add production phone number
5. Submit for Business Verification (if needed)

---

## 📞 Common Issues & Solutions

### Issue 1: Webhook verification failed

**Causes:**
- Server not running
- ngrok not running
- Wrong URL
- Token mismatch

**Solution:**
```bash
# Check server is running
curl http://localhost:8000/api/whatsapp/health/

# Check ngrok is forwarding
curl https://your-ngrok-url.ngrok-free.app/api/whatsapp/health/

# Verify token matches in both places:
# 1. .env file: WHATSAPP_WEBHOOK_VERIFY_TOKEN
# 2. Meta console webhook settings
```

---

### Issue 2: Bot not responding

**Check:**
```bash
# 1. Django logs
# Terminal এ error দেখাচ্ছে কিনা

# 2. Database
python manage.py shell
>>> from whatsapp_bot.models import WhatsAppMessage
>>> WhatsAppMessage.objects.all()

# 3. RAG API running
curl http://127.0.0.1:8000/api/chat/
```

---

### Issue 3: Token expired

**Solution:**
- System Users page এ যান
- New token generate করুন (same process)
- `.env` update করুন
- Server restart করুন

---

## 📚 Important URLs Reference

| Purpose | URL |
|---------|-----|
| Meta Business Manager | https://business.facebook.com |
| Meta Developer Console | https://developers.facebook.com/apps/ |
| System Users (Token) | https://business.facebook.com/settings/system-users |
| ngrok Download | https://ngrok.com/download |
| ngrok Dashboard | https://dashboard.ngrok.com |
| Your Health Check | http://localhost:8000/api/whatsapp/health/ |
| Your Stats | http://localhost:8000/api/whatsapp/stats/ |

---

## 🆘 Need Help?

যদি কোনো step এ আটকে যান:

1. Error message টি carefully পড়ুন
2. `.env` file verify করুন সব variables আছে কিনা
3. Django terminal এর logs check করুন
4. ngrok terminal এর logs check করুন
5. Meta Developer Console এ error logs check করুন

---

## ✅ Final Checklist

সব কিছু কাজ করছে কিনা verify করুন:

- [ ] Meta Business Account আছে
- [ ] Meta Developer Account আছে
- [ ] WhatsApp App তৈরি হয়েছে
- [ ] `.env` file এ সব 7টি variables দেওয়া আছে
- [ ] Django dependencies installed
- [ ] Database migration complete
- [ ] Django server running (port 8000)
- [ ] ngrok running এবং forwarding করছে
- [ ] Webhook verified এবং subscribed
- [ ] Health check endpoint responding
- [ ] Test message পাঠিয়ে reply পেয়েছি

---

**এখন আপনার WhatsApp bot fully functional!** 🚀

আর কোনো প্রশ্ন থাকলে জিজ্ঞেস করতে পারেন! 😊
