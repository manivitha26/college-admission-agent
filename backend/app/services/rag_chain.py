"""
app/services/rag_chain.py
-------------------------
Orchestrates the full Retrieval-Augmented Generation (RAG) pipeline.

This is the single entry point that the FastAPI chat router calls.
It wires together:

    User question
        │
        ▼
    vectorstore.similarity_search()   ← retrieves the k most relevant chunks
        │
        ▼
    granite.ask_granite()             ← sends context + question to IBM Granite
        │
        ▼
    ChatResponse                      ← answer + source citations

Public API
----------
    ask(question, embeddings) -> ChatResult

        ChatResult.answer   : str           — Granite's answer
        ChatResult.sources  : list[Source]  — deduplicated (file_name, page) pairs
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Allow running this file directly for smoke-tests.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_community.embeddings import HuggingFaceEmbeddings

from config import settings
from app.services import vectorstore as vs
from app.services.granite import ask_granite, GraniteResponse
from app.prompts.admission_prompt import NOT_FOUND_MESSAGE


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

@dataclass
class Source:
    """A single source citation returned to the API caller."""
    file_name: str
    page: int
    admission_year: str = ""   # e.g. "2024"; empty string when not available


@dataclass
class ChatResult:
    """
    The object returned by ask() to the FastAPI chat router.

    Attributes
    ----------
    answer  : the answer text (or the "not found" message)
    sources : list of unique (file_name, page) citations
              Empty when no relevant chunks were found or when the
              answer is the "not found" message.
    """
    answer: str
    sources: List[Source] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------

def ask(question: str, embeddings: HuggingFaceEmbeddings) -> ChatResult:
    """
    Run the full RAG pipeline for one user question.

    Steps
    -----
    1. Retrieve the top-k most relevant document chunks from ChromaDB using
       cosine similarity between the question embedding and stored chunk
       embeddings.

    2. If no chunks are found at all, return the "not found" response
       immediately without calling the LLM (saves API cost).

    3. Send the chunks + question to IBM Granite via granite.ask_granite().
       Granite is instructed to answer only from the provided context.

    4. If Granite returns an empty string (should not happen but handled
       defensively), substitute the "not found" message.

    5. Convert the GraniteResponse into a ChatResult and return it.

    Parameters
    ----------
    question   : the raw user question string
    embeddings : the shared HuggingFaceEmbeddings instance (created once at
                 app startup and reused for every request)

    Returns
    -------
    ChatResult with .answer and .sources populated.
    """

    # ── Step 1: Retrieve relevant chunks ──────────────────────────────────
    context_docs = vs.similarity_search(
        query=question,
        embeddings=embeddings,
        k=settings.RETRIEVAL_TOP_K,
    )

    # ── Step 2: Short-circuit if vector store is empty ────────────────────
    # This handles the edge case where ingest.py has never been run.
    if not context_docs:
        return ChatResult(
            answer=NOT_FOUND_MESSAGE,
            sources=[],
        )

    # ── Step 3: Ask IBM Granite ────────────────────────────────────────────
    response: GraniteResponse = ask_granite(
        question=question,
        context_docs=context_docs,
    )

    # ── Step 4: Defensive empty-answer guard ──────────────────────────────
    answer = response.answer.strip() or NOT_FOUND_MESSAGE

    # ── Step 5: Convert sources to the public type ────────────────────────
    # granite.py returns GraniteResponse with SourceDoc objects;
    # we map them to our public Source type here so the router doesn't
    # need to import from granite.py directly.
    sources: List[Source] = []
    if answer != NOT_FOUND_MESSAGE:
        # Only attach citations when a real answer was found.
        sources = [
            Source(
                file_name=s.file_name,
                page=s.page,
                admission_year=s.admission_year,
            )
            for s in response.sources
        ]

    return ChatResult(answer=answer, sources=sources)
