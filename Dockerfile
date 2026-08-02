# ============================================================
# CNPI Hybrid RAG - Dockerfile for HuggingFace Spaces
# ============================================================
# Backend: Django + LangGraph + Sentence-Transformers
# HuggingFace Spaces Docker SDK — must expose port 7860
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2 + sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model during build
# This avoids downloading 90MB on every cold start
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" \
    || echo "WARN: Could not pre-download embedding model"

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
ENV PORT=7860

# HuggingFace Spaces requires port 7860
EXPOSE 7860

# Run Django with gunicorn
# --workers 1: HuggingFace free tier has limited RAM; sentence-transformers
#              model + LangGraph need ~1.5GB, so 1 worker is safer
# --timeout 300: RAG pipeline can take 30-60s per query (LLM calls)
# --preload: loads the graph ONCE before workers fork (saves memory)
WORKDIR /app/cnpi_api
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "300", "--preload", "cnpi_api.wsgi:application"]
