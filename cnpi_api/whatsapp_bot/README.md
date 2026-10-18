# WhatsApp Bot - Complete Setup Guide

## 📱 Overview

Professional WhatsApp bot implementation with RAG (Retrieval-Augmented Generation) integration, conversation tracking, and comprehensive error handling. Built with Django and WhatsApp Business API.

## ✨ Features

- ✅ **WhatsApp Business API Integration** - Full Meta WhatsApp Business API support
- ✅ **Conversation History** - Maintains context across multiple messages
- ✅ **RAG Integration** - Intelligent responses using your RAG system
- ✅ **Security** - HMAC-SHA256 signature verification for webhooks
- ✅ **Idempotency** - Duplicate message prevention
- ✅ **Background Processing** - Fast webhook responses (<5 seconds)
- ✅ **Error Handling** - Comprehensive error tracking and recovery
- ✅ **Monitoring** - Health checks and statistics endpoints
- ✅ **Database Tracking** - Full message lifecycle tracking
- ✅ **Typing Indicators** - Shows bot is processing (optional)

## 📋 Prerequisites

1. **WhatsApp Business Account**
   - Meta Business Manager account
   - WhatsApp Business API access
   - Verified business phone number

2. **Technical Requirements**
   - Python 3.8+
   - Django 4.2+
   - PostgreSQL (recommended) or SQLite
   - Public HTTPS endpoint for webhooks

