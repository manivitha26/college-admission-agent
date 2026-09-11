"""
app/services/ingestion.py
-------------------------
PDF ingestion pipeline — the heart of the document processing system.

Pipeline steps
--------------
1. load_pdf(path)
       PyPDFLoader reads the PDF and returns one Document per page.
       Each Document already has metadata: { source: <path>, page: <int> }.

2. enrich_metadata(docs, file_name)
       Adds extra fields to every Document's metadata:
         - source      → just the file name (not the full path)
         - course      → extracted from the file name or page text
         - admission_year → four-digit year found in the text, if any

3. split_documents(docs)
       RecursiveCharacterTextSplitter breaks each page-Document into
       smaller overlapping chunks.  Chunk size and overlap come from
       settings so they can be tuned via environment variables.

4. ingest_pdf(path, embeddings)
       Orchestrates the above steps and calls vectorstore.add_documents()
       to embed and persist everything.

5. ingest_all(pdf_dir, embeddings)
       Walks an entire directory and calls ingest_pdf() for every .pdf file.
       Designed for batch ingestion at startup or from ingest.py.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Allow imports from backend/ root when run as a standalone script.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from app.services import vectorstore as vs


# ---------------------------------------------------------------------------
# Step 1 — Load PDF
# ---------------------------------------------------------------------------

def load_pdf(pdf_path: str) -> List[Document]:
    """
    Load a PDF and return a list of Documents, one per page.

    LangChain's PyPDFLoader already sets:
        doc.metadata["source"] = pdf_path  (full path string)
        doc.metadata["page"]   = 0-based page index

    We convert the page index to 1-based here so it matches what users
    see when they open the PDF in a viewer.
    """
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    # Convert 0-based page index to 1-based for human-friendly citations.
    for doc in pages:
        doc.metadata["page"] = doc.metadata.get("page", 0) + 1

    return pages


# ---------------------------------------------------------------------------
# Step 2 — Enrich metadata
# ---------------------------------------------------------------------------

# Regex patterns used to extract optional metadata from the file name / text.
_YEAR_RE = re.compile(r"\b(20\d{2})\b")          # matches 2000-2099
_COURSE_KEYWORDS = [                               # common course tokens
    "btech", "mtech", "bsc", "msc", "ba", "ma",
    "mba", "bca", "mca", "phd", "diploma", "pgdm",
]


def _extract_course(file_name: str, text: str) -> str:
    """
    Try to detect the course name.

    Strategy (in order):
      1. Look for a known course keyword in the PDF file name.
      2. Look for a known course keyword in the first 500 characters of text.
      3. Return empty string if nothing is found.
    """
    combined = (file_name + " " + text[:500]).lower()
    for keyword in _COURSE_KEYWORDS:
        if keyword in combined:
            return keyword.upper()
    return ""


def _extract_admission_year(text: str) -> str:
    """
    Return the first four-digit year in the range 2000-2099 found in the
    text, or an empty string if none is present.
    """
    match = _YEAR_RE.search(text)
    return match.group(1) if match else ""


def enrich_metadata(docs: List[Document], file_name: str) -> List[Document]:
    """
    Add course and admission_year fields to every Document's metadata,
    and replace the raw 'source' path with just the file name.

    This function mutates the Documents in-place and returns them so the
    call can be chained.
    """
    for doc in docs:
        text = doc.page_content

        # Replace the full file-system path with just the PDF file name so
        # citations shown to users are clean and portable.
        doc.metadata["source"] = file_name

        # Optional enrichment — store empty string rather than None so
        # ChromaDB metadata serialisation never fails.
        doc.metadata["course"] = _extract_course(file_name, text)
        doc.metadata["admission_year"] = _extract_admission_year(text)

    return docs


# ---------------------------------------------------------------------------
# Step 3 — Split into chunks
# ---------------------------------------------------------------------------

def split_documents(docs: List[Document]) -> List[Document]:
    """
    Split page-level Documents into smaller overlapping chunks.

    RecursiveCharacterTextSplitter tries to break on paragraph boundaries
    (double newline), then single newlines, then spaces, and only splits in
    the middle of a word as a last resort.

    Chunk size and overlap are read from settings so they can be tuned
    without touching this code:
        CHUNK_SIZE    (default 800 chars)
        CHUNK_OVERLAP (default 150 chars)

    Metadata (source, page, course, admission_year) is automatically
    copied to every child chunk by LangChain.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        # Separators tried in order — prefer semantic boundaries.
        separators=["\n\n", "\n", ". ", " ", ""],
        # Keep the chunk length in characters (not tokens).
        length_function=len,
    )
    chunks = splitter.split_documents(docs)
    return chunks


# ---------------------------------------------------------------------------
# Step 4 — Ingest a single PDF
# ---------------------------------------------------------------------------

def ingest_pdf(
    pdf_path: str,
    embeddings: HuggingFaceEmbeddings,
) -> Tuple[str, int]:
    """
    Full pipeline for one PDF file: load → enrich → split → embed → store.

    Args:
        pdf_path   : absolute or relative path to the .pdf file
        embeddings : the shared HuggingFaceEmbeddings instance

    Returns:
        (file_name, chunk_count) — useful for progress reporting in ingest.py
    """
    path = Path(pdf_path)
    file_name = path.name  # e.g. "admission_brochure_2024.pdf"

    # 1. Load raw pages from the PDF.
    pages = load_pdf(str(path))

    if not pages:
        return file_name, 0

    # 2. Add course / year metadata and clean up the source field.
    pages = enrich_metadata(pages, file_name)

    # 3. Split pages into smaller chunks suitable for embedding.
    chunks = split_documents(pages)

    # 4. Embed chunks and store them in ChromaDB.
    stored = vs.add_documents(chunks, embeddings)

    return file_name, stored


# ---------------------------------------------------------------------------
# Step 5 — Ingest an entire directory
# ---------------------------------------------------------------------------

def ingest_all(
    pdf_dir: str,
    embeddings: HuggingFaceEmbeddings,
) -> List[Tuple[str, int]]:
    """
    Walk pdf_dir and ingest every .pdf file found.

    Skips files that cannot be read (logs a warning) so a single corrupt
    PDF does not abort the whole batch.

    Returns a list of (file_name, chunk_count) tuples — one per PDF.
    """
    pdf_folder = Path(pdf_dir)

    if not pdf_folder.exists():
        raise FileNotFoundError(
            f"PDF directory not found: {pdf_folder}\n"
            "Create it or update PDF_UPLOAD_DIR in backend/.env"
        )

    pdf_files = sorted(pdf_folder.glob("*.pdf"))

    if not pdf_files:
        print(f"[ingest] No .pdf files found in {pdf_folder}")
        return []

    results = []
    for pdf_file in pdf_files:
        try:
            file_name, chunk_count = ingest_pdf(str(pdf_file), embeddings)
            results.append((file_name, chunk_count))
        except Exception as exc:
            # Log and continue — don't let one bad PDF stop the rest.
            print(f"[ingest] WARNING: could not process {pdf_file.name}: {exc}")

    return results
