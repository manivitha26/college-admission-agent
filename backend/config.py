"""
config.py
---------
Central place for every runtime setting.

All values are read from environment variables.
In local development a backend/.env file is loaded automatically by
python-dotenv (load_dotenv is a no-op when the file does not exist).
In production (IBM Cloud Code Engine) the variables are injected by the
platform — no .env file is ever present inside the container.

Import `settings` anywhere in the app — never read os.environ directly
outside this module.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load .env file when running locally.
# load_dotenv() is safe to call even when the file does not exist — it is
# simply a no-op, which is exactly what we want in production containers.
# ---------------------------------------------------------------------------
_ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(_ENV_FILE)

# Base directory = the backend/ folder, used to resolve relative paths.
_BASE = Path(__file__).parent


def _path(env_var: str, default_rel: str) -> str:
    """
    Return an absolute path string for a storage directory.

    Priority:
      1. If env_var is set to an absolute path → use it as-is.
      2. If env_var is set to a relative path  → resolve against _BASE.
      3. Otherwise                             → resolve default_rel against _BASE.

    This makes the app work both in local dev (relative paths) and inside a
    Docker container that mounts a volume at an absolute path like /app/data/…
    """
    raw = os.getenv(env_var, "")
    if raw:
        p = Path(raw)
        return str(p if p.is_absolute() else _BASE / p)
    return str(_BASE / default_rel)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class Settings:
    # ── IBM watsonx credentials ────────────────────────────────────────────
    # These MUST be provided as environment variables in production.
    # Never hard-code values or bake them into a Docker image.
    WATSONX_API_KEY: str    = os.getenv("WATSONX_API_KEY", "")
    WATSONX_PROJECT_ID: str = os.getenv("WATSONX_PROJECT_ID", "")
    WATSONX_URL: str        = os.getenv(
        "WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
    )

    # IBM Granite model ID on watsonx.ai.
    # Lite-tier recommendation: ibm/granite-3-8b-instruct  (faster, lower token cost)
    # Other options: ibm/granite-13b-chat-v2, ibm/granite-20b-multilingual
    GRANITE_MODEL_ID: str = os.getenv(
        "GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct"
    )

    # ── Embedding model (runs locally — no API key required) ───────────────
    # Downloaded once (~90 MB) and cached in HF_HOME / ~/.cache/huggingface/
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
    )

    # ── Storage paths ──────────────────────────────────────────────────────
    # Absolute in containers (volume mount), relative in local dev.
    CHROMA_PERSIST_DIR: str = _path("CHROMA_PERSIST_DIR", "data/vectorstore")
    PDF_UPLOAD_DIR: str     = _path("PDF_UPLOAD_DIR",     "data/pdfs")

    # ── ChromaDB collection name ───────────────────────────────────────────
    CHROMA_COLLECTION: str = os.getenv(
        "CHROMA_COLLECTION", "college_admission_docs"
    )

    # ── Text splitting parameters ──────────────────────────────────────────
    CHUNK_SIZE: int    = int(os.getenv("CHUNK_SIZE",    "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

    # ── RAG retrieval ──────────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "4"))

    # ── Server port (used by the Dockerfile CMD) ───────────────────────────
    # IBM Code Engine routes traffic to $PORT; default 8080.
    PORT: int = int(os.getenv("PORT", "8080"))

    # ─────────────────────────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Log a clear warning if required IBM credentials are missing.

        Called once at startup (main.py lifespan) so developers get an
        actionable message instead of a cryptic 500 error on first request.
        Does NOT raise — the server still starts so the /api/health endpoint
        remains reachable and the documents tab still works.
        """
        missing = [
            var for var, val in [
                ("WATSONX_API_KEY",    self.WATSONX_API_KEY),
                ("WATSONX_PROJECT_ID", self.WATSONX_PROJECT_ID),
            ]
            if not val
        ]
        if missing:
            logger.warning(
                "⚠  IBM watsonx credentials not configured: %s  "
                "Chat and eligibility endpoints will return HTTP 503 until "
                "these environment variables are set.",
                ", ".join(missing),
            )


# Single shared instance — import this everywhere.
settings = Settings()
