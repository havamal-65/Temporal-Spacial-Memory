"""Basic RAG demo that ingests *The Hobbit* PDF into NarrativeAtlas and answers a query.

Usage:
    python examples/rag_hobbit_demo.py <path_to_hobbit_pdf>

Dependencies:
    pip install pypdf tqdm
"""

import sys
from pathlib import Path
from typing import List

from tqdm import tqdm
from pypdf import PdfReader

from src.models.narrative_atlas import NarrativeAtlas


def extract_pdf_pages(pdf_path: Path) -> List[str]:
    reader = PdfReader(str(pdf_path))
    pages_text: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text.strip())
    return pages_text


def main():
    if len(sys.argv) != 2:
        print("Usage: python examples/rag_hobbit_demo.py <hobbit.pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1]).expanduser()
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        sys.exit(1)

    print("Reading PDF …")
    pages = extract_pdf_pages(pdf_path)

    atlas = NarrativeAtlas(storage_path="./hobbit_atlas", embed_dim=128)

    print("Adding pages to Atlas (as events) …")
    for idx, page_text in tqdm(list(enumerate(pages))):
        if not page_text:
            continue
        # Use first sentence as short description
        first_sentence = page_text.split(".")[0][:80]
        description = f"Hobbit Page {idx+1}: {first_sentence}…"
        atlas._create_event(description, impact=1.0, participant_ids=[])

    print(f"Atlas now contains {len(atlas.nodes)} nodes.")

    # Persist to disk
    atlas.save()

    # Example query
    query = "Where does Bilbo live at the beginning of the story?"
    print("\n=== RAG Demo Query ===")
    print("Q:", query)
    prompt = atlas.answer_query_with_context(query, k=5)
    print("\nConstructed prompt to send to LLM:\n")
    print(prompt)
    print("\nYou can now feed this prompt to your LLM of choice (e.g., OpenAI chat completion).")


if __name__ == "__main__":
    main() 