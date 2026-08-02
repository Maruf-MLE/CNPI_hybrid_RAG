# CNPI Hybrid RAG — Deployment Guide
=======================================

## Architecture

```
Frontend (Vercel)  ──▶  Backend (HuggingFace Spaces)  ──▶  Database (Neon)
  Next.js                 Django + LangGraph               PostgreSQL + pgvector
  cnpichat-next           Docker container                 Serverless
```

---

## 1. Database — Neon (PostgreSQL + pgvector)

### Create Neon Project
1. Go to https://neon.tech → Sign up with GitHub
2. New Project → name: `cnpi-rag` → PostgreSQL 16
3. Copy connection string:
   ```
   postgresql://USER:PASSWORD@ep-xxx-pooler.region.aws.neon.tech/cnpi_rag_db?sslmode=require
   ```

### Enable Extensions
In Neon SQL Editor, run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Migrate Local Data to Neon
Edit `scripts/migrate_to_neon.ps1`:
- Replace `$NEON_CONNECTION_STRING` with your Neon connection string

Then run:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\migrate_to_neon.ps1
```

Or double-click `scripts\migrate_to_neon.bat`

This will:
- Dump your local database (schema + all data)
- Restore everything to Neon

### Verify Migration
```bash
psql "postgresql://USER:PASSWORD@HOST.neon.tech/cnpi_rag_db?sslmode=require" \
  -c "SELECT COUNT(*) FROM departments;"   # should be 8
  -c "SELECT COUNT(*) FROM people;"        # should be 125
  -c "SELECT COUNT(*) FROM documents;"     # should be 462
```

---

## 2. Backend — HuggingFace Spaces (Docker)

### Create Space
1. Go to https://huggingface.co → New Space
2. Name: `cnpi-rag-api`
3. SDK: **Docker**
4. Visibility: **Public** (or Private if you have Pro)

### Add Secrets
In Space → Settings → Repository secrets, add:
| Key | Value |
|-----|-------|
| DB_HOST | ep-xxx-pooler.region.aws.neon.tech |
| DB_NAME | cnpi_rag_db |
| DB_USER | your-neon-user |
| DB_PASSWORD | your-neon-password |
| DB_PORT | 5432 |
| GEMINI_API_KEY | your-gemini-key |
| DJANGO_SECRET_KEY | generate-a-new-key |
| DEBUG | False |

### Deploy
```bash
# Add HuggingFace as a remote
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/cnpi-rag-api

# Push to HuggingFace
git push hf main
```

The Dockerfile will build automatically. Your API will be at:
```
https://YOUR_USERNAME-cnpi-rag-api.hf.space
```

Test:
```bash
curl -X POST https://YOUR_USERNAME-cnpi-rag-api.hf.space/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "CST department er CI ke?"}'
```

---

## 3. Frontend — Vercel

### Deploy
1. Go to https://vercel.com → Import `cnpichat-next` folder
2. Framework: Next.js (auto-detected)

### Add Environment Variable
In Vercel → Settings → Environment Variables:
| Key | Value |
|-----|-------|
| NEXT_PUBLIC_API_URL | https://YOUR_USERNAME-cnpi-rag-api.hf.space |

### Deploy
Click Deploy. Your frontend will be at:
```
https://cnpi-chat.vercel.app
```

---

## Summary

| Component | Platform | Free Tier | URL |
|-----------|----------|-----------|-----|
| Database | Neon | 0.5GB, 192h compute | neon.tech |
| Backend | HuggingFace Spaces | Free CPU, 16GB RAM | huggingface.co/spaces |
| Frontend | Vercel | Unlimited | vercel.com |
