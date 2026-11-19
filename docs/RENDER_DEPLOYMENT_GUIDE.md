# CNPI API Backend - Render Deployment Guide

## Overview

This guide covers deploying the CNPI Hybrid RAG API backend to Render.com using Docker.

**Stack:**
- Django 5.0 + Django REST Framework
- PostgreSQL (Neon) with pgvector
- LangGraph RAG pipeline
- Google Gemini API (LLM + Embeddings)
- Gunicorn WSGI server

**Render Plan:** Docker, 4GB RAM

---

## Prerequisites

1. **Render Account:** https://dashboard.render.com/
2. **GitHub Repository:** Code pushed to GitHub
3. **Neon PostgreSQL Database:** Already configured (see `.env.render`)
4. **API Keys:**
   - Google Gemini API key
   - HuggingFace token (for embeddings)
   - Facebook/Telegram bot tokens (optional)

---

## Deployment Steps

### 1. Create New Web Service on Render

1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select the `CNPI_Hybrid_RAG` repository

### 2. Configure Service Settings

**Basic Settings:**
- **Name:** `cnpi-hybrid-rag-1` (or your preferred name)
- **Region:** Singapore (or closest to your users)
- **Branch:** `main` (or your deployment branch)
- **Root Directory:** (leave empty - uses repository root)
- **Environment:** `Docker`
- **Docker Build Context:** (leave empty)
- **Dockerfile Path:** `Dockerfile`

**Instance Type:**
- Select **4 GB RAM** plan (required for RAG operations)
- Auto-deploy: **Yes** (optional - deploys on git push)

### 3. Add Environment Variables

Go to **Environment** tab and add all variables from `.env.render`:

#### Database (Neon PostgreSQL)
```
DB_HOST=your_neon_host_here
DB_NAME=neondb
DB_USER=neondb_owner
DB_PASSWORD=your_db_password_here
DB_PORT=5432
CONN_MAX_AGE=600
DB_CONNECT_TIMEOUT=5
```

#### Django Configuration
```
DJANGO_SECRET_KEY=your_django_secret_key_here
DEBUG=False
```

#### LLM & Embeddings
```
GEMINI_API_KEY=your_gemini_api_key_here
EMBEDDING_PROVIDER=hf_api
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024
HF_TOKEN=your_huggingface_token_here
```

#### RAG Configuration
```
TOP_K_SEARCH=5
MAX_RETRIES=3
MAX_HYBRID_DEPTH=1
```

#### Gunicorn Performance
```
GUNICORN_TIMEOUT=300
GUNICORN_MAX_REQUESTS=100
GUNICORN_MAX_REQUESTS_JITTER=20
```

#### Heartbeat / Keep-Alive
```
HEARTBEAT_SECRET=your_heartbeat_secret_here
HEARTBEAT_TARGET_URL=https://cnpi-hybrid-rag-7hvz.onrender.com/api/ping/
```

#### Bot Tokens (Optional - only if using bots)

**Facebook Messenger (Document Saver):**
```
FB_VERIFY_TOKEN=your_verify_token
FB_APP_SECRET=your_app_secret
FB_PAGE_ACCESS_TOKEN=your_page_token
FB_ALLOWED_PSIDS=comma,separated,psids
```

**Answer Bot (RAG Q&A):**
```
ANSWER_BOT_VERIFY_TOKEN=your_answer_bot_verify_token
ANSWER_BOT_APP_SECRET=your_answer_bot_app_secret
ANSWER_BOT_PAGE_ACCESS_TOKEN=your_answer_bot_page_access_token
ANSWER_BOT_ALLOWED_PSIDS=
RAG_API_URL=https://cnpi-hybrid-rag-7hvz.onrender.com/api/chat/
```

**Telegram Bot:**
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_SECRET_TOKEN=your_webhook_secret
TELEGRAM_BOT_ALLOWED_USERS=comma,separated,user_ids
```

**WhatsApp (optional):**
```
FIWANO_API_KEY=your_fiwano_key
FIWANO_WEBHOOK_SECRET=your_webhook_secret
```

### 4. Deploy

1. Click **"Create Web Service"**
2. Render will:
   - Pull your repository
   - Build Docker image using `Dockerfile`
   - Start the service with gunicorn
   - Assign a public URL: `https://cnpi-hybrid-rag-7hvz.onrender.com`

3. Monitor deployment logs in the **Logs** tab

---

## Post-Deployment Setup

### 1. Run Database Migrations

After first deployment, run migrations via Render Shell:

1. Go to **Shell** tab
2. Run:
```bash
cd /app/cnpi_api
python manage.py migrate
python manage.py collectstatic --noinput
```

### 2. Create Django Superuser (Optional)

```bash
cd /app/cnpi_api
python manage.py createsuperuser
```

