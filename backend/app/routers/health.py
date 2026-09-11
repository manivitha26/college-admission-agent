"""
app/routers/health.py
---------------------
GET /api/health — liveness and readiness check.

Returns whether the server is up, whether ChromaDB has been populated,
and the total number of stored chunks.  Useful for the frontend to show
a "documents not loaded yet" warning and for ops monitoring.
"""

import logging
from fastapi import APIRouter, Request

from config import settings
from app.models.schemas import HealthResponse
from app.services.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Server liveness and readiness check",
)
async def health_check(request: Request) -> HealthResponse:
    """
    Returns:
    - status           : always "ok" if the server is running
    - vectorstore_ready: True when ChromaDB has at least one chunk
    - collection_name  : the active ChromaDB collection name
    - document_count   : total chunks stored (0 = ingest.py not run yet)
    """
    embeddings = getattr(request.app.state, "embeddings", None)
    document_count = 0
    vectorstore_ready = False

    if embeddings is not None:
        try:
            vs = get_vectorstore(embeddings)
            document_count = vs._collection.count()
            vectorstore_ready = document_count > 0
        except Exception as exc:
            logger.warning("health: could not query ChromaDB — %s", exc)

    return HealthResponse(
        status="ok",
        vectorstore_ready=vectorstore_ready,
        collection_name=settings.CHROMA_COLLECTION,
        document_count=document_count,
    )
