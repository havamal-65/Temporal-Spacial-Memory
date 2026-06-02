"""
Paragraph segmentation and addressable reference helpers.

Splits page text into paragraph units for ingest as ``segment`` nodes with
stable verse-style references (``doc_id:page:para``).

Temporal convention (shared with entity nodes):
  t = page_num + (para_idx / max(1, total_paras_on_page))
  page_num is 1-indexed PDF page; display page = int(t).
"""

import re
from typing import Any, Dict, List


def sanitize_doc_id(stem: str) -> str:
    """Turn a PDF filename stem into a stable doc_id token."""
    token = re.sub(r"[^a-zA-Z0-9]+", "_", stem.lower()).strip("_")
    return token or "doc"


def compute_t(page_num: int, para_idx: int, total_paras: int) -> float:
    """Compute temporal coordinate for a paragraph on a page."""
    return float(page_num) + (float(para_idx) / float(max(1, total_paras)))


def make_ref(doc_id: str, page_num: int, para_idx: int) -> str:
    """Human-readable reference string, e.g. hobbit:40:3 (1-based para index)."""
    return f"{doc_id}:{page_num}:{para_idx + 1}"


def make_segment_id(doc_id: str, page_num: int, para_idx: int) -> str:
    """Node id for a segment (para_idx 0-based in id for consistency with ref para+1)."""
    return f"segment:{doc_id}:{page_num}:{para_idx + 1}"


def split_paragraphs(page_text: str, min_chars: int = 20) -> List[str]:
    """Split page text into paragraphs; fall back to whole page if no breaks."""
    if not page_text or not page_text.strip():
        return []
    raw = re.split(r"\n\s*\n", page_text.strip())
    paras = [p.strip() for p in raw if p.strip() and len(p.strip()) >= min_chars]
    if not paras:
        stripped = page_text.strip()
        if stripped:
            return [stripped]
    return paras


def segment_page(page_text: str, doc_id: str, page_num: int) -> List[Dict[str, Any]]:
    """Return segment dicts ready for atlas.add_node."""
    paragraphs = split_paragraphs(page_text)
    if not paragraphs:
        return []
    total = len(paragraphs)
    segments: List[Dict[str, Any]] = []
    for para_idx, text in enumerate(paragraphs):
        ref = make_ref(doc_id, page_num, para_idx)
        t = compute_t(page_num, para_idx, total)
        segments.append({
            "id": make_segment_id(doc_id, page_num, para_idx),
            "text": text,
            "ref": ref,
            "doc_id": doc_id,
            "page": page_num,
            "para_idx": para_idx,
            "total_paras": total,
            "t": t,
        })
    return segments
