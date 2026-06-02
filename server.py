"""
FastAPI Server for Narrative Atlas RAG Queries.

This server exposes grounded Q&A over a Narrative Atlas via an API endpoint.
"""

import os
import sys
import logging
from typing import List, Optional

from fastapi import FastAPI
from langserve import add_routes
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from src.models.narrative_atlas import NarrativeAtlas
    from src.utils.embedding_service import create_embedding_service
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
    from models.narrative_atlas import NarrativeAtlas
    from utils.embedding_service import create_embedding_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NarrativeAtlasAPI")

NARRATIVE_ATLAS_STORAGE_PATH = os.getenv("ATLAS_STORAGE_PATH", "output/hobbit_local_full")

logger.info(f"Initializing NarrativeAtlas from: {NARRATIVE_ATLAS_STORAGE_PATH}")
try:
    if not os.path.exists(NARRATIVE_ATLAS_STORAGE_PATH):
        logger.warning(f"Storage path {NARRATIVE_ATLAS_STORAGE_PATH} not found.")

    embedding_service = create_embedding_service("langchain")
    atlas = NarrativeAtlas(storage_path=NARRATIVE_ATLAS_STORAGE_PATH, embedding_service=embedding_service)
    logger.info("NarrativeAtlas loaded successfully.")

    if atlas.vector_store and hasattr(atlas.vector_store.index, "ntotal"):
        logger.info(f"FAISS index contains {atlas.vector_store.index.ntotal} vectors.")
    logger.info(f"Loaded {len(atlas.db.nodes)} nodes.")
except Exception as e:
    logger.error(f"Failed to initialize NarrativeAtlas: {e}", exc_info=True)
    sys.exit(1)

app = FastAPI(
    title="Narrative Atlas RAG API",
    version="1.1",
    description="API for grounded Q&A over the Narrative Atlas with citations.",
)


class QueryInput(BaseModel):
    query: str
    k: int = 5
    max_context_tokens: int = 1500


class RagOutput(BaseModel):
    result: str
    citations: Optional[List[str]] = None
    context_chars: Optional[int] = None
    context_tokens: Optional[int] = None


async def get_rag_answer(input_data: QueryInput) -> RagOutput:
    """Retrieve passages and generate a grounded answer."""
    logger.info(f"Received query: '{input_data.query}', k={input_data.k}")
    try:
        out = atlas.answer_query(
            user_query=input_data.query,
            k=input_data.k,
            max_context_tokens=input_data.max_context_tokens,
        )
        return RagOutput(
            result=out.get("answer", ""),
            citations=out.get("citations"),
            context_chars=out.get("context_chars"),
            context_tokens=out.get("context_tokens"),
        )
    except Exception as e:
        logger.error(f"Error during RAG processing: {e}", exc_info=True)
        return RagOutput(result=f"Error processing query: {e}")


add_routes(
    app,
    get_rag_answer,
    path="/narrative-rag",
    input_type=QueryInput,
    output_type=RagOutput,
    config_keys=["k"],
)


@app.get("/health")
async def health():
    index_size = -1
    if atlas and atlas.vector_store and hasattr(atlas.vector_store.index, "ntotal"):
        index_size = atlas.vector_store.index.ntotal
    return {
        "status": "ok",
        "atlas_status": "loaded" if atlas else "not loaded",
        "index_size": index_size,
        "node_count": len(atlas.db.nodes) if atlas else 0,
    }


if __name__ == "__main__":
    logger.info("Starting Narrative Atlas API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
