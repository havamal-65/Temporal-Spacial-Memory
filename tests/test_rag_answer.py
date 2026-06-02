"""Unit tests for grounded RAG answer generation (mock LLM, no network)."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.rag_answer import ANSWER_PROMPT, RagAnswerer


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class TestRagAnswerer(unittest.TestCase):

    def test_empty_context_returns_insufficient_message(self):
        answerer = RagAnswerer(atlas=MagicMock())
        out = answerer.generate_answer("Who is Bilbo?", "")
        self.assertIn("could not find", out["answer"].lower())
        self.assertEqual(out["citations"], [])

    @patch("src.models.rag_answer.llm_is_available", return_value=True)
    @patch("src.models.rag_answer.create_llm_service")
    def test_generate_answer_includes_context_in_prompt(self, mock_create, _mock_avail):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _FakeResponse(
            "Bilbo is a hobbit. [hobbit:10:1]"
        )
        mock_create.return_value = mock_llm

        answerer = RagAnswerer(atlas=MagicMock())
        context = "[hobbit:10:1 page 10 (t=10.00)]\nIn a hole in the ground there lived a hobbit."
        out = answerer.generate_answer("Who is Bilbo?", context)

        mock_llm.invoke.assert_called_once()
        prompt = mock_llm.invoke.call_args[0][0]
        self.assertIn("ONLY the passages below", prompt)
        self.assertIn("Cite sources inline", prompt)
        self.assertIn(context, prompt)
        self.assertIn("Bilbo is a hobbit", out["answer"])
        self.assertIn("hobbit:10:1", out["citations"])

    def test_extract_citations_dedupes(self):
        text = "See [hobbit:40:3] and again hobbit:40:3 plus hobbit:41:1"
        refs = RagAnswerer._extract_citations(text)
        self.assertEqual(refs, ["hobbit:40:3", "hobbit:41:1"])

    def test_answer_prompt_template_has_placeholders(self):
        filled = ANSWER_PROMPT.format(question="Q?", context="CTX")
        self.assertIn("Q?", filled)
        self.assertIn("CTX", filled)


if __name__ == "__main__":
    unittest.main()
