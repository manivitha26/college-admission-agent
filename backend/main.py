"""
main.py
-------
FastAPI application entry point.

Responsibilities
----------------
1. Define the application lifespan:
     startup  → load the HuggingFace embedding model once and store it on
                app.state so every request can reuse it without reloading.
     shutdown → nothing to clean up (ChromaDB and the LLM are stateless).

2. Configure CORS so the React dev server (localhost:5173) and any
   production origin can reach the API.

3. Register all routers:
     /api/chat        POST  — RAG chatbot
     /api/upload      POST  — PDF ingestion
     /api/documents   GET   — list ingested documents
     /api/health      GET   — liveness / readiness check

Run (from the backend/ directory, with venv active):
    uvicorn main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from app.services.llm import get_embeddings
from app.services.vectorstore import get_vectorstore
from app.routers import chat, documents, health

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — runs once at startup and once at shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup
    -------
    Load the HuggingFace sentence-transformers embedding model.
    This takes a few seconds on first run (model download) and is instant
    on subsequent runs (loaded from cache).

    The model is stored on app.state.embeddings so every request handler
    can access it via the _get_embeddings() dependency in chat.py.

    Shutdown
    --------
    Nothing to do — ChromaDB persists automatically and WatsonxLLM is
    stateless (a new HTTP call per request).
    """
    # Warn immediately if IBM credentials are missing (before any HTTP traffic).
    settings.validate()

    logger.info("startup: loading embedding model '%s' …", settings.EMBEDDING_MODEL)
    app.state.embeddings = get_embeddings()
    logger.info("startup: embedding model ready.")

    # Verify ChromaDB is reachable and log how many chunks are stored.
    try:
        vs = get_vectorstore(app.state.embeddings)
        count = vs._collection.count()   # internal Chroma API, stable across 0.4+
        if count == 0:
            logger.warning(
                "startup: ChromaDB collection '%s' is empty. "
                "Run  python ingest.py  to load documents.",
                settings.CHROMA_COLLECTION,
            )
        else:
            logger.info(
                "startup: ChromaDB ready — %d chunk(s) in collection '%s'.",
                count,
                settings.CHROMA_COLLECTION,
            )
    except Exception as exc:
        logger.warning("startup: could not verify ChromaDB — %s", exc)

    yield  # ← server is running; requests are processed here

    logger.info("shutdown: goodbye.")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="College Admission Agent",
    description=(
        "RAG-powered chatbot that answers college admission questions "
        "using IBM Granite (via watsonx.ai) and official PDF documents."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

# Allow the React Vite dev server and any localhost origin.
# In production replace the wildcard with your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default
        "http://localhost:3000",   # CRA / other common ports
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(health.router)


# ---------------------------------------------------------------------------
# Root redirect — useful for a quick browser check
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "College Admission Agent API is running.",
        "docs": "/docs",
        "health": "/api/health",
    }
