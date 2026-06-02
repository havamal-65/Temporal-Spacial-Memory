"""Tests for token budget and passage deduplication."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from src.utils.token_budget import (
    count_tokens,
    dedupe_results_by_embedding,
    dedupe_results_by_text,
    normalize_for_dedupe,
    trim_text_to_tokens,
)


class _FakeNode:
    def __init__(self, nid: str, t: float, text: str, embedding=None):
        self.id = nid
        self.coordinates = type("C", (), {"t": t})()
        self.content = {"text": text}
        self.embedding = embedding


class TestTokenBudget(unittest.TestCase):

    def test_count_tokens_nonempty(self):
        self.assertGreater(count_tokens("hello world"), 0)

    def test_normalize_for_dedupe(self):
        self.assertEqual(
            normalize_for_dedupe("  Hello\tWorld  "),
            "hello world",
        )

    def test_trim_text_to_tokens(self):
        long_text = "word " * 500
        trimmed = trim_text_to_tokens(long_text, max_tokens=20)
        self.assertLessEqual(count_tokens(trimmed), 25)

    def test_dedupe_exact_duplicates(self):
        n = _FakeNode("a", 1.0, "goblin tunnels in the mountain")
        results = [(n, 0.9), (_FakeNode("b", 2.0, "goblin tunnels in the mountain"), 0.5)]
        out = dedupe_results_by_text(results, lambda x: x.content["text"])
        self.assertEqual(len(out), 1)

    def test_dedupe_subsumed_passage(self):
        short = _FakeNode("a", 1.0, "goblin tunnels in the mountain pass " * 5)
        long = _FakeNode("b", 2.0, short.content["text"] + " with extra detail about the cave")
        out = dedupe_results_by_text(
            [(short, 0.6), (long, 0.9)],
            lambda x: x.content["text"],
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0][0].id, "b")

    def test_dedupe_embedding_near_duplicates(self):
        base = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        near = np.array([0.99, 0.01, 0.0, 0.0], dtype=np.float32)
        n1 = _FakeNode("a", 1.0, "the dragon guarded the treasure hoard", base)
        n2 = _FakeNode("b", 2.0, "smaug sat upon piles of gold and gems", near)
        out = dedupe_results_by_embedding([(n1, 0.7), (n2, 0.9)], threshold=0.92)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0][0].id, "b")


if __name__ == "__main__":
    unittest.main()
