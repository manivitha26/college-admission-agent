"""
app/services/vectorstore.py
---------------------------
All ChromaDB interactions live here.

Public API
----------
get_vectorstore(embeddings)
    Open (or create) the persistent ChromaDB collection and return a
    LangChain Chroma wrapper ready for similarity search.

add_documents(docs, embeddings)
    Embed a list of LangChain Document objects and upsert them into the
    collection.  Uses upsert so re-running ingestion on the same file is
    safe — duplicate chunks are replaced rather than duplicated.

similarity_search(query, embeddings, k)
    Return the k most-relevant Document objects for the given query string.
    Each Document carries its text in .page_content and metadata
    (source, page, course, admission_year) in .metadata.
"""

import sys
from pathlib import Path
from typing import List

# Allow imports from backend/ root when run as a standalone script.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

from config import settings


# ---------------------------------------------------------------------------
# Internal helper — open or create the collection
# ---------------------------------------------------------------------------

def _open_chroma(embeddings: HuggingFaceEmbeddings) -> Chroma:
    """
    Return a Chroma instance backed by the persisted directory on disk.

    ChromaDB automatically creates the directory and SQLite database if
    they do not exist yet, so no manual setup is required.
    """
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def get_vectorstore(embeddings: HuggingFaceEmbeddings) -> Chroma:
    """
    Open the persistent ChromaDB collection and return it.

    Use this in the FastAPI app at startup so the retriever is ready before
    the first request arrives.
    """
    return _open_chroma(embeddings)


def add_documents(
    docs: List[Document],
    embeddings: HuggingFaceEmbeddings,
) -> int:
    """
    Embed and store a list of Document chunks in ChromaDB.

    Each Document must have at least:
        doc.page_content  — the chunk text
        doc.metadata      — dict with keys: source, page, course,
                            admission_year (and any extras)

    Returns the number of chunks stored.

    The function uses Chroma.add_documents() which performs an upsert under
    the hood: if a chunk with the same id already exists it is replaced,
    so re-ingesting the same PDF is idempotent.
    """
    if not docs:
        return 0

    db = _open_chroma(embeddings)

    # Build deterministic IDs from (source filename + page + chunk index)
    # so that re-ingestion overwrites existing chunks for the same file.
    ids = [
        f"{doc.metadata.get('source', 'unknown')}_p{doc.metadata.get('page', 0)}_c{i}"
        for i, doc in enumerate(docs)
    ]

    db.add_documents(documents=docs, ids=ids)
    return len(docs)


def similarity_search(
    query: str,
    embeddings: HuggingFaceEmbeddings,
    k: int = None,
) -> List[Document]:
    """
    Retrieve the k most relevant chunks for the given query.

    Args:
        query     : the user's natural-language question
        embeddings: the same embeddings object used during ingestion
        k         : number of chunks to return (defaults to settings.RETRIEVAL_TOP_K)

    Returns a list of Document objects, each containing:
        .page_content  — the matching chunk text
        .metadata      — source, page, course, admission_year, etc.
    """
    if k is None:
        k = settings.RETRIEVAL_TOP_K

    db = _open_chroma(embeddings)
    return db.similarity_search(query, k=k)
