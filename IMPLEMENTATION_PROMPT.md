# Cloudflare Workers + Meta Messenger API Implementation Prompt

## Context

আমার কাছে একটি Django-based RAG (Retrieval-Augmented Generation) chatbot আছে যা বর্তমানে Fiwano service ব্যবহার করে Facebook Messenger এর সাথে connect করা। আমি চাই Fiwano dependency সরিয়ে **Cloudflare Workers + Meta Direct API** দিয়ে একটি forever free solution implement করতে।

**Project Location:** `G:\CNPI_Hybrid_RAG`

---

## Current Architecture

```
User → Facebook Messenger → Fiwano Platform → Django Webhook → RAG System → Fiwano API → User
```

**Current Files:**
- `cnpi_api/fiwano_bot/` - Fiwano integration Django app
- `cnpi_api/fiwano_bot/views.py` - Webhook handler
- `cnpi_api/fiwano_bot/fiwano_service.py` - API client
- `cnpi_api/fiwano_bot/tasks.py` - Background processing
- `cnpi_api/rag_api/rag_engine.py` - RAG system (must remain intact)

---

## Target Architecture

```
User → Facebook Messenger → Meta Webhook → Cloudflare Worker → Django API → Worker → Meta Send API → User
```

---

## Requirements

### 🎯 Primary Goal

Implement a **production-ready, forever free** Facebook Messenger bot using:
1. **Cloudflare Workers** (free tier: 100K requests/day) as webhook middleware
2. **Meta Direct API** (Development Mode: 25 test users, no trade licence required)
3. **Existing Django backend** on Render (keep RAG system intact)

---

## Implementation Tasks

### **Phase 1: Research & Verification (Critical)**

**IMPORTANT:** Before writing any code, you MUST:

1. **Read Official Cloudflare Workers Documentation:**
   - Go to: https://developers.cloudflare.com/workers/
   - Understand: Request handling, Fetch API, Web Crypto API, Environment Variables
   - Find examples of: HMAC-SHA256 signature verification, POST request handling, external API calls

2. **Read Meta Messenger Platform Documentation:**
   - Search for: "Meta Messenger Platform webhooks 2026"
   - Understand: Webhook verification flow, signature verification (x-hub-signature-256), message format
   - Find: App creation process, Development Mode setup, webhook configuration

3. **Verify Technical Compatibility:**
   - Confirm: Cloudflare Workers can handle GET (verification) and POST (webhooks)
   - Confirm: Web Crypto API supports HMAC-SHA256
   - Confirm: Workers can make fetch() calls to external APIs
   - Confirm: Response time fits within Meta's 20-second timeout

4. **Search for Real Examples:**
   - GitHub search: "cloudflare workers facebook messenger"
   - GitHub search: "cloudflare workers webhook hmac"
   - Look for: Similar implementations, gotchas, best practices

**DO NOT proceed to coding until you've verified these points.**

---

### **Phase 2: Cloudflare Workers Implementation**

#### **2.1: Create Worker Script**

Create a `messenger-webhook-worker.js` file that handles:

**Requirements:**
- ✅ GET request handler for Meta webhook verification
  - Extract `hub.mode`, `hub.verify_token`, `hub.challenge` from query params
  - Verify token matches environment variable
  - Return challenge as plain text with 200 status

- ✅ POST request handler for webhook events
  - Read request body as text (for signature verification)
  - Verify x-hub-signature-256 header using HMAC-SHA256
  - Parse JSON body
  - Forward to Django backend
  - Return "EVENT_RECEIVED" with 200 status immediately (within 20 seconds)

- ✅ HMAC-SHA256 Signature Verification
  - Use Web Crypto API (`crypto.subtle`)
  - Compare Meta's signature with computed signature
  - Prevent timing attacks (use constant-time comparison)

- ✅ Environment Variables Support
  - `VERIFY_TOKEN` - Meta webhook verification token
  - `APP_SECRET` - Meta app secret for signature verification
  - `DJANGO_BACKEND_URL` - URL to Django API endpoint

- ✅ Error Handling
  - Return 403 for invalid signatures
  - Return 405 for unsupported methods
  - Log errors properly

**Code Quality Requirements:**
- Professional code with comments
- Async/await properly handled
- No hardcoded secrets
- Production-ready error handling

---

#### **2.2: Deploy to Cloudflare**

