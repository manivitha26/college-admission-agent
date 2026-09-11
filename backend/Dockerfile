# ── Stage 1: dependency layer ──────────────────────────────────────────────
# Use a slim Python image. Pinned to 3.12-slim for reproducibility.
FROM python:3.12-slim AS deps

WORKDIR /app

# Install OS packages needed for:
#   - chromadb native extensions (gcc, g++)
#   - sentence-transformers / PyTorch (libgomp)
#   - pdf processing (no extra OS deps needed for pypdf)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first so Docker can cache this layer.
COPY requirements.txt .

# Install all Python dependencies into a dedicated prefix so we can copy
# just the installed packages to the final stage (keeps image lean).
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ──────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# libgomp1 is required at runtime by sentence-transformers / torch.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the build stage.
COPY --from=deps /install /usr/local

WORKDIR /app

# Copy application source (no .venv, no __pycache__, no .env).
COPY app/        ./app/
COPY config.py   ./config.py
COPY ingest.py   ./ingest.py

# Pre-create the data directories so volume mounts work cleanly.
RUN mkdir -p data/pdfs data/vectorstore

# The embedding model cache lives in the HuggingFace default cache dir.
# Map this to a writable volume in production so the model is not
# re-downloaded on every container restart.
ENV HF_HOME=/app/data/hf_cache
RUN mkdir -p data/hf_cache

# ── Runtime configuration ──────────────────────────────────────────────────
# All secrets are injected as environment variables at deploy time.
# No .env file is ever baked into the image.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# IBM Code Engine / Cloud Run route traffic to $PORT.
# Uvicorn reads it at startup.
EXPOSE 8080

# Non-root user — defence-in-depth.
RUN useradd --no-create-home --shell /bin/false appuser \
    && chown -R appuser:appuser /app
USER appuser

# Start uvicorn.  --workers 1 is intentional: ChromaDB's SQLite store is
# not safe for concurrent multi-process writes. Use a read-replica
# pattern or a hosted vector DB for higher concurrency.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
