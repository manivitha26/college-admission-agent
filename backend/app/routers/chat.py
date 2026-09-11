"""
app/routers/chat.py
-------------------
POST /api/chat  — the main chatbot endpoint.

The router itself is intentionally thin:
  1. Validate the request body (Pydantic does this automatically).
  2. Call rag_chain.ask() — the RAG pipeline lives there, not here.
  3. Map the result to a ChatResponse and return it.

The embeddings object is injected via FastAPI's dependency injection system
so it is created once at app startup (in main.py lifespan) and reused for
every request rather than re-loading the 90 MB model on every call.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models.schemas import (
    AskRequest,
    AskResponse,
    AskSource,
    ChatRequest,
    ChatResponse,
    EligibilityRequest,
    EligibilityResponse,
    EligibilitySource,
    SourceDoc,
)
from app.services import rag_chain
from app.services.rag_chain import ChatResult
from app.prompts.admission_prompt import (
    ELIGIBILITY_DISCLAIMER,
    ELIGIBILITY_SYSTEM_PROMPT,
    format_eligibility_question,
    format_context_block,
)
from app.services.granite import _get_llm, _extract_sources, _clean_answer
from app.services import vectorstore as vs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


# ---------------------------------------------------------------------------
# Dependency — injects the shared embeddings object from app state
# ---------------------------------------------------------------------------

def _get_embeddings(request: Request):
    """
    FastAPI dependency that reads the pre-loaded HuggingFaceEmbeddings
    instance from app.state (set in main.py lifespan).

    Raises HTTP 503 if the embeddings object is not ready (e.g. the server
    started but the model failed to load).
    """
    embeddings = getattr(request.app.state, "embeddings", None)
    if embeddings is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Embedding model is not loaded. "
                "The server may still be starting up — please retry in a moment."
            ),
        )
    return embeddings


# ---------------------------------------------------------------------------
# POST /ask  — simple endpoint with the exact schema {question} / {answer, sources}
# ---------------------------------------------------------------------------

@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a college admission question",
    description=(
        "Retrieves relevant chunks from the document vector store, sends them "
        "as context to IBM Granite, and returns the answer with the source "
        "document name and page number for each citation."
    ),
    responses={
        400: {"description": "Question is empty or too long."},
        422: {"description": "Request body failed validation."},
        500: {"description": "Unexpected server error."},
        503: {"description": "Embedding model or IBM credentials not ready."},
    },
)
async def ask(
    body: AskRequest,
    embeddings=Depends(_get_embeddings),
) -> AskResponse:
    """
    Full RAG pipeline:

    1. Embed the question with the local sentence-transformers model.
    2. Search ChromaDB for the top-k most relevant document chunks.
    3. Build a SYSTEM + CONTEXT + QUESTION prompt.
    4. Call IBM Granite (watsonx.ai) — answer is generated strictly from
       the retrieved context; if the context does not contain the answer,
       Granite returns the "information not available" message.
    5. Return { answer, sources: [{ document, page }] }.

    Error handling
    --------------
    EnvironmentError  → 503  (IBM credentials missing in .env)
    ValueError        → 400  (malformed input that slips past Pydantic)
    Any other error   → 500  (logged server-side; safe message to client)
    """
    logger.info("/ask question=%r", body.question[:120])

    try:
        result: ChatResult = rag_chain.ask(
            question=body.question,
            embeddings=embeddings,
        )

    except EnvironmentError as exc:
        # WATSONX_API_KEY / WATSONX_PROJECT_ID not set in .env
        logger.error("/ask credentials error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "IBM watsonx credentials are not configured. "
                "Set WATSONX_API_KEY and WATSONX_PROJECT_ID in backend/.env"
            ),
        )

    except ValueError as exc:
        logger.warning("/ask bad input: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception:
        logger.exception("/ask unexpected error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "An error occurred while processing your question. "
                "Please try again."
            ),
        )

    # Map internal Source dataclasses → AskSource (uses "document" not "file_name").
    sources = [
        AskSource(document=s.file_name, page=s.page)
        for s in result.sources
    ]

    logger.info("/ask answered, sources=%d", len(sources))
    return AskResponse(answer=result.answer, sources=sources)


# ---------------------------------------------------------------------------
# POST /api/eligibility
# ---------------------------------------------------------------------------

@router.post(
    "/eligibility",
    response_model=EligibilityResponse,
    summary="Check course eligibility based on academic marks",
    description=(
        "Retrieves official eligibility criteria from the document store, "
        "compares the student's marks against them using IBM Granite, and "
        "returns a structured analysis. Does NOT guarantee admission."
    ),
    responses={
        422: {"description": "Marks out of range or course name missing."},
        500: {"description": "Unexpected server error."},
        503: {"description": "Embedding model or IBM credentials not ready."},
    },
)
async def check_eligibility(
    body: EligibilityRequest,
    embeddings=Depends(_get_embeddings),
) -> EligibilityResponse:
    """
    Eligibility RAG pipeline:

    1. Build a natural-language question from the student's marks + course.
    2. Retrieve the top-k eligibility-related chunks from ChromaDB.
    3. Build a specialised prompt (ELIGIBILITY_SYSTEM_PROMPT) that instructs
       Granite to compare marks against published criteria — never to guarantee
       admission.
    4. Call IBM Granite and return:
         analysis   — structured eligibility analysis
         disclaimer — fixed "does not guarantee admission" warning
         sources    — documents and pages cited
    """
    logger.info(
        "/eligibility course=%r pct=%.1f maths=%.1f phy=%.1f chem=%.1f",
        body.preferred_course,
        body.percentage_12th,
        body.maths_marks,
        body.physics_marks,
        body.chemistry_marks,
    )

    # Build the retrieval query from the student's data.
    question = format_eligibility_question(
        percentage_12th=body.percentage_12th,
        maths_marks=body.maths_marks,
        physics_marks=body.physics_marks,
        chemistry_marks=body.chemistry_marks,
        preferred_course=body.preferred_course,
    )

    try:
        # Retrieve relevant eligibility chunks from ChromaDB.
        from config import settings
        context_docs = vs.similarity_search(
            query=question,
            embeddings=embeddings,
            k=settings.RETRIEVAL_TOP_K,
        )

        if not context_docs:
            return EligibilityResponse(
                analysis=(
                    "I could not find eligibility criteria for "
                    f"'{body.preferred_course}' in the available official documents. "
                    "Please contact the admissions office directly."
                ),
                disclaimer=ELIGIBILITY_DISCLAIMER,
                sources=[],
            )

        # Build the eligibility-specific prompt (different system prompt
        # from the general chat — stricter about the structured output format
        # and explicitly forbids guaranteeing admission).
        context_block = format_context_block(context_docs)
        prompt = (
            f"SYSTEM:\n{ELIGIBILITY_SYSTEM_PROMPT}\n\n"
            f"CONTEXT:\n{context_block}\n\n"
            f"STUDENT PROFILE AND QUESTION:\n{question}\n\n"
            f"ELIGIBILITY ANALYSIS:\n"
        )

        # Call IBM Granite.
        llm = _get_llm()
        raw = llm.invoke(prompt)
        analysis = _clean_answer(raw, question)

        if not analysis:
            analysis = (
                "I could not find eligibility criteria for "
                f"'{body.preferred_course}' in the available official documents."
            )

        # Extract source citations from the retrieved chunks.
        raw_sources = _extract_sources(context_docs)
        sources = [
            EligibilitySource(document=s.file_name, page=s.page)
            for s in raw_sources
        ]

    except EnvironmentError as exc:
        logger.error("/eligibility credentials error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "IBM watsonx credentials are not configured. "
                "Set WATSONX_API_KEY and WATSONX_PROJECT_ID in backend/.env"
            ),
        )

    except Exception:
        logger.exception("/eligibility unexpected error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while checking eligibility. Please try again.",
        )

    logger.info("/eligibility answered, sources=%d", len(sources))
    return EligibilityResponse(
        analysis=analysis,
        disclaimer=ELIGIBILITY_DISCLAIMER,
        sources=sources,
    )


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask the college admission chatbot a question",
    description=(
        "Accepts a question, retrieves relevant chunks from the document "
        "vector store, sends them as context to IBM Granite, and returns "
        "the answer with source citations."
    ),
)
async def chat(
    body: ChatRequest,
    embeddings=Depends(_get_embeddings),
) -> ChatResponse:
    """
    Full RAG pipeline per request:

    1. Embed the question  (done inside vectorstore.similarity_search)
    2. Retrieve top-k chunks from ChromaDB
    3. Build a strict prompt (SYSTEM + CONTEXT + QUESTION)
    4. Call IBM Granite via WatsonxLLM.invoke()
    5. Return ChatResponse { answer, sources, retrieval_count }

    Error handling
    --------------
    - EnvironmentError (missing watsonx credentials) → HTTP 503
    - Any unexpected exception → HTTP 500 with a safe error message
      (the original exception is logged server-side, not exposed to the client)
    """
    logger.info("chat: question=%r", body.question[:120])

    try:
        result: ChatResult = rag_chain.ask(
            question=body.question,
            embeddings=embeddings,
        )
    except EnvironmentError as exc:
        # Credentials not configured — give the developer a clear message.
        logger.error("chat: credentials error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        # Unexpected error (network issue, ChromaDB failure, etc.)
        logger.exception("chat: unexpected error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "An error occurred while processing your question. "
                "Please try again."
            ),
        ) from exc

    # Map the internal Source dataclass to the Pydantic SourceDoc schema.
    source_docs = [
        SourceDoc(
            file_name=s.file_name,
            page=s.page,
            admission_year=s.admission_year,
        )
        for s in result.sources
    ]

    response = ChatResponse(
        answer=result.answer,
        sources=source_docs,
        retrieval_count=len(result.sources),
    )

    logger.info(
        "chat: answered with %d source(s), retrieval_count=%d",
        len(source_docs),
        response.retrieval_count,
    )

    return response
