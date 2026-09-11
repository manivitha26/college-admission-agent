"""
app/services/granite.py
-----------------------
IBM Granite integration — the only file in the project that talks to watsonx.ai.

Responsibilities
----------------
1. Validate that the required IBM credentials exist in the environment.
2. Build a WatsonxLLM instance pointing at IBM Granite.
3. Expose a single public function:

       answer = ask_granite(question, context_docs)

   This function:
     - Formats the retrieved document chunks into a numbered context block.
     - Builds a strict prompt that forbids the model from answering outside
       the provided context.
     - Calls IBM Granite and returns a GraniteResponse dataclass containing
       the answer text and the source citations.

Design rules (never break these)
---------------------------------
- Credentials are read exclusively from `config.settings`.  No value is
  ever hard-coded in this file.
- If the context chunks contain no relevant text the model is instructed to
  return the NOT_FOUND_MESSAGE rather than guessing.
- The prompt is constructed here, not scattered across other modules.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Allow running this file directly for quick smoke-tests.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.documents import Document
from langchain_ibm import WatsonxLLM

from config import settings
from app.prompts.admission_prompt import (
    NOT_FOUND_MESSAGE,
    SYSTEM_PROMPT,
    format_context_block,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum characters of a single chunk's text included in the prompt.
# Keeps the prompt within token limits for large PDFs.
_MAX_CHUNK_CHARS = 1200


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------

@dataclass
class SourceDoc:
    """One cited source returned with every Granite answer."""
    file_name: str       # PDF file name, e.g. "admission_brochure_2024.pdf"
    page: int            # 1-based page number
    admission_year: str  # e.g. "2024", or "" if not found in the chunk metadata


@dataclass
class GraniteResponse:
    """What ask_granite() returns to the caller."""
    answer: str                          # The model's answer (or NOT_FOUND_MESSAGE)
    sources: List[SourceDoc] = field(default_factory=list)  # Deduplicated citations


# ---------------------------------------------------------------------------
# LLM factory  (module-private — callers use ask_granite(), not get_llm())
# ---------------------------------------------------------------------------

def _get_llm() -> WatsonxLLM:
    """
    Build and return a WatsonxLLM instance for IBM Granite.

    Called once per request (LangChain's WatsonxLLM is stateless so this is
    cheap).  Raises EnvironmentError with a clear message if credentials are
    missing so developers get an actionable error immediately on startup.
    """
    missing = []
    if not settings.WATSONX_API_KEY:
        missing.append("WATSONX_API_KEY")
    if not settings.WATSONX_PROJECT_ID:
        missing.append("WATSONX_PROJECT_ID")

    if missing:
        raise EnvironmentError(
            f"Missing IBM watsonx credentials: {', '.join(missing)}\n"
            "Copy backend/.env.example to backend/.env and fill in your values.\n"
            "See docs/setup.md for instructions on obtaining these credentials."
        )

    return WatsonxLLM(
        model_id=settings.GRANITE_MODEL_ID,
        url=settings.WATSONX_URL,
        apikey=settings.WATSONX_API_KEY,
        project_id=settings.WATSONX_PROJECT_ID,
        params={
            # Enough tokens for a thorough, multi-paragraph answer.
            "max_new_tokens": 512,
            # Low temperature → deterministic, factual output.
            # We never want creative hallucinations here.
            "temperature": 0.1,
            # Discourage the model from repeating phrases verbatim.
            "repetition_penalty": 1.1,
            # Stop generation at these tokens (Granite chat format).
            "stop_sequences": ["<|endoftext|>", "\n\nQuestion:"],
        },
    )


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(question: str, context_docs: List[Document]) -> str:
    """
    Build the full prompt string sent to IBM Granite.

    Uses the shared SYSTEM_PROMPT and format_context_block() from
    admission_prompt.py so the wording is maintained in one place.

    Structure:  SYSTEM  →  CONTEXT  →  QUESTION  →  ANSWER:
    Granite instruction-tuned models respond reliably to this layout.
    """
    context_block = format_context_block(context_docs, _MAX_CHUNK_CHARS)

    prompt = (
        f"SYSTEM:\n{SYSTEM_PROMPT}\n\n"
        f"CONTEXT:\n{context_block}\n\n"
        f"QUESTION:\n{question.strip()}\n\n"
        f"ANSWER:\n"
    )
    return prompt


# ---------------------------------------------------------------------------
# Source extractor
# ---------------------------------------------------------------------------

def _extract_sources(context_docs: List[Document]) -> List[SourceDoc]:
    """
    Build a deduplicated list of SourceDoc citations from the retrieved chunks.

    Deduplication is by (file_name, page) pair so repeated chunks from the
    same page appear only once in the UI.

    admission_year is taken from the chunk metadata where ingestion.py stored
    it (extracted by regex from the PDF text). Empty string when not present.
    """
    seen: set = set()
    sources: List[SourceDoc] = []
    for doc in context_docs:
        file_name      = doc.metadata.get("source", "unknown")
        page           = doc.metadata.get("page", 0)
        admission_year = doc.metadata.get("admission_year", "")
        key = (file_name, page)
        if key not in seen:
            seen.add(key)
            sources.append(
                SourceDoc(
                    file_name=file_name,
                    page=page,
                    admission_year=admission_year,
                )
            )
    return sources


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ask_granite(
    question: str,
    context_docs: List[Document],
) -> GraniteResponse:
    """
    Send a question + retrieved document chunks to IBM Granite and return
    the answer with source citations.

    Parameters
    ----------
    question     : the user's natural-language question
    context_docs : list of Document objects returned by the vector store
                   similarity search — each has .page_content and .metadata

    Returns
    -------
    GraniteResponse
        .answer  — Granite's answer string, or NOT_FOUND_MESSAGE
        .sources — deduplicated list of SourceDoc(file_name, page)

    How it works
    ------------
    1. Build a strict prompt that places the context and question into a
       structured template (see _build_prompt).
    2. Call WatsonxLLM.invoke() — a single synchronous HTTP request to the
       watsonx.ai inference API.
    3. Clean up the raw output (strip leading/trailing whitespace, remove
       any accidentally echoed prompt fragments).
    4. Return the cleaned answer together with source citations extracted
       from the chunk metadata.
    """
    # Build the prompt string.
    prompt = _build_prompt(question, context_docs)

    # Call IBM Granite via the LangChain WatsonxLLM wrapper.
    llm = _get_llm()
    raw_answer: str = llm.invoke(prompt)

    # Clean up the model output.
    answer = _clean_answer(raw_answer, question)

    # Build source citations from the chunk metadata.
    sources = _extract_sources(context_docs)

    return GraniteResponse(answer=answer, sources=sources)


# ---------------------------------------------------------------------------
# Output cleaner
# ---------------------------------------------------------------------------

def _clean_answer(raw: str, question: str) -> str:
    """
    Normalise the raw text returned by Granite.

    Handles edge cases:
    - Empty or whitespace-only output → return NOT_FOUND_MESSAGE.
    - Output that starts by echoing the question or the word "ANSWER:" →
      strip that prefix (happens occasionally with some Granite checkpoints).
    - Strip leading/trailing whitespace.
    """
    text = raw.strip()

    if not text:
        return NOT_FOUND_MESSAGE

    # Remove accidental "ANSWER:" prefix the model sometimes produces.
    if text.upper().startswith("ANSWER:"):
        text = text[len("ANSWER:"):].strip()

    # Remove accidental echo of the question at the start of the answer.
    if text.lower().startswith(question.strip().lower()):
        text = text[len(question.strip()):].strip()

    return text if text else NOT_FOUND_MESSAGE
