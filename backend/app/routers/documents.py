"""
app/routers/documents.py
------------------------
POST /api/upload    — upload a PDF and ingest it into ChromaDB
GET  /api/documents — list all ingested PDF files
"""

import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from config import settings
from app.models.schemas import DocumentInfo, UploadResponse
from app.services.ingestion import ingest_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


def _get_embeddings(request: Request):
    embeddings = getattr(request.app.state, "embeddings", None)
    if embeddings is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model not ready.",
        )
    return embeddings


# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a PDF document and ingest it into the vector store",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to ingest"),
    embeddings=Depends(_get_embeddings),
) -> UploadResponse:
    """
    Save the uploaded PDF to PDF_UPLOAD_DIR, then run the full ingestion
    pipeline (load → split → embed → store in ChromaDB).
    """
    # Validate file type by extension.
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    pdf_dir = Path(settings.PDF_UPLOAD_DIR)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    dest = pdf_dir / file.filename

    # Save the uploaded bytes to disk.
    try:
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        await file.close()

    logger.info("upload: saved %s (%d bytes)", file.filename, dest.stat().st_size)

    # Ingest into ChromaDB.
    try:
        _, chunk_count = ingest_pdf(str(dest), embeddings)
    except Exception as exc:
        logger.exception("upload: ingestion failed for %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File saved but ingestion failed: {exc}",
        ) from exc

    logger.info("upload: ingested %s → %d chunks", file.filename, chunk_count)

    return UploadResponse(
        message=f"Successfully ingested {file.filename}",
        file_name=file.filename,
        chunks=chunk_count,
    )


# ---------------------------------------------------------------------------
# GET /api/documents
# ---------------------------------------------------------------------------

@router.get(
    "/documents",
    response_model=list[DocumentInfo],
    summary="List all ingested PDF documents",
)
async def list_documents() -> list[DocumentInfo]:
    """
    Return every PDF file currently in PDF_UPLOAD_DIR.
    These are the files whose content has been (or will be) indexed.
    """
    pdf_dir = Path(settings.PDF_UPLOAD_DIR)
    if not pdf_dir.exists():
        return []

    docs = []
    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        size_kb = round(pdf_file.stat().st_size / 1024, 1)
        docs.append(DocumentInfo(file_name=pdf_file.name, file_size_kb=size_kb))

    return docs