**Step-by-step guide needed for:**
1. Creating Cloudflare Workers account (free tier)
2. Installing Wrangler CLI
3. Configuring `wrangler.toml`
4. Setting environment variables (secrets)
5. Deploying worker
6. Getting the *.workers.dev URL

**Provide exact commands and configuration examples.**

---

### **Phase 3: Meta Developer App Setup**

#### **3.1: Create Meta App**

**Guide me through:**
1. Creating Facebook Developer account
2. Creating a new App
3. Adding Messenger product
4. Generating Page Access Token
5. Configuring webhook URL (Cloudflare Worker URL)
6. Setting up webhook subscriptions (messages, messaging_postbacks, etc.)

**Important Notes:**
- App will be in **Development Mode** (no business verification needed)
- Can add up to 25 test users (Admins, Developers, Testers roles)
- No trade licence required for Development Mode

---

#### **3.2: Webhook Verification**

**Test and verify:**
1. Meta sends GET request to Worker
2. Worker returns challenge correctly
3. Meta confirms webhook is verified
4. Test POST webhook with Meta's test tool

---

### **Phase 4: Django Backend Integration**

#### **4.1: Create New Endpoint for Cloudflare Worker**

**Modify Django to accept webhooks from Cloudflare Worker:**

Create: `cnpi_api/messenger_direct/` (new Django app)

**Files needed:**
- `views.py` - Webhook handler (similar to fiwano_bot/views.py)
- `messenger_service.py` - Meta Graph API client
- `models.py` - Message tracking (reuse fiwano_bot models or create new)
- `tasks.py` - Background RAG processing

**Key differences from Fiwano:**
- Accept webhooks from Cloudflare Worker (not Fiwano)
- Send responses via Meta Graph API directly (not Fiwano API)
- Use Page Access Token authentication

---

#### **4.2: Meta Graph API Integration**

**Implement `messenger_service.py` to:**
1. Send text messages: `POST https://graph.facebook.com/v18.0/me/messages`
2. Send typing indicators (sender_action)
3. Handle Page Access Token authentication
4. Implement retry logic
5. Handle rate limits

**Authentication:**
- Use Page Access Token from Meta App
- Store in environment variable: `META_PAGE_ACCESS_TOKEN`

---

#### **4.3: Message Flow**

```python
# cnpi_api/messenger_direct/views.py

def webhook_view(request):
    # 1. Parse Meta webhook format
    # 2. Extract sender PSID, message text
    # 3. Save to database (idempotency)
    # 4. Return 200 OK immediately
    # 5. Background: Process with RAG system
    # 6. Send response via Meta Graph API
```

**Must preserve:**
- Existing RAG system (`rag_api/rag_engine.py`) - NO CHANGES
- Conversation history tracking
- Idempotency (duplicate message prevention)

---

### **Phase 5: Testing & Validation**

#### **5.1: Local Testing**

**Test flow:**
1. Deploy Worker to Cloudflare
2. Configure Meta webhook
3. Send test message from Facebook Page
4. Verify: Worker receives → Django processes → Response sent
5. Check logs at each step

**Provide debugging commands and log checking methods.**

---

#### **5.2: End-to-End Testing**

**Test scenarios:**
1. Simple text message
2. Long message (RAG processing)
3. Multiple messages (conversation history)
4. Error handling (invalid input, API failures)
5. Duplicate message handling (idempotency)

---

### **Phase 6: Documentation**

**Create comprehensive documentation:**

1. **README.md** - Overview, architecture diagram, setup instructions
2. **DEPLOYMENT.md** - Step-by-step deployment guide
3. **TESTING.md** - Testing procedures and troubleshooting
4. **ENV_VARIABLES.md** - All required environment variables with examples

---

## Technical Constraints

### ✅ MUST DO:
- Read official documentation before implementing
- Verify all technical details via web search
- Use Web Crypto API for HMAC (not custom implementation)
- Test thoroughly before marking as complete
- Follow Meta's Platform Policies
- Implement proper error handling and logging
- Keep existing RAG system completely intact
- Maintain conversation history functionality
- Ensure idempotency (no duplicate processing)

### ❌ MUST NOT DO:
- Hardcode any secrets or tokens
- Modify existing RAG engine code
- Ignore Meta's webhook signature verification
- Skip error handling
- Use deprecated APIs
- Guess implementation details (always verify via docs)

---

## Deliverables