### 3. Set Up Heartbeat/Keep-Alive

Render free tier spins down after 15 minutes of inactivity. Set up a cron job to keep it alive:

**Option A: External Cron Service**
- Use [cron-job.org](https://cron-job.org) or similar
- URL: `https://cnpi-hybrid-rag-7hvz.onrender.com/api/ping/`
- Method: `GET`
- Interval: Every 10 minutes
- Header: `X-Heartbeat-Secret: yx5SgGHSzRY0Iv2Lq9-XWHVRrfHVFHc52m-pbcIRAeM`

**Option B: Render Cron Job**
- Create a new **Cron Job** service in Render
- Command: `curl -H "X-Heartbeat-Secret: $HEARTBEAT_SECRET" $HEARTBEAT_TARGET_URL`
- Schedule: `*/10 * * * *` (every 10 minutes)

### 4. Configure Facebook Webhooks (If Using Bots)

**Document Saver Bot:**
1. Meta App Dashboard → Webhooks
2. Callback URL: `https://cnpi-hybrid-rag-7hvz.onrender.com/webhook/`
3. Verify Token: (value from `FB_VERIFY_TOKEN`)
4. Subscribe to: `messages`, `messaging_postbacks`

**Answer Bot:**
1. Meta App Dashboard → Webhooks
2. Callback URL: `https://cnpi-hybrid-rag-7hvz.onrender.com/answer-webhook/`
3. Verify Token: (value from `ANSWER_BOT_VERIFY_TOKEN`)
4. Subscribe to: `messages`, `messaging_postbacks`, `messaging_optins`

**Note:** A single Facebook Page can only have ONE webhook URL. Use separate pages for different bots.

### 5. Configure Telegram Webhook (If Using Telegram Bot)

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://cnpi-hybrid-rag-7hvz.onrender.com/telegram-webhook/",
    "secret_token": "<YOUR_WEBHOOK_SECRET>"
  }'
```

---

## Available API Endpoints

### RAG API
- **POST** `/api/chat/` - RAG query endpoint
- **POST** `/api/upload/` - Upload documents

### Health & Monitoring
- **GET** `/api/ping/` - Health check / keep-alive
- **GET** `/api/health/` - System health status

### Bot Webhooks
- **POST** `/webhook/` - Facebook Messenger (document saver)
- **POST** `/answer-webhook/` - Facebook Answer Bot (RAG Q&A)
- **POST** `/telegram-webhook/` - Telegram Bot
- **POST** `/whatsapp-webhook/` - WhatsApp (via Fiwano)

### Admin
- **GET** `/admin/` - Django admin panel
- **GET** `/admin-panel/` - Custom admin dashboard

---

## Testing the Deployment

### 1. Test Health Check
```bash
curl https://cnpi-hybrid-rag-7hvz.onrender.com/api/ping/
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "2026-11-19T12:30:00Z"
}
```

### 2. Test RAG API
```bash
curl -X POST https://cnpi-hybrid-rag-7hvz.onrender.com/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is CNPI?",
    "session_id": "test-session"
  }'
```

### 3. Check Logs
- Go to Render Dashboard → Your Service → **Logs** tab
- Look for:
  - `Starting gunicorn`
  - `Listening at: http://0.0.0.0:10000`
  - No error messages

---

## Troubleshooting

### Service Won't Start

**Check Dockerfile:**
- Ensure all paths are correct
- Verify `requirements.txt` exists at `Cnpi_RAG/requirements.txt`

**Check Environment Variables:**
- All required variables from `.env.render` are set
- Database credentials are correct
- No typos in variable names

**Check Logs:**
```
# Look for import errors or missing dependencies
# Common issues:
- ModuleNotFoundError: Missing package in requirements.txt
- psycopg2.OperationalError: Database connection failed
- ImproperlyConfigured: Missing Django settings
```

### High Memory Usage / OOM Kills

**Symptoms:** Service crashes with `Error code 137`

**Solutions:**
1. Reduce gunicorn workers (already set to 1 in Dockerfile)
2. Lower `GUNICORN_MAX_REQUESTS` to force worker restarts
3. Use `hf_api` embedding provider (not `local`)
4. Upgrade to 8GB RAM plan

**Current Config (Optimized for 4GB):**
```
--workers 1
--timeout 300
--max-requests 100
--preload
```

### Slow Response Times

**Cold Start:** First request after 15min idle takes 30-60s
- Solution: Set up heartbeat/keep-alive (see above)

**Database Latency:** Connection pooling not working
- Check: `CONN_MAX_AGE=600` is set
- Verify: Using Neon pooler URL (ends with `-pooler.c-3...`)

**RAG Pipeline Slow:**
- Check `TOP_K_SEARCH` (default: 5)
- Monitor Gemini API rate limits
- Check HuggingFace API token is valid

