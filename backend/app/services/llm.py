"""
app/services/llm.py
-------------------
Factory functions that create the two ML objects the rest of the app needs:

  get_embeddings()  →  HuggingFaceEmbeddings
      A locally-running sentence-transformers model.
      No API key required.  The model is downloaded once and cached by
      the sentence-transformers library in ~/.cache/huggingface/.

  get_llm()         →  WatsonxLLM  (IBM Granite via IBM watsonx.ai)
      Requires WATSONX_API_KEY and WATSONX_PROJECT_ID in .env.
      Only used at query time — not during ingestion.

Both functions are intentionally lightweight: they just build and return the
object; they do not store any global state here.  Call them once at startup
and keep the result.
"""

import sys
from pathlib import Path

# Allow imports from the backend/ root when this file is run directly.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ibm import WatsonxLLM

from config import settings


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Return a HuggingFaceEmbeddings instance using the model name from settings.

    The model runs entirely on the local machine — no external API call is
    made during embedding.  On first run the model weights (~90 MB for
    all-MiniLM-L6-v2) are downloaded and cached automatically.
    """
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        # encode_kwargs controls the underlying sentence-transformers call.
        encode_kwargs={"normalize_embeddings": True},
    )


# ---------------------------------------------------------------------------
# LLM (IBM Granite)
# ---------------------------------------------------------------------------

def get_llm() -> WatsonxLLM:
    """
    Return a WatsonxLLM instance pointing at IBM Granite on watsonx.ai.

    Generation parameters chosen for a factual Q&A chatbot:
      - max_new_tokens  : long enough for a thorough answer
      - temperature     : low → deterministic, factual output
      - repetition_penalty: discourages the model from repeating itself
    """
    if not settings.WATSONX_API_KEY:
        raise EnvironmentError(
            "WATSONX_API_KEY is not set.  "
            "Copy backend/.env.example to backend/.env and fill in your credentials."
        )
    if not settings.WATSONX_PROJECT_ID:
        raise EnvironmentError(
            "WATSONX_PROJECT_ID is not set.  "
            "Copy backend/.env.example to backend/.env and fill in your credentials."
        )

    return WatsonxLLM(
        model_id=settings.GRANITE_MODEL_ID,
        url=settings.WATSONX_URL,
        apikey=settings.WATSONX_API_KEY,
        project_id=settings.WATSONX_PROJECT_ID,
        params={
            "max_new_tokens": 512,
            "temperature": 0.1,        # near-deterministic for factual answers
            "repetition_penalty": 1.1,
        },
    )
