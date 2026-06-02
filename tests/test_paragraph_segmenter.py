"""Unit tests for paragraph segmentation and reference helpers."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from utils.paragraph_segmenter import (
    compute_t,
    make_ref,
    make_segment_id,
    sanitize_doc_id,
    segment_page,
    split_paragraphs,
)


class TestParagraphSegmenter(unittest.TestCase):

    def test_split_paragraphs_blank_lines(self):
        text = "First paragraph here with enough chars.\n\nSecond paragraph also long enough."
        paras = split_paragraphs(text)
        self.assertEqual(len(paras), 2)
        self.assertIn("First paragraph", paras[0])

    def test_split_paragraphs_min_length_filters_short(self):
        text = "Hi\n\nThis is a long enough paragraph for the test."
        paras = split_paragraphs(text, min_chars=20)
        self.assertEqual(len(paras), 1)
        self.assertIn("long enough", paras[0])

    def test_split_paragraphs_fallback_whole_page(self):
        text = "Single block of text without blank lines but still long enough."
        paras = split_paragraphs(text)
        self.assertEqual(len(paras), 1)
        self.assertEqual(paras[0], text)

    def test_compute_t_convention(self):
        self.assertEqual(compute_t(40, 0, 4), 40.0)
        self.assertEqual(compute_t(40, 2, 4), 40.5)

    def test_make_ref_and_segment_id(self):
        self.assertEqual(make_ref("hobbit", 40, 2), "hobbit:40:3")
        self.assertEqual(make_segment_id("hobbit", 40, 2), "segment:hobbit:40:3")

    def test_sanitize_doc_id(self):
        self.assertEqual(sanitize_doc_id("The-Hobbit.Tolkien"), "the_hobbit_tolkien")

    def test_segment_page_returns_ordered_segments(self):
        page = "Alpha paragraph one with sufficient length.\n\nBeta paragraph two also long enough."
        segments = segment_page(page, "hobbit", 5)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["ref"], "hobbit:5:1")
        self.assertEqual(segments[1]["ref"], "hobbit:5:2")
        self.assertLess(segments[0]["t"], segments[1]["t"])


if __name__ == "__main__":
    unittest.main()
