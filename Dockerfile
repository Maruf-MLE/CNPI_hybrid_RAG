# ============================================================
# CNPI Hybrid RAG - Dockerfile for Render.com
# ============================================================
# Backend: Django + LangGraph
# Render: 4GB RAM, Docker support
#
# Embedding backend is selected by EMBEDDING_PROVIDER env var:
#   - local  : loads SentenceTransformer in-process (~2GB RAM, model download)
#   - hf_api : calls HuggingFace Inference API (no model download, ~0 RAM)
# For Render (4GB) use hf_api + HF_TOKEN to avoid OOM.  When hf_api is set,
# sentence-transformers / torch are NOT imported, so the image stays small.
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (minimal — save RAM)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY Cnpi_RAG/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Embedding: Google Gemini Embedding 2 (API-based, no model download needed)
# The embedding model runs via Google's API using GEMINI_API_KEY environment variable.
# No local model download required, which keeps the Docker image small and fast to build.

# Copy project files
COPY Cnpi_RAG/ ./Cnpi_RAG/
COPY cnpi_api/ ./cnpi_api/
COPY plan/ ./plan/
COPY manage_data.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_SETTINGS_MODULE=cnpi_api.settings
ENV DEBUG=False

# Run Django with gunicorn
# --workers 1: Render 4GB RAM — 1 worker is safest with RAG + LLM calls
# --timeout 300: RAG pipeline can take 30-60s per query
# --preload: loads graph ONCE before worker forks (saves memory)
WORKDIR /app/cnpi_api

# Render sets the PORT env var at runtime.  Shell form (not exec array)
# so that ${PORT:-8000} is expanded by /bin/sh before gunicorn starts.
# Use environment variables for timeout and worker lifecycle settings
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --timeout ${GUNICORN_TIMEOUT:-300} \
    --max-requests ${GUNICORN_MAX_REQUESTS:-100} \
    --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-20} \
    --worker-class sync \
    --keep-alive 5 \
    --preload \
    cnpi_api.wsgi:application
