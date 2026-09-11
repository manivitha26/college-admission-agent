"""
ingest.py
---------
Standalone CLI script — run this once (or whenever you add new PDFs) to
populate the ChromaDB vector store from all PDF files in the documents folder.

Usage
-----
    # From the backend/ directory:
    python ingest.py

    # Ingest a single specific file instead of the whole folder:
    python ingest.py --file data/pdfs/admission_brochure_2024.pdf

    # Point to a different PDF directory:
    python ingest.py --dir /path/to/my/pdfs

    # Reset the vector store before ingesting (removes all existing data):
    python ingest.py --reset

    # Combine flags:
    python ingest.py --reset --dir /path/to/my/pdfs

Exit codes
----------
    0  — success
    1  — no PDFs found or fatal error
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure Python can find config.py and the app package regardless of the
# working directory from which this script is called.
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BACKEND_DIR))

from config import settings
from app.services.llm import get_embeddings
from app.services.ingestion import ingest_pdf, ingest_all


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_vectorstore() -> None:
    """
    Delete the ChromaDB persistence directory so the next run starts fresh.
    Use --reset when you want to re-ingest everything from scratch.
    """
    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
        print(f"[reset]  Deleted existing vector store at {persist_dir}")
    else:
        print(f"[reset]  Nothing to delete — {persist_dir} does not exist yet.")

    # Re-create the empty directory so ChromaDB can initialise cleanly.
    persist_dir.mkdir(parents=True, exist_ok=True)


def _print_banner() -> None:
    print()
    print("=" * 60)
    print("  College Admission Agent — Document Ingestion")
    print("=" * 60)


def _print_summary(results: list, elapsed: float) -> None:
    """Print a table of results and the total chunk count."""
    print()
    print("-" * 60)
    print(f"  {'File':<40} {'Chunks':>6}")
    print("-" * 60)

    total_chunks = 0
    for file_name, chunk_count in results:
        # Truncate long names so the table stays readable.
        display_name = (file_name[:37] + "...") if len(file_name) > 40 else file_name
        print(f"  {display_name:<40} {chunk_count:>6}")
        total_chunks += chunk_count

    print("-" * 60)
    print(f"  {'TOTAL':<40} {total_chunks:>6}")
    print(f"  Time: {elapsed:.1f}s")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest PDF documents into the ChromaDB vector store.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Ingest a single PDF file instead of the whole directory.",
    )
    parser.add_argument(
        "--dir",
        metavar="PATH",
        default=settings.PDF_UPLOAD_DIR,
        help=(
            f"Directory containing PDF files to ingest. "
            f"Defaults to PDF_UPLOAD_DIR from .env ({settings.PDF_UPLOAD_DIR})."
        ),
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Delete the existing vector store before ingesting. "
            "Use this to rebuild from scratch."
        ),
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """
    Entry point.  Returns 0 on success, 1 on failure.
    """
    _print_banner()

    parser = _build_arg_parser()
    args = parser.parse_args()

    # ── Optional reset ────────────────────────────────────────────────────
    if args.reset:
        _reset_vectorstore()

    # ── Load the embedding model ─────────────────────────────────────────
    # The model is downloaded on first run (~90 MB) and cached locally.
    # Subsequent runs load it from cache and are instant.
    print(f"[embed]  Loading embedding model: {settings.EMBEDDING_MODEL} ...")
    embeddings = get_embeddings()
    print(f"[embed]  Model ready.")

    start_time = time.time()

    # ── Ingest ────────────────────────────────────────────────────────────
    if args.file:
        # ── Single file mode ──────────────────────────────────────────────
        pdf_path = Path(args.file)
        if not pdf_path.exists():
            print(f"[error]  File not found: {pdf_path}")
            return 1
        if pdf_path.suffix.lower() != ".pdf":
            print(f"[error]  Not a PDF file: {pdf_path}")
            return 1

        print(f"[ingest] Processing: {pdf_path.name}")
        file_name, chunk_count = ingest_pdf(str(pdf_path), embeddings)
        results = [(file_name, chunk_count)]

    else:
        # ── Directory mode (default) ──────────────────────────────────────
        pdf_dir = Path(args.dir)
        print(f"[ingest] Scanning directory: {pdf_dir}")

        try:
            results = ingest_all(str(pdf_dir), embeddings)
        except FileNotFoundError as exc:
            print(f"[error]  {exc}")
            return 1

    elapsed = time.time() - start_time

    # ── Report ────────────────────────────────────────────────────────────
    if not results:
        print("[ingest] No documents were ingested.")
        return 1

    _print_summary(results, elapsed)

    total = sum(c for _, c in results)
    print(
        f"[done]   {len(results)} file(s) ingested, "
        f"{total} chunk(s) stored in ChromaDB.\n"
        f"         Vector store: {settings.CHROMA_PERSIST_DIR}"
    )
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
