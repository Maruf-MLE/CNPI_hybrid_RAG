# CNPI Hybrid RAG — Deployment Guide
=======================================

## Architecture

```
Frontend (Vercel)  ──▶  Backend (Render)  ──▶  Database (Neon)
  Next.js               Django + LangGraph      PostgreSQL + pgvector
  cnpichat-next         Docker container       Serverless
                        Embeddings via HF API
```

---

## 0. Embedding Backend — HuggingFace Inference API (critical for Render)

The RAG system uses `BAAI/bge-m3` embeddings (1024-dim).  Loading this model
in-process needs ~2GB RAM, which will OOM on Render's 4GB tier once Django +
LangGraph + LLM calls are also running.

**Solution**: use the HuggingFace Inference API.  The model stays on HF's
servers; your backend just sends text over HTTPS and gets the vector back.
Zero model download, ~0 extra RAM.

### Get an HF token
1. Go to https://huggingface.co/settings/tokens
2. Create a **READ** token (free, no billing)
3. Copy the value (`hf_xxx...`)

### Set these env vars on Render
| Key | Value |
|-----|-------|
| `EMBEDDING_PROVIDER` | `hf_api` |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` |
| `EMBEDDING_DIMENSION` | `1024` |
| `HF_TOKEN` | `hf_xxx...` |

> The same `EMBEDDING_PROVIDER` flag is used by the seed script
> (`database/seed_documents.py`) and the query-time `embed_text()`, so
> the vectors stored in Neon and the vectors generated at query time are
> always produced by the same model.

### Local dev stays on the local model
Your `.env` already has `EMBEDDING_PROVIDER=local`, so locally the model
loads in-process (faster, offline).  Only Render uses `hf_api`.

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

## 2. Backend — Render (Docker)

### Create Service
1. Go to https://render.com → New → **Web Service**
2. Connect your GitHub repo, select the root directory
3. Runtime: **Docker**
4. Instance Type: Free (4GB RAM) or Starter

### Add Environment Variables
In Render → Environment, add:
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
| EMBEDDING_PROVIDER | hf_api |
| EMBEDDING_MODEL | BAAI/bge-m3 |
| EMBEDDING_DIMENSION | 1024 |
| HF_TOKEN | hf_xxx... (from https://huggingface.co/settings/tokens) |

### Deploy
Render builds the Dockerfile automatically.  The build skips the
sentence-transformers model download (because `EMBEDDING_PROVIDER=hf_api`
is the default), keeping the image small.

Your API will be at:
```
https://your-service-name.onrender.com
```

Test:
```bash
curl -X POST https://your-service-name.onrender.com/api/chat/ \
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
| NEXT_PUBLIC_API_URL | https://your-service-name.onrender.com |

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
| Backend | Render | 4GB RAM, Docker | render.com |
| Frontend | Vercel | Unlimited | vercel.com |
| Embeddings | HuggingFace Inference API | Free | huggingface.co |
