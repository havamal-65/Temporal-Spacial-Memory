"""
Grounded RAG answer generation for the Narrative Atlas.

Uses the configured LLM provider (local Ollama by default) to produce answers
strictly from retrieved, t-ordered context with inline citations.
"""

import re
import logging
from typing import Any, Dict, List, Optional

from src.utils.llm_factory import create_llm_service, llm_is_available

logger = logging.getLogger("RagAnswerer")

ANSWER_PROMPT = """You are a careful narrative assistant. Answer the user's question using ONLY the passages below.

Rules:
- Base your answer strictly on the provided passages; do not invent facts.
- Cite sources inline using the reference tags shown (e.g. [hobbit:40:3]).
- If the passages support several valid answers (different dangers, characters, or events), list each one that is supported — do not stop at only the first.
- For questions asking what the party met or avoided on a journey, give a bullet list of every distinct danger supported by the passages.
- If the passages do not contain enough information, say so clearly.
- Keep the answer concise and in narrative order when describing sequences.

Question: {question}

Passages (in narrative order):
{context}

Answer:"""


class RagAnswerer:
    """Generate grounded answers from assembled context."""

    def __init__(self, atlas: Any):
        self.atlas = atlas
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            if not llm_is_available():
                raise RuntimeError("LLM provider not available for answer generation.")
            self._llm = create_llm_service(temperature=0)
        return self._llm

    def generate_answer(self, question: str, context: str) -> Dict[str, Any]:
        """Return answer text and extracted citation refs from the model output."""
        if not context.strip():
            return {
                "answer": "I could not find relevant passages to answer that question.",
                "citations": [],
                "context_chars": 0,
            }

        prompt = ANSWER_PROMPT.format(question=question, context=context)
        try:
            response = self.llm.invoke(prompt)
            answer_text = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.warning("LLM answer generation failed: %s", e)
            return {
                "answer": (
                    "Could not generate an answer (LLM unavailable). "
                    "Retrieved context is included below.\n\n" + context
                ),
                "citations": self._extract_citations(context),
                "context_chars": len(context),
                "error": str(e),
            }

        citations = self._extract_citations(answer_text + "\n" + context)
        return {
            "answer": answer_text.strip(),
            "citations": citations,
            "context_chars": len(context),
        }

    @staticmethod
    def _extract_citations(text: str) -> List[str]:
        """Pull doc:page:para refs from text."""
        found = re.findall(r"\b([a-zA-Z0-9_]+:\d+:\d+)\b", text)
        return list(dict.fromkeys(found))
