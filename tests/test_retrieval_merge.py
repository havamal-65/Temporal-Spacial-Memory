"""Unit tests for retrieval merge / diversity helpers."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.retrieval_merge import (
    expansion_queries,
    filter_to_region,
    inject_theme_coverage,
    merge_result_lists,
    query_suggests_enumeration,
    region_t_range,
    spread_by_time,
    themes_for_query,
)


class _FakeNode:
    def __init__(self, nid: str, t: float, text: str = ""):
        self.id = nid
        self.coordinates = type("C", (), {"t": t})()
        self.content = {"text": text}


class TestRetrievalMerge(unittest.TestCase):

    def test_enumeration_detection(self):
        self.assertTrue(query_suggests_enumeration("What does the party meet and avoid?"))
        self.assertFalse(query_suggests_enumeration("Who is Gandalf?"))

    def test_region_hint_mountains(self):
        self.assertEqual(region_t_range("traveling through the mountains"), (55.0, 110.0))

    def test_jewel_question_prefers_erebor_over_misty_mountains(self):
        q = (
            "What was the prized jewel that the dwarves were seeking, "
            "which mountain was it in and what was it being guarded by?"
        )
        rng = region_t_range(q)
        self.assertIn(rng, ((200.0, 305.0), (220.0, 305.0)))

    def test_expansion_queries_for_enumeration(self):
        extras = expansion_queries("What dangers in the mountains?")
        self.assertGreaterEqual(len(extras), 2)
        self.assertTrue(any("goblins" in q for q in extras))

    def test_expansion_queries_region_specific(self):
        extras = expansion_queries(
            "What dangers in the mountains?",
            region=(55.0, 95.0),
        )
        self.assertTrue(any("giants" in q for q in extras))
        self.assertFalse(any("wolves" in q for q in extras))

    def test_filter_to_region(self):
        nodes = [_FakeNode(f"n{i}", float(i * 10)) for i in range(10)]
        results = [(n, 1.0 - i * 0.05) for i, n in enumerate(nodes)]
        filtered = filter_to_region(results, 55.0, 95.0, k=4)
        for n, _ in filtered:
            self.assertGreaterEqual(n.coordinates.t, 55.0)
            self.assertLessEqual(n.coordinates.t, 95.0)

    def test_merge_dedupes_by_id(self):
        n1 = _FakeNode("a", 1.0)
        n2 = _FakeNode("b", 2.0)
        merged = merge_result_lists([(n1, 0.5), (n1, 0.9), (n2, 0.7)], k=5)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0][0].id, "a")
        self.assertEqual(merged[0][1], 0.9)

    def test_themes_for_beorn_query(self):
        themes = themes_for_query("Who is Beorn and what is a skin-changer?")
        labels = [t[0] for t in themes]
        self.assertIn("skin_changer", labels)
        goblin = _FakeNode("g", 70.0, "goblin-town tunnels")
        storm = _FakeNode("s", 68.0, "stone giants and thunder storm")
        base = [(_FakeNode("a", 56.0, "mountain paths"), 0.9)]
        out = inject_theme_coverage(
            base,
            [goblin, storm],
            lambda n: n.content["text"],
            themes=[("goblins", ("goblin",)), ("storm", ("thunder",))],
        )
        blob = " ".join(n.content["text"] for n, _ in out)
        self.assertIn("goblin", blob)
        self.assertIn("thunder", blob)
        nodes = [_FakeNode(f"n{i}", float(i * 5)) for i in range(10)]
        results = [(n, 1.0 - i * 0.05) for i, n in enumerate(nodes)]
        spread = spread_by_time(results, k=4, min_t_gap=4.0)
        ts = [n.coordinates.t for n, _ in spread]
        self.assertEqual(len(spread), 4)
        for i in range(len(ts) - 1):
            self.assertGreaterEqual(ts[i + 1] - ts[i], 4.0)


if __name__ == "__main__":
    unittest.main()