### Database Connection Errors

```
psycopg2.OperationalError: could not connect to server
```

**Solutions:**
1. Verify database credentials in environment variables
2. Check Neon database is not paused (free tier pauses after 7 days)
3. Ensure `DB_HOST` uses the pooler URL
4. Test connection from Render Shell:
```bash
psql "postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=require"
```

### Import Errors

```
ModuleNotFoundError: No module named 'Cnpi_RAG'
```

**Solutions:**
1. Check Dockerfile copies `Cnpi_RAG/` correctly
2. Verify `settings.py` adds directories to `sys.path`
3. Ensure working directory is set: `WORKDIR /app/cnpi_api`

---

## Monitoring & Logs

### View Real-Time Logs
```bash
# In Render Dashboard → Logs tab
# Or use Render CLI:
render logs -f -s cnpi-hybrid-rag-1
```

### Key Log Markers

**Startup:**
```
Listening at: http://0.0.0.0:10000
Booting worker with pid: 123
```

**RAG Query:**
```
INFO rag_api: Processing question from session <id>
INFO rag_api: Found <n> relevant documents
INFO rag_api: Generated answer in <time>s
```

**Bot Activity:**
```
INFO messenger_bot: Processing message from PSID <id>
INFO answer_bot: Sent answer to PSID <id>
```

### Metrics to Monitor

1. **Response Time:** Should be <5s for cached, <30s for cold start
2. **Memory Usage:** Should stay under 3.5GB (4GB plan)
3. **Error Rate:** Should be <1% of requests
4. **Database Connections:** Check connection pool usage

---

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `DJANGO_SECRET_KEY` set
- [ ] Database password is secret
- [ ] Bot tokens are not in git history
- [ ] `ALLOWED_HOSTS` configured (currently allows all)
- [ ] HTTPS enforced via Render (automatic)
- [ ] CORS properly configured for frontend domain
- [ ] Heartbeat secret is strong random token
- [ ] Admin panel protected (check middleware)

---

## Scaling & Performance

### Current Configuration (4GB RAM)
- 1 gunicorn worker
- 300s timeout (5 minutes)
- 100 requests per worker before restart
- Connection pooling (10min)

### If You Need More Performance

**Upgrade to 8GB RAM:**
- Increase workers to 2-3
- Use local embeddings instead of API
- Enable concurrent request handling

**Database Optimization:**
- Add indexes on frequently queried columns
- Use Neon's caching features
- Consider read replicas for heavy loads

**Caching:**
- Add Redis for session/query caching
- Cache embedding results
- Cache LLM responses (be careful with freshness)

---

## Maintenance

### Update Deployment

1. Push changes to GitHub
2. Render auto-deploys (if enabled)
3. Monitor logs for successful startup
4. Test endpoints after deployment

### Manual Deploy

1. Render Dashboard → Your Service
2. Click **"Manual Deploy"**
3. Select branch
4. Click **"Deploy"**

### Rollback

1. Render Dashboard → Your Service → **Deploys** tab
2. Find previous successful deploy
3. Click **"Rollback to this version"**

### Database Backups

Neon provides automatic backups. To manually backup:
```bash
pg_dump "postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=require" > backup.sql
```

---

## Cost Estimation

**Render Pricing (as of 2026):**
- 4GB RAM: $15-25/month
- 8GB RAM: $40-60/month
- Custom domains: Free
- SSL certificates: Free

**External Services:**
- Neon PostgreSQL: Free tier (0.5GB) or $20/month (10GB)
- Google Gemini API: Pay-per-use (~$0.002 per query)
- HuggingFace API: Free tier or $9/month

**Total Monthly Cost:** ~$15-50 depending on traffic

---

## Support & Resources

- **Render Docs:** https://render.com/docs
- **Django Deployment:** https://docs.djangoproject.com/en/5.0/howto/deployment/
- **Neon Database:** https://neon.tech/docs
- **Project Issues:** Contact dev team

---

## Quick Reference Commands

```bash
# View logs
render logs -s cnpi-hybrid-rag-1

# Open shell
render shell -s cnpi-hybrid-rag-1

# Restart service
render restart -s cnpi-hybrid-rag-1

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser

# Test database connection
python manage.py dbshell

# Check environment
env | grep DB_
```

---

## Next Steps

1. ✅ Deploy to Render
2. ✅ Configure environment variables
3. ✅ Run migrations
4. ✅ Set up heartbeat/keep-alive
5. ✅ Configure bot webhooks (if needed)
6. ✅ Test all endpoints
7. ✅ Monitor logs and performance
8. 🔄 Connect frontend to `https://cnpi-hybrid-rag-7hvz.onrender.com`

---

**Deployment completed!** Your CNPI API backend is now live at:
`https://cnpi-hybrid-rag-7hvz.onrender.com`