### **Code Files:**
1. `messenger-webhook-worker.js` - Cloudflare Worker script
2. `wrangler.toml` - Worker configuration
3. `cnpi_api/messenger_direct/` - New Django app (complete)
4. Environment variable templates (`.env.example`)

### **Documentation:**
1. Complete setup guide (Bangla + English)
2. Deployment instructions
3. Testing procedures
4. Troubleshooting guide
5. Architecture diagrams

### **Configuration:**
1. Meta App settings checklist
2. Cloudflare Worker secrets setup
3. Django settings modifications
4. Render deployment updates

---

## Success Criteria

✅ Cloudflare Worker successfully handles Meta webhooks
✅ Signature verification works correctly
✅ Django backend receives and processes messages
✅ RAG system generates responses
✅ Responses sent back via Meta Graph API
✅ User receives bot responses in Messenger
✅ Conversation history maintained
✅ Idempotency working (no duplicate processing)
✅ Error handling tested and working
✅ Documentation complete and clear
✅ **Forever free** - no subscription costs
✅ **No trade licence required** (Development Mode)

---

## Professional Standards

### Research First Approach:
- Always consult official documentation
- Verify API endpoints and parameters
- Check for latest best practices (2026)
- Search for existing solutions and learn from them

### Code Quality:
- Clear comments and documentation
- Error handling for all edge cases
- Secure coding practices (no exposed secrets)
- Performance optimization (fast webhook responses)

### Testing:
- Unit tests for critical functions
- Integration tests for full flow
- Error scenario testing
- Load testing (within free tier limits)

### Documentation:
- Step-by-step instructions
- Screenshots where helpful
- Troubleshooting sections
- Common issues and solutions

---

## Important Notes

1. **Development Mode Limitation:**
   - Only 25 users (Admins, Developers, Testers can use the bot)
   - For public bot, Meta App Review + trade licence required (future consideration)

2. **Free Tier Limits:**
   - Cloudflare Workers: 100,000 requests/day
   - Meta API: No cost for messaging
   - Render: Check current free tier limits

3. **Security:**
   - Always verify webhook signatures
   - Use environment variables for secrets
   - Implement rate limiting if needed

4. **Scalability:**
   - Current solution handles moderate traffic
   - Can upgrade Cloudflare Workers if needed
   - Django backend can be scaled on Render

---

## Additional Resources to Consult

**Official Documentation:**
- Cloudflare Workers: https://developers.cloudflare.com/workers/
- Meta Messenger Platform: https://developers.facebook.com/docs/messenger-platform/
- Meta Graph API: https://developers.facebook.com/docs/graph-api/

**Search Keywords:**
- "cloudflare workers webhook handler"
- "meta messenger platform webhook verification"
- "hmac sha256 verification cloudflare workers"
- "facebook messenger bot without third party"
- "meta graph api send message"

---

## Final Instructions

**Please implement this step-by-step:**

1. ✅ Start with thorough research and documentation reading
2. ✅ Verify technical feasibility at each step
3. ✅ Implement Cloudflare Worker first (test standalone)
4. ✅ Set up Meta App and verify webhook
5. ✅ Integrate Django backend
6. ✅ Test end-to-end flow
7. ✅ Create comprehensive documentation
8. ✅ Provide troubleshooting guide

**Keep me informed:**
- Share findings from documentation research
- Ask for clarification if requirements are unclear
- Report any blockers or technical limitations discovered
- Suggest improvements if you find better approaches

**Remember:** This is a production system. Quality, security, and reliability are paramount. Take time to do it right rather than rushing through implementation.

---

## Current Project State

**Working Directory:** `G:\CNPI_Hybrid_RAG`

**Key Files to Preserve:**
- `rag_api/rag_engine.py` - RAG system (DO NOT MODIFY)
- `Cnpi_RAG/` - RAG logic (DO NOT MODIFY)
- Database models in `fiwano_bot/models.py` (can reference/reuse)

**Deployment:**
- Backend: Render.com (already deployed)
- Database: PostgreSQL (already configured)

---

## Let's Begin!

Please start by:
1. Reading Cloudflare Workers documentation
2. Reading Meta Messenger Platform documentation
3. Confirming technical feasibility
4. Then proceed with implementation

**আপনার কাজ শুরু করুন এবং প্রতিটি phase সম্পন্ন হওয়ার পর আমাকে update দিন!**
