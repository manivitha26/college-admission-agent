"""
app/prompts/admission_prompt.py
--------------------------------
Prompt constants and helpers used by the RAG chain.

This module is intentionally kept separate from granite.py so the prompt
wording can be adjusted without touching any business logic.

What lives here
---------------
TOPIC_LABELS   — human-readable names for the nine admission topics.
                 Used to detect which topic a question belongs to (optional
                 logging / routing — not required for the RAG pipeline).

NOT_FOUND_MESSAGE
               — The exact string Granite must return when it cannot find the
                 answer in the context.  Imported by both granite.py and any
                 tests so there is a single source of truth.

SYSTEM_PROMPT  — The static system instruction block that is prepended to
                 every Granite request.  Defines the assistant's persona,
                 the nine topics it covers, and the rules it must follow.

format_context_block(docs)
               — Converts a list of LangChain Documents into the numbered
                 CONTEXT block that is injected between the system prompt and
                 the user question.
"""

from typing import List
from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Shared constant — single source of truth for the "not found" reply
# ---------------------------------------------------------------------------

NOT_FOUND_MESSAGE = (
    "I could not find this information in the available official documents."
)


# ---------------------------------------------------------------------------
# Topic labels
# The chatbot is designed to answer questions in these nine areas.
# These labels are used for logging and can be used for UI category filters.
# ---------------------------------------------------------------------------

TOPIC_LABELS = [
    "Courses",
    "Eligibility",
    "Fees",
    "Admission Procedure",
    "Required Documents",
    "Important Dates",
    "Scholarships",
    "Hostel",
    "FAQs",
]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are an official College Admission Assistant.
You help prospective students by answering questions about the following topics:
{chr(10).join(f"  - {t}" for t in TOPIC_LABELS)}

You answer questions using ONLY the official college documents provided in the \
CONTEXT section.

Rules you must follow without exception:
1. Answer ONLY using information explicitly present in the CONTEXT.
   Do not use any general knowledge, assumptions, or outside information.
2. If the CONTEXT does not contain enough information to fully answer the question,
   respond with exactly this sentence and nothing else:
   "{NOT_FOUND_MESSAGE}"
3. When you cite a fact, include its source at the end of the relevant sentence,
   for example: (Source: admission_brochure.pdf, Page 5)
4. Never guess, estimate, invent, or speculate about any information.
5. If multiple chunks provide complementary information, synthesise them into
   a single coherent answer and cite all relevant sources.
6. Be concise, professional, and factual. Do not add filler phrases like
   "Great question!" or "I hope this helps."
7. If the question is outside the nine topics listed above, politely say you
   can only assist with college admission queries."""


# ---------------------------------------------------------------------------
# Eligibility-specific prompt and question formatter
# ---------------------------------------------------------------------------

# Fixed disclaimer appended to every eligibility response.
ELIGIBILITY_DISCLAIMER = (
    "⚠ Important: Meeting the published eligibility criteria does not guarantee "
    "admission. Final selection is subject to seat availability, entrance exam "
    "scores, counselling process, and other criteria determined by the institution. "
    "Please refer to the official admission office for authoritative guidance."
)

ELIGIBILITY_SYSTEM_PROMPT = f"""You are an official College Admission Eligibility Advisor.

A student has provided their academic marks and a preferred course.
Your job is to compare their marks against the official eligibility criteria
found in the CONTEXT section below, and explain whether they appear to meet
the published requirements.

Rules you must follow without exception:
1. Base your analysis ONLY on the eligibility criteria explicitly stated in the CONTEXT.
   Do not use any general knowledge or assumptions.
2. For the preferred course, state clearly whether the student's marks meet
   each published criterion (percentage, subject-wise minimums, etc.).
3. If the CONTEXT mentions other courses the student may qualify for based on
   their marks, list those as well.
4. If the CONTEXT does not contain eligibility criteria for the requested course,
   say so explicitly — do not invent criteria.
5. Never guarantee admission. Never say the student "will be admitted".
6. Cite the source document and page for every criterion you reference,
   for example: (Source: admission_brochure.pdf, Page 7)
7. Use this exact structure in your response:
   - **Preferred Course Analysis:** [analysis for the requested course]
   - **Other Courses You May Qualify For:** [list based only on context, or "None found in documents"]
   - **Summary:** [one or two plain sentences]"""


def format_eligibility_question(
    percentage_12th: float,
    maths_marks: float,
    physics_marks: float,
    chemistry_marks: float,
    preferred_course: str,
) -> str:
    """
    Build the question string sent to the RAG pipeline for eligibility checks.

    The question is worded so that the similarity search retrieves chunks
    about eligibility criteria and minimum percentage requirements.
    """
    return (
        f"What are the eligibility criteria for {preferred_course}? "
        f"The student has the following academic profile:\n"
        f"  - Overall 12th percentage: {percentage_12th:.1f}%\n"
        f"  - Mathematics: {maths_marks:.1f}%\n"
        f"  - Physics: {physics_marks:.1f}%\n"
        f"  - Chemistry: {chemistry_marks:.1f}%\n"
        f"  - Preferred course: {preferred_course}\n\n"
        f"Based on the official eligibility criteria in the documents, "
        f"does this student meet the requirements for {preferred_course}? "
        f"Also mention any other courses they may qualify for."
    )


# ---------------------------------------------------------------------------
# Context block formatter
# ---------------------------------------------------------------------------

def format_context_block(docs: List[Document], max_chars_per_chunk: int = 1200) -> str:
    """
    Convert a list of retrieved Document chunks into a numbered CONTEXT block.

    Each entry is formatted as:

        [1] Source: fee_structure.pdf, Page: 3
        The annual tuition fee for B.Tech is ₹85,000 …

    Parameters
    ----------
    docs               : chunks returned by the vector store similarity search
    max_chars_per_chunk: hard cap on each chunk's text to stay within token
                         limits.  Longer text is truncated with "…".

    Returns
    -------
    A single string ready to be inserted into the prompt as the CONTEXT block.
    If docs is empty, returns a message saying no documents were found.
    """
    if not docs:
        return "No relevant documents were retrieved for this question."

    entries = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown document")
        page   = doc.metadata.get("page", "?")
        text   = doc.page_content.strip()

        # Truncate to stay within the model's context window.
        if len(text) > max_chars_per_chunk:
            text = text[:max_chars_per_chunk] + "…"

        entries.append(f"[{i}] Source: {source}, Page: {page}\n{text}")

    return "\n\n".join(entries)