3. **Existing Setup**
   - RAG API running (default: http://127.0.0.1:8000/api/chat/)

## 🚀 Installation & Setup

### Step 1: Install Dependencies

```bash
# Navigate to project directory
cd G:\CNPI_Hybrid_RAG\cnpi_api

# Install WhatsApp bot dependencies
pip install -r whatsapp_bot/requirements.txt
```

### Step 2: Configure Django Settings

Add the WhatsApp bot app to your Django settings:

```python
# In your settings.py (e.g., cnpi_api/settings.py)

INSTALLED_APPS = [
    # ... existing apps ...
    'whatsapp_bot',  # Add this line
]

# Add URL configuration
# In your main urls.py
from django.urls import path, include

urlpatterns = [
    # ... existing patterns ...
    path('api/whatsapp/', include('whatsapp_bot.urls')),  # Add this line
]
```

### Step 3: Environment Configuration

Create your environment file:

```bash
# Copy the example environment file
cp whatsapp_bot/.env.example .env

# Edit .env and add your actual values
notepad .env
```

Required environment variables:

```bash
# WhatsApp API credentials from Meta Business Manager
WHATSAPP_API_TOKEN=your_actual_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here

# Create a strong random token for webhook verification
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_secure_random_token

# Get this from Meta Developer Console
WHATSAPP_WEBHOOK_SECRET=your_webhook_secret

# Your RAG API endpoint
RAG_API_URL=http://127.0.0.1:8000/api/chat/
```

### Step 4: Database Migration

Run Django migrations to create database tables:

```bash
# Create migration files
python manage.py makemigrations whatsapp_bot

# Apply migrations
python manage.py migrate whatsapp_bot

# (Optional) Create superuser for admin access
python manage.py createsuperuser
```

### Step 5: Get WhatsApp Business API Credentials

#### 5.1 Access Meta Business Manager
1. Go to https://business.facebook.com
2. Select your business account
3. Navigate to **WhatsApp Business Account**

#### 5.2 Get API Token
1. Go to **System Users** in Business Settings
2. Create a system user or select existing one
3. Click **Generate New Token**
4. Select your WhatsApp app
5. Grant permissions: `whatsapp_business_management`, `whatsapp_business_messaging`
6. Copy the token → This is your `WHATSAPP_API_TOKEN`

#### 5.3 Get Phone Number ID
1. Go to **WhatsApp > API Setup**
2. Find your phone number
3. Copy the **Phone Number ID** → This is your `WHATSAPP_PHONE_NUMBER_ID`

#### 5.4 Create Webhook Verify Token
1. Generate a random secure string (e.g., using password generator)
2. Save it as `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
3. You'll need this when setting up the webhook

### Step 6: Setup Webhook

#### 6.1 Deploy Your Application
Your webhook endpoint must be publicly accessible via HTTPS. Options:

**Option A: Use ngrok for testing**
```bash
# Install ngrok from https://ngrok.com
# Run your Django app
python manage.py runserver 8000

# In another terminal, create tunnel
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

**Option B: Deploy to production server**
- Use services like Heroku, AWS, DigitalOcean, etc.
- Ensure HTTPS is enabled

#### 6.2 Configure Webhook in Meta
1. Go to **Meta Developer Console** (https://developers.facebook.com)
2. Select your WhatsApp app
3. Go to **WhatsApp > Configuration**
4. Click **Edit** next to Webhook
5. Enter:
   - **Callback URL**: `https://your-domain.com/api/whatsapp/webhook/`
   - **Verify Token**: Your `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
6. Click **Verify and Save**
7. Subscribe to webhook fields:
   - ✅ `messages`

#### 6.3 Get Webhook Secret
1. After webhook is verified, go to **Webhook Settings**
2. Copy the **App Secret** → This is your `WHATSAPP_WEBHOOK_SECRET`
3. Update your `.env` file

### Step 7: Start the Bot

```bash
# Load environment variables
# (or use python-dotenv to auto-load from .env)

# Start Django development server
python manage.py runserver 8000

# For production, use gunicorn or uwsgi
gunicorn cnpi_api.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Step 8: Test the Bot

#### Test Health Check
```bash
curl http://localhost:8000/api/whatsapp/health/
```

Expected response:
```json
{
  "status": "healthy",
  "service": "whatsapp_bot",
  "timestamp": "2026-10-18T07:52:39Z",
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

#### Test WhatsApp
1. Add your WhatsApp Business number to your contacts
2. Send a message: "Hello"
3. Bot should respond with an answer from your RAG system

## 📁 Project Structure

```
whatsapp_bot/
├── __init__.py           # Package initialization
├── apps.py               # Django app configuration
├── models.py             # Database models (WhatsAppMessage, WhatsAppConversation)
├── views.py              # Webhook views and endpoints
├── urls.py               # URL routing
├── whatsapp_service.py   # WhatsApp API service layer
├── tasks.py              # Background processing tasks
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `WHATSAPP_API_TOKEN` | Yes | WhatsApp Business API token | - |
| `WHATSAPP_PHONE_NUMBER_ID` | Yes | Your WhatsApp phone number ID | - |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Yes | Token for webhook verification | - |
| `WHATSAPP_WEBHOOK_SECRET` | Recommended | Secret for signature verification | - |
| `WHATSAPP_API_VERSION` | No | WhatsApp API version | v18.0 |
| `RAG_API_URL` | Yes | Your RAG API endpoint | http://127.0.0.1:8000/api/chat/ |
| `RAG_API_TIMEOUT` | No | RAG API timeout (seconds) | 60 |

### Django Admin

Access the Django admin panel to view messages and conversations:

1. Create superuser: `python manage.py createsuperuser`
2. Add to `admin.py` in `whatsapp_bot/`:

```python
from django.contrib import admin
from .models import WhatsAppMessage, WhatsAppConversation

@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'phone_number', 'status', 'received_at']
    list_filter = ['status', 'received_at']
    search_fields = ['phone_number', 'message_text', 'response_text']
    readonly_fields = ['message_id', 'raw_payload', 'received_at', 'processed_at']

@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'user_name', 'message_count', 'last_message_at']
    search_fields = ['phone_number', 'user_name']
    readonly_fields = ['created_at', 'last_message_at']
```

3. Access: http://localhost:8000/admin/

## 📡 API Endpoints

### 1. Webhook Endpoint
**URL**: `/api/whatsapp/webhook/`

**GET** - Webhook verification
- Used during initial setup
- Returns challenge string

**POST** - Receive messages
- Accepts webhook events from WhatsApp
- Returns 200 OK immediately
- Processes messages in background

### 2. Health Check
**URL**: `/api/whatsapp/health/`

**GET** - Service health status
```json
{
  "status": "healthy",
  "configuration": { ... },
  "database": { ... }
}
```

### 3. Statistics
**URL**: `/api/whatsapp/stats/`

**GET** - Message processing statistics
```json
{
  "total_messages": 100,
  "by_status": {
    "received": 2,
    "processing": 1,
    "completed": 95,
    "failed": 2
  },
  "recent_messages": [...]
}
```

## 🗃️ Database Models

### WhatsAppMessage
Tracks individual messages for duplicate prevention and debugging.

Fields:
- `message_id` - Unique WhatsApp message ID
- `phone_number` - Sender's phone number
- `message_text` - Original message content
- `status` - Processing status (received/processing/completed/failed)
- `response_text` - Bot's response
- `error_message` - Error details if failed
- `raw_payload` - Original webhook data

### WhatsAppConversation
Maintains conversation history for context-aware responses.

Fields:
- `phone_number` - User's phone number (unique)
- `user_name` - User's display name
- `chat_history` - JSON array of messages
- `message_count` - Total messages in conversation
- `last_message_at` - Timestamp of last message

## 🔄 Message Flow

1. **User sends message** → WhatsApp
2. **WhatsApp** → POST to `/api/whatsapp/webhook/`
3. **Webhook validates** signature & creates `WhatsAppMessage`
4. **Returns 200 OK** (< 5 seconds)
5. **Background thread**:
   - Marks message as processing
   - Gets/creates conversation
   - Retrieves chat history (last 10 messages)
   - Calls RAG API with context
   - Sends response via WhatsApp API
   - Updates message status
   - Saves to conversation history

## 🔒 Security Features

- ✅ **HMAC-SHA256 signature verification** - Validates webhook authenticity
- ✅ **Webhook verify token** - Prevents unauthorized webhook setup
- ✅ **CSRF exemption** - Webhooks don't use CSRF tokens
- ✅ **Duplicate prevention** - Idempotent message handling
- ✅ **Error isolation** - Failed messages don't crash the service
- ✅ **Rate limiting** - (Recommended: Add Django rate limiting)

## 🐛 Troubleshooting

### Bot not responding

1. **Check health endpoint**:
```bash
curl http://your-domain.com/api/whatsapp/health/
```

2. **Check Django logs**:
```bash
# Development
python manage.py runserver --verbosity 2

# Production logs
tail -f /var/log/whatsapp_bot.log
```

3. **Check webhook delivery** in Meta Developer Console:
   - Go to WhatsApp > Configuration
   - View webhook delivery logs

### Webhook verification failed

- Ensure `WHATSAPP_WEBHOOK_VERIFY_TOKEN` matches token in Meta console
- Check webhook URL is correct and publicly accessible
- Ensure endpoint accepts GET requests

### Signature verification failed

- Ensure `WHATSAPP_WEBHOOK_SECRET` matches App Secret in Meta
- Check webhook is receiving correct headers
- Verify payload is not modified before verification

### RAG API timeout

- Increase `RAG_API_TIMEOUT` in `.env`
- Check RAG API is running and accessible
- Monitor RAG API performance

### Database errors

```bash
# Reset migrations if needed
python manage.py migrate whatsapp_bot zero
python manage.py migrate whatsapp_bot
```

## 📊 Monitoring

### View Statistics

```python
# In Django shell
python manage.py shell

from whatsapp_bot.models import WhatsAppMessage, WhatsAppConversation

# Total messages
WhatsAppMessage.objects.count()

# Messages by status
WhatsAppMessage.objects.filter(status='completed').count()

# Active conversations
WhatsAppConversation.objects.count()

# Recent failures
WhatsAppMessage.objects.filter(status='failed').order_by('-received_at')[:10]
```

### Retry Failed Messages

```python
from whatsapp_bot.tasks import retry_failed_messages

# Retry up to 10 failed messages
retry_failed_messages(limit=10)
```

## 🚀 Production Deployment

### 1. Use Production Server

```bash
# Install gunicorn
pip install gunicorn

# Run with workers
gunicorn cnpi_api.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --log-level info
```

### 2. Use PostgreSQL

Update `.env`:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/whatsapp_bot
```

### 3. Setup Logging

Add to Django settings:
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/whatsapp_bot.log',
        },
    },
    'loggers': {
        'whatsapp_bot': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### 4. Setup Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /api/whatsapp/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Setup Systemd Service

Create `/etc/systemd/system/whatsapp-bot.service`:

```ini
[Unit]
Description=WhatsApp Bot Service
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/var/www/cnpi_api
Environment="PATH=/var/www/cnpi_api/venv/bin"
ExecStart=/var/www/cnpi_api/venv/bin/gunicorn cnpi_api.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable whatsapp-bot
sudo systemctl start whatsapp-bot
sudo systemctl status whatsapp-bot
```

## 📝 Bot Behavior

The bot inherits behavior patterns from existing bots (answer_bot, fiwano_bot):

- **Conversational context** - Remembers last 10 messages
- **RAG-powered responses** - Uses your knowledge base
- **Bengali language support** - Default error messages in Bengali
- **Graceful error handling** - User-friendly error messages
- **Automatic history cleanup** - Keeps last 20 messages per user

Customize responses in `whatsapp_bot/tasks.py`:

```python
# Default response when RAG returns empty
answer_text = "দুঃখিত, আমি এই মুহূর্তে আপনার প্রশ্নের উত্তর দিতে পারছি না।"

# Error message sent to user
error_response = "দুঃখিত, আপনার বার্তা প্রক্রিয়া করতে একটি সমস্যা হয়েছে।"
```

## 🔄 Updates & Maintenance

### Update Dependencies

```bash
pip install --upgrade -r whatsapp_bot/requirements.txt
```

### Database Cleanup

```python
# Clean old conversations (optional)
from whatsapp_bot.models import WhatsAppConversation
from django.utils import timezone
from datetime import timedelta

# Delete conversations inactive for 30+ days
cutoff = timezone.now() - timedelta(days=30)
WhatsAppConversation.objects.filter(last_message_at__lt=cutoff).delete()
```

## 📞 Support & Resources

- **WhatsApp Business API Docs**: https://developers.facebook.com/docs/whatsapp
- **Django Documentation**: https://docs.djangoproject.com/
- **Meta Business Manager**: https://business.facebook.com/

## 📄 License

This WhatsApp bot implementation follows your project's license.

---

**Created**: 2026-10-18  
**Version**: 1.0.0  
**Author**: Professional WhatsApp Bot for CNPI RAG System
