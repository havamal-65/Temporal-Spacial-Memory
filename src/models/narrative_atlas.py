import os
import json
import faiss
import numpy as np
import shutil
import pickle
from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING, Set
from dataclasses import dataclass, field, asdict
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from src.models.spatial_temporal_db import SpatialTemporalDB
from src.utils.embedding_service import EmbeddingService
from src.data_models import PolarTemporalCoordinate
import time
import hashlib
import logging
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
import math
from src.nl_parser import CoordinateFilters, NlQueryParser, ParsedQuery
from src.utils.sector_legend import get_sector_legend
from src.utils.semantic_compass import SemanticCompassMapper

# --- Add Logger Setup ---
logger = logging.getLogger('NarrativeAtlas') # Create logger instance
# --- End Logger Setup ---

# Maps SectorLegend category strings to 8-point compass sector names.
# Keyed by the lowercase string returned in recommendation["category"].
CATEGORY_TO_SECTOR: Dict[str, str] = {
    "action_adventure":        "N",
    "technical_instructional": "NE",
    "scientific_analytical":   "E",
    "educational_reference":   "SE",
    "creative_artistic":       "S",
    "personal_lifestyle":      "SW",
    "historical_reflective":   "W",
    "philosophical_abstract":  "NW",
}


def _sectors_to_theta_range(sectors: List[str]) -> Optional[Tuple[float, float]]:
    """Convert a list of 8-point sector names to a (theta_min, theta_max) range.

    Uses the first valid sector only (highest-confidence). The existing
    _is_coordinate_match filter supports a single contiguous range.
    Returns None when no valid sector name is found.
    """
    HALF = math.pi / 8  # 8 sectors × (π/4 each) → half-width is π/8
    angles = SemanticCompassMapper.SECTOR_ANGLES
    for sector in sectors:
        if sector not in angles:
            continue
        center = angles[sector]
        if center == 0.0:  # N straddles 0/2π — produce wrap-around signal
            return (2 * math.pi - HALF, HALF)
        return (center - HALF, center + HALF)
    return None


def _sectors_to_theta_ranges(sectors: List[str]) -> List[Tuple[float, float]]:
    """Return one (theta_min, theta_max) range per valid sector name.

    Unlike _sectors_to_theta_range (singular), all valid sectors in the list
    are converted, enabling multi-sector OR queries.  Wrap-around sectors
    (N, whose center is 0.0) produce theta_min > theta_max as the signal.
    Invalid sector names are silently skipped.  Empty list → empty list.
    """
    HALF = math.pi / 8
    angles = SemanticCompassMapper.SECTOR_ANGLES
    ranges: List[Tuple[float, float]] = []
    for sector in sectors:
        if sector not in angles:
            continue
        center = angles[sector]
        if center == 0.0:
            ranges.append((2 * math.pi - HALF, HALF))
        else:
            ranges.append((center - HALF, center + HALF))
    return ranges


def _derive_sectors_from_query(
    query: str, confidence_threshold: float = 0.3
) -> List[str]:
    """Translate a natural-language query to 8-point sector names via SectorLegend.

    No LLM required — pure keyword/pattern matching.
    confidence_threshold: pattern matches score 0.7-0.95; keyword scoring is
    min(count*0.1, 1.0), so 0.3 requires 3+ keywords or 1 phrase match.
    """
    result = get_sector_legend().translate_query(query)
    sectors: List[str] = []
    for rec in result.get("recommendations", []):
        if rec.get("confidence", 0.0) < confidence_threshold:
            continue
        sector = CATEGORY_TO_SECTOR.get(rec.get("category", ""))
        if sector and sector not in sectors:
            sectors.append(sector)
    return sectors


if TYPE_CHECKING:
    # Correct the import path for type checking
    from src.utils.embedding_service import EmbeddingService
    from src.utils.coordinate_mapper import CoordinateMapper

@dataclass
class Node:
    id: str
    type: str
    content: dict
    coordinates: PolarTemporalCoordinate
    embedding: Optional[np.ndarray]
    keywords: Optional[List[str]]
    metadata: dict
    parent_node_id: Optional[str]
    timestamp: float
    mapping_details: dict

class NarrativeAtlas:
    def __init__(self, storage_path: str, embedding_service: EmbeddingService):
        self.storage_path = storage_path
        self.db = SpatialTemporalDB(db_path=os.path.join(storage_path, "nodes.sqlite"))
        self.embedding_service = embedding_service
        from src.utils.coordinate_mapper import CoordinateMapper
        
        # Initialize coordinate mapper with embedding-based coordinate options
        use_embedding_coords = os.getenv('USE_EMBEDDING_COORDS', 'True').lower() in ('true', '1', 'yes')
        embedding_r_scale = float(os.getenv('EMBEDDING_R_SCALE', '1.0'))
        embedding_theta_scale = float(os.getenv('EMBEDDING_THETA_SCALE', '3.14159'))
        
        self.coordinate_mapper = CoordinateMapper(
            embedding_service=self.embedding_service,
            base_radius=float(os.getenv('BASE_RADIUS', '0.9')),
            # Enable embedding-based coordinate transformation
            use_embedding_for_coords=use_embedding_coords,
            embedding_r_scale=embedding_r_scale,
            embedding_theta_scale=embedding_theta_scale
        )
        
        logger.info(f"Initialized NarrativeAtlas with embedding-based coordinates: {use_embedding_coords}")
        logger.info(f"Coordinate scaling factors - r: {embedding_r_scale}, theta: {embedding_theta_scale}")
        
        try:
            self.embedding_dim = self.embedding_service.embedding_dim
        except AttributeError:
             logger.error(f"Embedding service {type(self.embedding_service)} lacks 'embedding_dim' attribute.")
             raise ValueError("Cannot determine embedding dimension from service.")
        
        # Langchain FAISS wrapper (initialized during load or _initialize_vector_store)
        self.vector_store: Optional[FAISS] = None
        # Raw FAISS index (Not directly used anymore, managed by Langchain FAISS)
        # self.raw_faiss_index: Optional[faiss.Index] = None # REMOVED
        
        # Mappings for direct FAISS interaction (loaded from file)
        self.node_id_to_faiss_id: Dict[str, int] = {}
        self.faiss_id_to_node_id: Dict[int, str] = {}
        self.next_faiss_id: int = 0 # Counter for next available FAISS integer ID (loaded or reset)

        # NL parser is initialised lazily — only when search_with_nl_query() is called,
        # so the atlas can be used without OPENAI_API_KEY for embedding-only workloads.
        self._nl_parser: Optional[NlQueryParser] = None
        
        # Attempt to load existing data first
        if not self.load(): # If loading fails or path doesn't exist
            self._initialize_vector_store() # Create a new empty store
        # DO NOT CALL load() here again

    @property
    def nl_parser(self) -> NlQueryParser:
        if self._nl_parser is None:
            self._nl_parser = NlQueryParser()
        return self._nl_parser

    def _initialize_vector_store(self):
        """Initializes a NEW, EMPTY vector store in memory.""" # Changed docstring
        if self.embedding_service is None:
            raise ValueError("Cannot initialize vector store without an embedding service.")
            
        # Dimension already checked in __init__
        dimension = self.embedding_dim
        logger.info(f"Initializing NEW EMPTY in-memory FAISS index with dimension: {dimension}")
        
        try:
            import faiss 
            # Use IndexFlatL2 for simplicity, can be changed later
            index = faiss.IndexFlatL2(dimension)
            
            # Create the FAISS wrapper with the service and an empty index/docstore
            self.vector_store = FAISS( 
                 embedding_function=self.embedding_service, 
                 index=index, 
                 docstore=InMemoryDocstore({}), # Start with empty docstore
                 index_to_docstore_id={}  # Start with empty mapping
            )
            # Reset ID mappings for the new index
            self.node_id_to_faiss_id = {}
            self.faiss_id_to_node_id = {}
            self.next_faiss_id = 0
            logger.info("New empty in-memory FAISS index initialized successfully.")
        except ImportError:
            logger.error("FAISS library not installed. Please install it (`pip install faiss-cpu` or `pip install faiss-gpu`).")
            raise
        except Exception as e:
            logger.error(f"Error initializing new FAISS vector store: {e}", exc_info=True)
            raise

    def _get_or_create_character(self, name: str, temporal_coordinate: float) -> str:
        """Get or create a character node (stores in DB only)."""
        node_id = f"character_{name.lower().replace(' ', '_')}"
        if node_id not in self.db.nodes:
            node = Node(
                id=node_id,
                type="character",
                content={"name": name},
                coordinates={"t": temporal_coordinate, "r": 0.0, "theta": 0.0},
                embedding=np.zeros(self.embedding_dim, dtype=np.float32),
                keywords=None,
                metadata={"node_type": "character"},
                parent_node_id=None,
                timestamp=time.time(),
                mapping_details={}
            )
            self.db.add_node(node)
            # No call to _add_or_update_embedding here
        return node_id

    def _create_event(self, description: str, temporal_coordinate: float, participant_names: List[str]) -> str:
        """Create an event node (stores in DB only)."""
        node_id = f"event_{description.lower().replace(' ', '_')[:50]}"
        original_node_id = node_id
        counter = 1
        while node_id in self.db.nodes:
            node_id = f"{original_node_id}_{counter}"
            counter += 1

        node = Node(
            id=node_id,
            type="event",
            content={"description": description, "participant_names": participant_names},
            coordinates={"t": temporal_coordinate, "r": 0.0, "theta": 0.0},
            embedding=np.zeros(self.embedding_dim, dtype=np.float32),
            keywords=None,
            metadata={"node_type": "event"},
            parent_node_id=None,
            timestamp=time.time(),
            mapping_details={}
        )
        self.db.add_node(node)
        # No call to _add_or_update_embedding here
        return node_id

    def _get_or_create_location(self, name: str, temporal_coordinate: float) -> str:
        """Get or create a location node (stores in DB only)."""
        node_id = f"location_{name.lower().replace(' ', '_')}"
        if node_id not in self.db.nodes:
            node = Node(
                id=node_id,
                type="location",
                content={"name": name},
                coordinates={"t": temporal_coordinate, "r": 0.0, "theta": 0.0},
                embedding=np.zeros(self.embedding_dim, dtype=np.float32),
                keywords=None,
                metadata={"node_type": "location"},
                parent_node_id=None,
                timestamp=time.time(),
                mapping_details={}
            )
            self.db.add_node(node)
            # No call to _add_or_update_embedding here
        return node_id

    def _add_or_update_embedding(self,
                               node: Node,
                               text_to_embed: Optional[str] = None,
                               precomputed_embedding: Optional[np.ndarray] = None):
        """
        Adds or updates the node's embedding in the FAISS vector store and the node object itself.
        Handles both precomputed embeddings and generating them from text.
        Uses the Langchain FAISS wrapper's add_texts method.
        """
        if self.vector_store is None:
            logger.error("FAISS vector store not initialized. Cannot add embedding.")
            return

        embedding_to_use = None
        if precomputed_embedding is not None:
            embedding_to_use = precomputed_embedding
        elif text_to_embed:
            try:
                # Use the standard embed_query method
                embedding_list = self.embedding_service.embed_query(text_to_embed) 
                if embedding_list:
                    embedding_to_use = np.array(embedding_list, dtype=np.float32)
            except Exception as e:
                logger.error(f"Error getting embedding for node {node.id}: {e}", exc_info=True)
                return
        
        if embedding_to_use is None:
            logger.warning(f"No embedding available for node {node.id}. Cannot add to FAISS.")
            return
            
        if embedding_to_use.shape[0] != self.embedding_dim:
             logger.error(f"Embedding dimension mismatch for node {node.id}. Expected {self.embedding_dim}, got {embedding_to_use.shape[0]}. Skipping add.")
             return

        # Update the node object with the embedding
        node.embedding = embedding_to_use

        # --- Add/Update using Langchain FAISS wrapper --- 
        # Prepare metadata including coordinates
        doc_metadata = node.metadata.copy() if node.metadata else {}
        doc_metadata["coord_r"] = node.coordinates.r
        doc_metadata["coord_theta"] = node.coordinates.theta
        doc_metadata["coord_t"] = node.coordinates.t
        doc_metadata["coord_z"] = node.coordinates.z
        doc_metadata["coord_z_type"] = node.coordinates.z_type
        doc_metadata["node_type"] = node.type
        doc_metadata["timestamp"] = node.timestamp
        doc_metadata["keywords"] = ",".join(node.keywords) if node.keywords else ""
        doc_metadata["mapping_details"] = json.dumps(node.mapping_details)
        if node.parent_node_id:
             doc_metadata["parent_node_id"] = node.parent_node_id
        doc_metadata["node_id"] = node.id # Crucial: Ensure node_id is in metadata
        
        # Determine page_content for the Document
        page_content = node.content.get('text', json.dumps(node.content))

        # Use add_texts with the node_id as the ID
        # Langchain's FAISS handles mapping this ID internally.
        # Note: FAISS typically doesn't support efficient updates. 
        # Calling add_texts for an existing ID might lead to duplicates 
        # depending on the underlying index type and Langchain version.
        # A true update might require delete + add.
        # For now, we assume add_texts handles this reasonably or we accept potential duplicates.
        try:
            # FAISS.add_texts expects list of texts and list of metadatas
            added_ids = self.vector_store.add_texts(
                 texts=[page_content], 
                 metadatas=[doc_metadata], 
                 ids=[node.id] # Provide the node_id directly
            )
            # Optionally update our internal ID maps if needed, though Langchain manages its own.
            # The `ids` parameter *should* make Langchain use our node.id internally.
            # Let's verify if the internal index_to_docstore_id map looks correct after adding.
            # logger.debug(f"Added/updated node {node.id} in FAISS. Langchain IDs returned: {added_ids}")
            # logger.debug(f"Current vector_store.index_to_docstore_id: {self.vector_store.index_to_docstore_id}")
        except Exception as e:
            logger.error(f"Error adding/updating node {node.id} in FAISS vector store: {e}", exc_info=True)
        # --- End Add/Update --- 

    def add_node(self,
                 node_id: str,
                 content: Dict[str, Any],
                 embedding: Optional[np.ndarray],
                 metadata: Dict,
                 coordinates: Optional[PolarTemporalCoordinate] = None,
                 keywords: Optional[List[str]] = None,
                 mapping_details: Optional[Dict] = None,
                 parent_node_id: Optional[str] = None,
                 explicit_timestamp: Optional[float] = None
                ) -> str:
        """
        Add a node to the narrative atlas with either provided coordinates or
        coordinates computed from the embedding and/or content.
        
        Args:
            node_id: Unique identifier for the node
            content: Dictionary containing node content (varies by node type)
            embedding: Pre-computed embedding vector (optional)
            metadata: Additional metadata for the node
            coordinates: Pre-computed coordinates (optional)
            keywords: Pre-extracted keywords (optional)
            mapping_details: Details about how coordinates were mapped (optional)
            parent_node_id: ID of parent node (optional)
            explicit_timestamp: Override timestamp (optional)
            
        Returns:
            The node ID (may be generated if not provided)
        """
        # If no node_id provided, generate one
        if not node_id:
            node_id = f"node_{int(time.time())}_{hashlib.md5(str(content).encode()).hexdigest()[:8]}"
            
        timestamp = explicit_timestamp if explicit_timestamp is not None else time.time()

        # Generate mapping if coordinates not provided
        if coordinates is None:
            text_content = content.get('text', str(content))
            
            # If no embedding is provided, generate one
            if embedding is None and text_content:
                try:
                    embedding_list = self.embedding_service.embed_query(text_content)
                    embedding = np.array(embedding_list)
                    logger.debug(f"Generated embedding for node {node_id}")
                except Exception as e:
                    logger.error(f"Failed to generate embedding for node {node_id}: {e}")
                    # Continue with None embedding
            
            # Map to coordinates using embedding and/or metadata
            mapping_result = self.coordinate_mapper.map_to_coordinates(
                content=text_content,
                metadata=metadata,
                embedding=embedding
            )
            
            coordinates = mapping_result['coordinate']
            keywords = mapping_result.get('keywords', keywords)
            mapping_details = mapping_result.get('mapping_details', mapping_details or {})
            logger.info(f"Mapped node {node_id} to coordinates: r={coordinates.r:.3f}, theta={coordinates.theta:.3f}, t={coordinates.t:.3f}, z={coordinates.z:.3f}, z_type={coordinates.z_type}")
        
        # Create a Node instance
        node = Node(
            id=node_id,
            type=metadata.get('node_type', 'content'),
            content=content,
            coordinates=coordinates,
            embedding=embedding,
            keywords=keywords,
            metadata=metadata,
            parent_node_id=parent_node_id,
            timestamp=timestamp,
            mapping_details=mapping_details or {}
        )
        
        # Store in the database
        self.db.add_node(node)

        # Add to FAISS if embedding is available
        if embedding is not None:
            self._add_or_update_embedding(node, text_to_embed=None, precomputed_embedding=embedding)
            
        return node_id

    def get_node(self, node_id: str) -> Optional["Node"]:
        """Return the Node with the given ID, or None if not found."""
        return self.db.nodes.get(node_id)

    def update_node(self, node: "Node") -> bool:
        """Persist in-place changes to a node back to SQLite and the docstore."""
        if node.id not in self.db.nodes:
            return False
        self.db.add_node(node)
        if self.vector_store is not None and hasattr(self.vector_store, "docstore"):
            page_content = node.content.get("text", "")
            self.vector_store.docstore.add({node.id: Document(page_content=page_content, metadata=node.metadata)})
        return True

    def remove_node(self, node_id: str) -> bool:
        """Alias for delete_node for API compatibility."""
        return self.delete_node(node_id)

    def dedup_nodes(self) -> int:
        """Remove duplicate nodes (same content JSON) from DB and in-memory cache.

        For each duplicate group the lexicographically smallest node id is kept.
        Returns the number of nodes removed.
        """
        removed = self.db.dedup_by_content()
        if removed:
            logger.info("dedup_nodes: removed %d duplicate nodes", removed)
        return removed

    def find_similar_nodes(self, query_text: str, k: int = 5) -> List[Tuple[Node, float]]:
        """Find nodes similar to the query text."""
        # Search the vector store
        docs = self.vector_store.similarity_search_with_score(query_text, k=k)
        
        # Convert results to nodes
        results = []
        for doc, score in docs:
            # Retrieve the node_id stored in the metadata
            node_id = doc.metadata.get("node_id") # Use .get() for safety
            
            # Retrieve the mapped node ID - This mapping might be redundant now?
            # Let's rely on the node_id directly from metadata first.
            # doc_id = self.doc_id_to_node_id.get(doc_id) # We don't have doc_id here easily
            
            if node_id and node_id in self.db.nodes:
                 results.append((self.db.nodes[node_id], score))
            elif node_id:
                 print(f"Warning: Found node_id {node_id} in FAISS metadata but not in DB.")
            else:
                 print(f"Warning: FAISS result metadata missing 'node_id': {doc.metadata}")
                 
        return results
    
    def save(self):
        """Save the atlas data (DB nodes, FAISS index + docstore)."""
        index_folder = os.path.join(self.storage_path)
        # id_maps_path = os.path.join(self.storage_path, "id_maps.json") # REMOVED - Managed by FAISS wrapper
        db_path = os.path.join(self.storage_path, "spatial_temporal_db.pkl")

        os.makedirs(index_folder, exist_ok=True)
        
        try:
            # Save FAISS index and docstore using Langchain's method
            if self.vector_store:
                self.vector_store.save_local(folder_path=index_folder, index_name="vector_index") # Changed index_name
                logger.info(f"FAISS index and docstore saved to {index_folder}")
            else:
                 logger.warning("Vector store not initialized, skipping FAISS save.")
            
            # REMOVED ID maps save - Langchain FAISS wrapper handles this internally in its index.pkl
            
            # SpatialTemporalDB writes to SQLite on every add_node() — no separate save needed.
            logger.info("SpatialTemporalDB nodes are persisted in SQLite (no separate save required)")
                
            logger.info(f"Narrative Atlas saved successfully to {self.storage_path}")

        except Exception as e:
            logger.error(f"Error saving Narrative Atlas: {e}", exc_info=True)
            # raise # Optional: re-raise if saving failure is critical

    def load(self) -> bool:
        """Load the atlas data (DB nodes, FAISS index + docstore). Returns True on success, False otherwise.""" 
        legacy_pkl_path = os.path.join(self.storage_path, "spatial_temporal_db.pkl")
        index_folder = os.path.join(self.storage_path)
        index_file = os.path.join(index_folder, "vector_index.faiss") # Match saved name
        pkl_file = os.path.join(index_folder, "vector_index.pkl") # Match saved name

        db_loaded = False
        index_loaded = False

        # 1. Migrate legacy pickle if it exists, then load from SQLite.
        if os.path.exists(legacy_pkl_path):
            logger.info(f"Migrating legacy pickle to SQLite: {legacy_pkl_path}")
            try:
                with open(legacy_pkl_path, "rb") as f:
                    legacy_nodes: dict = pickle.load(f)
                for node in legacy_nodes.values():
                    self.db.add_node(node)
                os.rename(legacy_pkl_path, legacy_pkl_path + ".migrated")
                logger.info(f"Migrated {len(legacy_nodes)} nodes from pickle to SQLite")
            except Exception as e:
                logger.error(f"Error migrating legacy pickle {legacy_pkl_path}: {e}", exc_info=True)

        # Load all persisted nodes from SQLite into memory.
        try:
            rows = self.db.load_all_to_memory()
            if rows:
                from src.data_models import PolarTemporalCoordinate as _PTC
                for row in rows:
                    coords = _PTC(
                        r=row["r"], theta=row["theta"],
                        t=row["t"], z=row["z"], z_type=row["z_type"],
                    )
                    node = Node(
                        id=row["id"],
                        type=row["type"],
                        content=row["content"],
                        coordinates=coords,
                        embedding=row["embedding"],
                        keywords=row["keywords"],
                        metadata=row["metadata"],
                        parent_node_id=row["parent_node_id"],
                        timestamp=row["timestamp"],
                        mapping_details=row["mapping_details"],
                    )
                    self.db.nodes[node.id] = node
                logger.info(f"Loaded {len(rows)} nodes from SQLite into memory")
                db_loaded = True
            else:
                logger.info("SQLite DB is empty — starting fresh")
        except Exception as e:
            logger.error(f"Error loading nodes from SQLite: {e}", exc_info=True)
            self.db.nodes = {}

        # 2. Load FAISS index and docstore using Langchain
        if os.path.exists(index_file) and os.path.exists(pkl_file):
            if self.embedding_service is None:
                 logger.error("Cannot load FAISS index without an embedding service.")
                 return False # Cannot proceed without embedding service
            try:
                # allow_dangerous_deserialization=True might be needed depending on Langchain/Pickle versions
                self.vector_store = FAISS.load_local(
                    folder_path=index_folder, 
                    embeddings=self.embedding_service, 
                    index_name="vector_index",
                    allow_dangerous_deserialization=True # Added for compatibility
                )
                
                # --- Dimension Validation --- 
                if self.vector_store.index is None:
                     logger.error("Loaded FAISS index is None.")
                     index_loaded = False
                elif not hasattr(self.vector_store.index, 'd'):
                     logger.error("Loaded FAISS index object does not have dimension attribute 'd'.")
                     index_loaded = False
                elif self.vector_store.index.d != self.embedding_dim:
                    logger.error(f"Dimension mismatch! Loaded FAISS index dimension ({self.vector_store.index.d}) does not match current embedding service dimension ({self.embedding_dim}).")
                    # Decide how to handle: raise error, re-initialize, etc.
                    # For now, treat as load failure
                    self.vector_store = None # Reset vector store
                    index_loaded = False
                else:
                    logger.info(f"FAISS index and docstore loaded successfully from {index_folder}. Dimension: {self.vector_store.index.d}")
                    index_loaded = True
                    # Restore ID mappings from the loaded docstore (if needed for other logic)
                    # Typically, Langchain methods use the docstore/index directly
                    # self.node_id_to_faiss_id = {v: k for k, v in self.vector_store.index_to_docstore_id.items()} # Rebuild if needed
                    # self.faiss_id_to_node_id = self.vector_store.index_to_docstore_id.copy()
                    # self.next_faiss_id = max(self.faiss_id_to_node_id.keys()) + 1 if self.faiss_id_to_node_id else 0

            except Exception as e:
                logger.error(f"Error loading FAISS index/docstore from {index_folder}: {e}", exc_info=True)
                self.vector_store = None # Ensure it's None on error
                index_loaded = False
        else:
             logger.warning(f"FAISS index files not found in {index_folder}. Vector store not loaded.")
             self.vector_store = None # Ensure it's None if files missing

        # Return True only if both DB and Index loaded successfully (or were intentionally empty)
        # If DB loaded but index failed, return False as atlas is inconsistent
        if db_loaded and index_loaded:
             return True
        elif not os.path.exists(legacy_pkl_path) and not os.path.exists(index_file):
             logger.info("Atlas storage path was empty. Initializing fresh atlas.")
             return False # Indicates fresh start needed
        else:
             logger.error("Atlas loaded partially or inconsistently. DB loaded: {db_loaded}, Index loaded: {index_loaded}")
             return False # Load was not fully successful

    def clear(self):
        """Clears the database, vector index, and mappings, and removes persisted files."""
        print(f"Clearing Narrative Atlas data in {self.storage_path}...")
        
        # 1. Clear in-memory data and SQLite store
        self.db.clear_all()
        self.node_id_to_faiss_id = {}
        self.faiss_id_to_node_id = {}
        
        # 2. Reset FAISS index to a new empty one
        print("Resetting FAISS index...")
        self._initialize_vector_store()
        self.next_faiss_id = 0 # Reset counter for new index
        
        # 3. Delete physical files/directory
        if os.path.exists(self.storage_path):
            try:
                # Attempt to remove the entire directory and recreate it
                shutil.rmtree(self.storage_path)
                os.makedirs(self.storage_path, exist_ok=True)
                print(f"Successfully cleared and recreated directory: {self.storage_path}")
            except OSError as e:
                print(f"Error removing directory {self.storage_path}: {e}. Manual cleanup might be required.")
        else:
             # Ensure directory exists if it didn't before
             os.makedirs(self.storage_path, exist_ok=True)
             
        print("Narrative Atlas cleared.")

    def delete_node(self, node_id: str) -> bool:
        """Remove a node from the database and its corresponding vector."""
        # 1. Remove from SQLite + in-memory cache
        if not self.db.delete_node(node_id):
            return False

        # 2. Remove from FAISS index
        if node_id in self.node_id_to_faiss_id:
            doc_id = self.node_id_to_faiss_id[node_id]
            try:
                # Deletion in Langchain FAISS might need the internal docstore ID.
                # This simplified version assumes `doc_id` works or deletion isn't critical.
                # A more robust approach might require interacting with `vector_store.docstore` 
                # and `vector_store.index_to_docstore_id`.
                deleted = self.vector_store.delete([doc_id]) 
                if not deleted:
                    print(f"Warning: Failed to delete vector for doc_id {doc_id} from FAISS store.")
            except Exception as e:
                print(f"Warning: Error deleting vector for node {node_id} (doc_id {doc_id}): {e}")
            
            # 3. Remove from mappings
            del self.node_id_to_faiss_id[node_id]
            if doc_id in self.faiss_id_to_node_id:
                 del self.faiss_id_to_node_id[doc_id]
            
            return True
        else:
            print(f"Warning: Node {node_id} found in DB but not in FAISS mappings.")
            return True # Node deleted from DB, but vector inconsistency noted

    def _get_ids_matching_filters(self, filters: CoordinateFilters) -> Optional[Set[str]]:
        """Retrieve a set of node IDs that match the coordinate filters."""
        if not filters or not filters.has_filters():
            return None

        logger.info(f"Filtering nodes based on coordinates: {filters}")

        matching_ids = self.db.query_by_coordinate_range(
            theta_min=filters.theta_min,
            theta_max=filters.theta_max,
            r_min=filters.r_min,
            r_max=filters.r_max,
            t_min=filters.t_min,
            t_max=filters.t_max,
            z_min=filters.z_min,
            z_max=filters.z_max,
            z_type=filters.z_type,
        )

        logger.info(f"Found {len(matching_ids)} nodes matching coordinate filters.")
        return matching_ids

    def _is_coordinate_match(self, node_coords: PolarTemporalCoordinate, filters: CoordinateFilters) -> bool:
        """Check if node coordinates match the specified filters."""
        # Shortcut for empty filters
        if not filters.has_filters():
            return True
            
        # Radius (Relevance) filters
        if filters.r_min is not None and node_coords.r < filters.r_min:
            return False
        if filters.r_max is not None and node_coords.r > filters.r_max:
            return False
            
        # Temporal sequence filters
        if filters.t_min is not None and node_coords.t < filters.t_min:
            return False
        if filters.t_max is not None and node_coords.t > filters.t_max:
            return False
            
        # Theta (Angular) filters
        if filters.theta_min is not None and filters.theta_max is not None:
            # Handle cases where theta_min > theta_max (crosses the 0/2π boundary)
            if filters.theta_min > filters.theta_max:
                # Check if node_theta is outside the excluded range
                if node_coords.theta > filters.theta_max and node_coords.theta < filters.theta_min:
                    return False
            else:
                # Normal case, theta_min <= theta_max
                if node_coords.theta < filters.theta_min or node_coords.theta > filters.theta_max:
                    return False
        elif filters.theta_min is not None and node_coords.theta < filters.theta_min:
            return False
        elif filters.theta_max is not None and node_coords.theta > filters.theta_max:
            return False
            
        # Z-coordinate filters
        if filters.z_min is not None and node_coords.z < filters.z_min:
            return False
        if filters.z_max is not None and node_coords.z > filters.z_max:
            return False
            
        # Z-type filter (only if specified)
        if filters.z_type is not None and node_coords.z_type != filters.z_type:
            return False
            
        # If passed all checks, the node matches the filters
        return True

    def search_with_nl_query(self, nl_query: str, k: int = 10) -> List[Tuple[Node, float]]:
        """
        Search the narrative atlas using natural language query with parsing and filtering.
        This is the main search entry point that leverages coordinate filters.
        
        Args:
            nl_query: Natural language query string.
            k: Maximum number of results to return.
            
        Returns:
            List of (node, score) tuples sorted by score.
        """
        start_time = time.time()
        # Parse the NL query to extract filters
        parsed_query = self.nl_parser.parse(nl_query)
        
        logger.info(f"Parsed query: '{nl_query}' into text='{parsed_query.query_text}', filters={parsed_query.filters}")
        
        # Get all nodes that match the filters (or all nodes if no filters)
        prefiltered_ids = self._get_ids_matching_filters(parsed_query.filters)

        # Sector augmentation: if the LLM left theta unset, derive it from the query text
        if (parsed_query.filters is not None
                and parsed_query.filters.theta_min is None
                and parsed_query.filters.theta_max is None):
            derived = _derive_sectors_from_query(nl_query)
            theta_range = _sectors_to_theta_range(derived) if derived else None
            if theta_range is not None:
                parsed_query.filters.theta_min = theta_range[0]
                parsed_query.filters.theta_max = theta_range[1]
                prefiltered_ids = self._get_ids_matching_filters(parsed_query.filters)
                logger.info(
                    "Sector augmentation: %s → theta=[%.4f, %.4f], %s nodes in filter",
                    derived, theta_range[0], theta_range[1],
                    len(prefiltered_ids) if prefiltered_ids is not None else "all",
                )

        # Use the semantic part of the query to get embeddings
        query_text = parsed_query.query_text or nl_query  # Fallback to original if no semantic extracted
        
        # Preprocess the query with default settings
        # This extracts keywords, estimates theta, etc.
        query_text, retrieval_params = self.preprocess_query(query_text, {
            'extract_keywords': True,
            'decompose_query': True,
            'estimate_theta': True
        })
        
        # Add filter-derived parameters to retrieval_params
        if parsed_query.filters:
            # If there's a temporal range specified, use middle as focus
            if parsed_query.filters.t_min is not None and parsed_query.filters.t_max is not None:
                retrieval_params['time_preference'] = (parsed_query.filters.t_min + parsed_query.filters.t_max) / 2
            
            # If there's a radial range, use it as preference
            if parsed_query.filters.r_min is not None and parsed_query.filters.r_max is not None:
                retrieval_params['radial_preference'] = {
                    'radius': (parsed_query.filters.r_min + parsed_query.filters.r_max) / 2,
                    'strength': 0.2
                }
            
            # If there's a theta range, use it for directional bias
            if parsed_query.filters.theta_min is not None and parsed_query.filters.theta_max is not None:
                # Use middle of the range for direction
                theta_mid = (parsed_query.filters.theta_min + parsed_query.filters.theta_max) / 2
                # Handle wrap-around case
                if parsed_query.filters.theta_min > parsed_query.filters.theta_max:
                    theta_mid = (theta_mid + np.pi) % (2 * np.pi)
                    
                retrieval_params['directional_bias'] = {
                    'direction': theta_mid,
                    'strength': 0.3
                }
                
            # If there's a z_type specified, add it to priority list
            if parsed_query.filters.z_type:
                retrieval_params['z_type_priority'] = [parsed_query.filters.z_type]
        
        # Use a pre-filtered FAISS search if we have filters
        if prefiltered_ids is not None:
            # If empty set returned, there are no matches
            if not prefiltered_ids:
                logger.info(f"No nodes match the coordinate filters for query: '{nl_query}'")
                return []
            
            # Search only within nodes matching filters
            filtered_nodes = [self.db.nodes[nid] for nid in prefiltered_ids]
            filtered_embeddings = [node.embedding for node in filtered_nodes if node.embedding is not None]
            
            if not filtered_embeddings:
                logger.warning("No valid embeddings found in filtered nodes")
                return []
                
            # Use these node embeddings for similarity search
            try:
                # Use our enhanced retrieval method with the node subset
                # First convert the filtered nodes to a format compatible with search_with_retrieval_params
                base_results = []
                
                # If we have Langchain FAISS wrapper
                if self.vector_store:
                    # Create a temporary embedding array for the query
                    query_embedding = self.embedding_service.embed_query(query_text)
                    
                    # Get similarity scores for all filtered nodes
                    for i, node in enumerate(filtered_nodes):
                        if node.embedding is not None:
                            # Use dot product similarity (cosine similarity for normalized vectors)
                            similarity = np.dot(query_embedding, node.embedding)
                            base_results.append((node, float(similarity)))
                    
                    # Sort by similarity (highest first)
                    base_results.sort(key=lambda x: x[1], reverse=True)
                
                # Apply additional score adjustments with retrieval_params
                results = []
                for node, score in base_results:
                    adjusted_score = score
                    
                    # Apply temporal decay if time_preference is specified
                    if 'time_preference' in retrieval_params:
                        adjusted_score = self.apply_temporal_decay(
                            adjusted_score, 
                            node.coordinates.t, 
                            retrieval_params['time_preference'],
                            retrieval_params.get('temporal_decay_rate', 0.1)
                        )
                    
                    # Apply directional bias if specified
                    if 'directional_bias' in retrieval_params:
                        bias = retrieval_params['directional_bias']
                        adjusted_score = self.apply_directional_bias(
                            adjusted_score,
                            node.coordinates.theta,
                            bias['direction'],
                            bias.get('strength', 0.3)
                        )
                    
                    # Apply radial preference if specified
                    if 'radial_preference' in retrieval_params:
                        pref = retrieval_params['radial_preference']
                        adjusted_score = self.apply_radial_preference(
                            adjusted_score,
                            node.coordinates.r,
                            pref['radius'],
                            pref.get('strength', 0.2)
                        )
                    
                    # Boost score for relevant keywords
                    if 'boost_keywords' in retrieval_params and node.keywords:
                        keywords = retrieval_params['boost_keywords']
                        matching_keywords = set(keywords).intersection(set(node.keywords))
                        if matching_keywords:
                            keyword_boost = len(matching_keywords) / len(keywords) * 0.2
                            adjusted_score += keyword_boost
                    
                    # Apply z_type priority if specified
                    if 'z_type_priority' in retrieval_params and node.coordinates.z_type in retrieval_params['z_type_priority']:
                        adjusted_score += 0.1  # Simple boost for matching z_type
                    
                    results.append((node, adjusted_score))
                
                # Sort by adjusted score
                results.sort(key=lambda x: x[1], reverse=True)
                
                # Return top k results
                return results[:k]
                    
            except Exception as e:
                logger.error(f"Error in similarity search with filtered nodes: {e}", exc_info=True)
                return []
        else:
            # No filters, use the enhanced retrieval method directly
            return self.search_with_retrieval_params(query_text, retrieval_params, k)
                
    def search_with_sector_filter(
        self,
        query: str,
        sectors: Optional[List[str]] = None,
        k: int = 10,
        confidence_threshold: float = 0.1,
    ) -> List[Tuple[Node, float]]:
        """Semantic search pre-filtered to specific compass sectors.

        Args:
            query: Natural-language search text (also used for embedding similarity).
            sectors: Explicit 8-point sector names e.g. ["N", "NE"], or None to derive
                     from query text automatically via SectorLegend (no LLM required).
            k: Maximum results to return.
            confidence_threshold: Minimum SectorLegend confidence when auto-deriving sectors.

        Returns:
            List of (Node, similarity_score) sorted descending. Falls back to unfiltered
            search when no sectors are matched or the sector filter returns 0 nodes.
        """
        resolved = sectors if sectors is not None else _derive_sectors_from_query(
            query, confidence_threshold
        )
        theta_ranges = _sectors_to_theta_ranges(resolved) if resolved else []

        prefiltered_ids: Optional[Set[str]] = None
        if theta_ranges:
            prefiltered_ids = self.db.query_by_coordinate_range(theta_ranges=theta_ranges)
            logger.info(
                "search_with_sector_filter: sectors=%s → %d candidate nodes",
                resolved, len(prefiltered_ids) if prefiltered_ids else 0,
            )

        if not prefiltered_ids:
            if theta_ranges:
                logger.warning(
                    "Sector filter matched 0 nodes — falling back to unfiltered search"
                )
            return self.find_similar_nodes(query, k=k)

        try:
            query_emb = np.array(self.embedding_service.embed_query(query))
            results: List[Tuple[Node, float]] = []
            for nid in prefiltered_ids:
                node = self.db.nodes[nid]
                if node.embedding is not None:
                    sim = float(np.dot(query_emb, node.embedding))
                    results.append((node, sim))
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:k]
        except Exception:
            logger.exception("Sector-filtered search failed — falling back to unfiltered")
            return self.find_similar_nodes(query, k=k)

    def answer_query_with_context(self, user_query: str, k: int = 3) -> str:
        """
        Generate an answer to a user query using retrieved context nodes.
        Uses the enhanced retrieval methods for better context selection.

        Args:
            user_query: The user's question
            k: Number of context nodes to retrieve
            
        Returns:
            Generated answer string
        """
        # Parse the query to extract any coordinate filters
        parsed_query = self.nl_parser.parse(user_query)
        
        # Preprocess the query to extract keywords, estimate theta, etc.
        query_text, retrieval_params = self.preprocess_query(
            parsed_query.query_text or user_query,
            {
                'extract_keywords': True,
                'decompose_query': True,
                'estimate_theta': True,
                'default_r_preference': 0.5  # Prefer more relevant nodes
            }
        )
        
        # Add any coordinate filters to retrieval params
        if parsed_query.filters:
            # Focus on temporal range if specified
            if parsed_query.filters.t_min is not None or parsed_query.filters.t_max is not None:
                t_min = parsed_query.filters.t_min or 0
                t_max = parsed_query.filters.t_max or float('inf')
                # Use middle of range as focus point
                if t_max < float('inf'):
                    retrieval_params['time_preference'] = (t_min + t_max) / 2
            
            # Use z_type priority if specified
            if parsed_query.filters.z_type:
                retrieval_params['z_type_priority'] = [parsed_query.filters.z_type]
        
        # Use our enhanced retrieval method
        results = self.search_with_retrieval_params(query_text, retrieval_params, k=k)
        
        if not results:
            return f"I couldn't find any relevant information to answer your question about '{user_query}'."
        
        # Construct context from results
        context_parts = []
        for i, (node, score) in enumerate(results):
            # Extract meaningful content from the node
            if isinstance(node.content, dict):
                if 'text' in node.content:
                    content_text = node.content['text']
                else:
                    # Fallback to serializing the content dict
                    content_text = json.dumps(node.content)
            else:
                content_text = str(node.content)
                
            # Add metadata about the source 
            source_info = f"[Source {i+1}: {node.type}"
            if node.coordinates:
                source_info += f" (t={node.coordinates.t:.2f}, r={node.coordinates.r:.2f}"
                
                # Add directional info using angle conversion to compass directions
                theta_degrees = (node.coordinates.theta * 180 / np.pi) % 360
                directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                direction_idx = int(((theta_degrees + 22.5) % 360) / 45)
                source_info += f", direction={directions[direction_idx]}°"
                
                source_info += f", score={score:.3f})"
            source_info += "]"
            
            # Add this chunk to context
            context_parts.append(f"{source_info}\n{content_text}\n")
            
        # Join all context parts
        context = "\n".join(context_parts)
        
        # Generate answer using LLM (in a real implementation)
        answer = f"Based on the retrieved information, here's the answer to your question about '{user_query}':\n\n"
        
        # For now, just return the context with explanation
        # In a full implementation, this would use an LLM to generate an answer
        answer += context
        
        return answer

    def update_node_coordinates(self, node_id: str, new_coordinates: PolarTemporalCoordinate) -> bool:
        """
        Updates the coordinates of an existing node and its metadata in the docstore.

        Args:
            node_id: The ID of the node to update.
            new_coordinates: The new PolarTemporalCoordinate object.

        Returns:
            True if the update was successful, False otherwise.
        """
        if node_id not in self.db.nodes:
            logger.warning(f"Attempted to update coordinates for non-existent node: {node_id}")
            return False

        if self.vector_store is None or not hasattr(self.vector_store, 'docstore'):
            logger.error("Vector store or docstore not initialized. Cannot update node coordinates.")
            return False
            
        node_to_update = self.db.nodes[node_id]

        # 1. Update Node object's coordinates
        node_to_update.coordinates = new_coordinates
        logger.debug(f"Updated node {node_id} coordinates in internal DB.")

        # 2. Update coordinate metadata in the Node's metadata dict
        # Ensure metadata exists
        if not isinstance(node_to_update.metadata, dict):
             node_to_update.metadata = {} # Initialize if somehow missing/wrong type

        node_to_update.metadata['coord_r'] = new_coordinates.r
        node_to_update.metadata['coord_theta'] = new_coordinates.theta
        node_to_update.metadata['coord_t'] = new_coordinates.t
        node_to_update.metadata['coord_z'] = new_coordinates.z
        node_to_update.metadata['coord_z_type'] = new_coordinates.z_type
        logger.debug(f"Updated node {node_id} coordinate metadata.")

        # 3. Reconstruct the Document object with updated metadata
        # Assuming content is stored under 'text' key
        page_content = node_to_update.content.get('text', '') 
        updated_metadata = node_to_update.metadata 
        
        updated_document = Document(page_content=page_content, metadata=updated_metadata)

        # 4. Persist updated node to SQLite
        self.db.add_node(node_to_update)

        # 5. Update the document in the docstore using its add method
        # For InMemoryDocstore, adding with an existing ID overwrites.
        try:
            self.vector_store.docstore.add({node_id: updated_document})
            logger.info(f"Successfully updated coordinates and metadata for node {node_id} in docstore.")
            return True
        except Exception as e:
            logger.error(f"Error updating docstore for node {node_id}: {e}", exc_info=True)
            return False

    # --- Phase 3: Retrieval Methods Implementation ---
    
    def apply_temporal_decay(self, original_score: float, node_temporal: float, 
                           query_temporal: float, decay_rate: float = 0.1) -> float:
        """
        Apply temporal decay to a similarity score based on temporal distance.
        Higher decay_rate means more penalty for temporal distance.
        
        Args:
            original_score: Original similarity score
            node_temporal: Node's temporal coordinate
            query_temporal: Query's temporal coordinate (reference point)
            decay_rate: Rate of decay (higher = faster decay)
            
        Returns:
            Adjusted score after temporal decay
        """
        temporal_distance = abs(node_temporal - query_temporal)
        decay_factor = np.exp(-decay_rate * temporal_distance)
        return original_score * decay_factor
    
    def apply_directional_bias(self, original_score: float, node_theta: float, 
                             preferred_direction: float, bias_strength: float = 0.3) -> float:
        """
        Apply directional bias to favor results in a particular direction.
        
        Args:
            original_score: Original similarity score
            node_theta: Node's angular coordinate
            preferred_direction: Preferred direction in radians
            bias_strength: Strength of the directional bias (0-1)
            
        Returns:
            Adjusted score with directional bias
        """
        # Calculate angular distance (shortest distance on unit circle)
        angle_diff = abs((node_theta - preferred_direction + np.pi) % (2 * np.pi) - np.pi)
        max_diff = np.pi
        
        # Normalize to [0, 1] where 0 means perfect alignment
        normalized_diff = angle_diff / max_diff
        
        # Apply bias (higher score for closer alignment)
        direction_factor = 1.0 - (bias_strength * normalized_diff)
        return original_score * direction_factor
    
    def apply_radial_preference(self, original_score: float, node_r: float, 
                              preferred_radius: float, preference_strength: float = 0.2) -> float:
        """
        Apply preference for a specific radius/relevance level.
        
        Args:
            original_score: Original similarity score
            node_r: Node's radial coordinate
            preferred_radius: Preferred radial distance
            preference_strength: Strength of the preference (0-1)
            
        Returns:
            Adjusted score with radial preference
        """
        # Calculate radial distance and normalize by a reasonable max range
        radial_diff = abs(node_r - preferred_radius)
        max_diff = 10.0  # Assuming this is a reasonable maximum difference
        
        # Normalize to [0, 1]
        normalized_diff = min(radial_diff / max_diff, 1.0)
        
        # Apply preference (higher score for closer to preferred radius)
        radial_factor = 1.0 - (preference_strength * normalized_diff)
        return original_score * radial_factor
    
    def search_with_retrieval_params(self, query_text: str, retrieval_params: dict = None, k: int = 10) -> List[Tuple[Node, float]]:
        """
        Enhanced search with configurable retrieval parameters.
        
        Args:
            query_text: The semantic query text
            retrieval_params: Dictionary of retrieval parameters to customize behavior
                - temporal_decay_rate: float (default: 0.1)
                - directional_bias: dict with 'direction' (radians) and 'strength' (0-1)
                - radial_preference: dict with 'radius' and 'strength' (0-1)
                - time_preference: float (temporal coordinate to focus on)
                - boost_keywords: list of keywords to boost score for
                - keyword_boost_factor: float (default: 0.2)
                - z_type_priority: list of z_types to prioritize in results
                - min_score_threshold: float (default: 0.0)
            k: Maximum number of results to return
            
        Returns:
            List of (node, score) tuples sorted by adjusted score
        """
        # Default parameters
        if retrieval_params is None:
            retrieval_params = {}
            
        # Extract parameters with defaults
        temporal_decay_rate = retrieval_params.get('temporal_decay_rate', 0.1)
        time_preference = retrieval_params.get('time_preference', None)
        directional_bias = retrieval_params.get('directional_bias', None)
        radial_preference = retrieval_params.get('radial_preference', None)
        boost_keywords = retrieval_params.get('boost_keywords', [])
        keyword_boost_factor = retrieval_params.get('keyword_boost_factor', 0.2)
        z_type_priority = retrieval_params.get('z_type_priority', [])
        min_score_threshold = retrieval_params.get('min_score_threshold', 0.0)
        
        # Get the base semantic search results (could be a raw or prefiltered search)
        base_results = self.find_similar_nodes(query_text, k=min(k * 2, 100))  # Get more results than needed for reranking
        
        if not base_results:
            logger.warning(f"No base results found for query: '{query_text}'")
            return []
            
        # Apply score adjustments based on retrieval parameters
        adjusted_results = []
        for node, score in base_results:
            if score < min_score_threshold:
                continue
                
            adjusted_score = score
            
            # Apply temporal decay if time_preference is specified
            if time_preference is not None:
                adjusted_score = self.apply_temporal_decay(
                    adjusted_score, node.coordinates.t, time_preference, temporal_decay_rate
                )
                
            # Apply directional bias if specified
            if directional_bias and isinstance(directional_bias, dict):
                direction = directional_bias.get('direction', 0.0)
                strength = directional_bias.get('strength', 0.3)
                adjusted_score = self.apply_directional_bias(
                    adjusted_score, node.coordinates.theta, direction, strength
                )
                
            # Apply radial preference if specified
            if radial_preference and isinstance(radial_preference, dict):
                radius = radial_preference.get('radius', 0.5)
                strength = radial_preference.get('strength', 0.2)
                adjusted_score = self.apply_radial_preference(
                    adjusted_score, node.coordinates.r, radius, strength
                )
                
            # Boost score for relevant keywords
            if boost_keywords and node.keywords:
                matching_keywords = set(boost_keywords).intersection(set(node.keywords))
                if matching_keywords:
                    keyword_boost = len(matching_keywords) / len(boost_keywords) * keyword_boost_factor
                    adjusted_score += keyword_boost
                    
            # Boost for z_type priority
            if z_type_priority and node.coordinates.z_type in z_type_priority:
                # Prioritize by position in the list
                type_index = z_type_priority.index(node.coordinates.z_type)
                type_boost = (len(z_type_priority) - type_index) / len(z_type_priority) * 0.1
                adjusted_score += type_boost
                
            adjusted_results.append((node, adjusted_score))
            
        # Sort by adjusted score
        adjusted_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k results
        return adjusted_results[:k]
    
    def preprocess_query(self, query_text: str, params: dict = None) -> Tuple[str, dict]:
        """
        Preprocess a query to align with the coordinate system.
        
        Args:
            query_text: Original query text
            params: Optional parameters to guide preprocessing
                - extract_keywords: bool (default: True)
                - decompose_query: bool (default: False)
                - estimate_theta: bool (default: False)
                - default_r_preference: float or None
                - default_temporal_focus: float or None
            
        Returns:
            Tuple of (processed_query_text, retrieval_params)
        """
        # Default parameters
        if params is None:
            params = {}
            
        extract_keywords = params.get('extract_keywords', True)
        decompose_query = params.get('decompose_query', False)
        estimate_theta = params.get('estimate_theta', False)
        default_r_preference = params.get('default_r_preference', None)
        default_temporal_focus = params.get('default_temporal_focus', None)
        
        # Initialize retrieval params
        retrieval_params = {}
        
        # Extract keywords for boosting if requested
        if extract_keywords:
            # Use the same keyword extraction as in coordinate mapper
            from src.utils.coordinate_mapper import CoordinateMapper
            if not hasattr(self, '_coordinate_mapper_for_keywords'):
                # FIXED: Ensure consistent coordinate parameters with main mapper
                main_config = self.coordinate_mapper.get_config()
                self._coordinate_mapper_for_keywords = CoordinateMapper(
                    embedding_service=self.embedding_service,
                    use_embedding_for_coords=main_config.get('use_embedding_coords', True),
                    embedding_r_scale=main_config.get('embedding_r_scale', 1.0),
                    embedding_theta_scale=main_config.get('embedding_theta_scale', 3.14159)
                )
                logger.info(f"Created keyword extraction coordinate mapper with matching config: {main_config}")
            keywords = self._coordinate_mapper_for_keywords._extract_keywords(query_text)
            retrieval_params['boost_keywords'] = keywords
            
        # Decompose complex queries if requested
        if decompose_query:
            # Simple approach: look for sections separated by 'and', 'or', etc.
            import re
            parts = re.split(r'\s+(?:and|or|plus|with|including)\s+', query_text, flags=re.IGNORECASE)
            if len(parts) > 1:
                # If decomposed, we might use the main part as the query
                query_text = parts[0].strip()
                # And add additional parts as keywords to boost
                additional_keywords = []
                for part in parts[1:]:
                    words = re.findall(r'\b\w+\b', part)
                    additional_keywords.extend(words)
                retrieval_params.setdefault('boost_keywords', []).extend(additional_keywords)
                
        # Estimate theta (topic angle) if requested
        if estimate_theta and self.embedding_service:
            try:
                # Get the query embedding
                query_embedding = np.array(self.embedding_service.embed_query(query_text))
                
                # We can use the first two dimensions after normalization to estimate a topic angle
                if len(query_embedding) >= 2:
                    normalized = query_embedding / np.linalg.norm(query_embedding)
                    # Use first two dimensions to get an angle
                    theta = np.arctan2(normalized[1], normalized[0]) % (2 * np.pi)
                    
                    # Use this as a directional bias
                    retrieval_params['directional_bias'] = {
                        'direction': float(theta),
                        'strength': 0.2  # Moderate strength
                    }
            except Exception as e:
                logger.warning(f"Failed to estimate theta for query: {e}")
                
        # Apply default preferences if specified
        if default_r_preference is not None:
            retrieval_params['radial_preference'] = {
                'radius': default_r_preference,
                'strength': 0.15  # Mild preference
            }
            
        if default_temporal_focus is not None:
            retrieval_params['time_preference'] = default_temporal_focus
            
        return query_text, retrieval_params
    
    def search_with_temporal_focus(self, query_text: str, temporal_focus: float, 
                                 decay_rate: float = 0.1, k: int = 10) -> List[Tuple[Node, float]]:
        """
        Search with a specific temporal focus point.
        
        Args:
            query_text: The query text
            temporal_focus: The temporal coordinate to focus around
            decay_rate: Rate of decay away from focus point
            k: Maximum number of results
            
        Returns:
            List of (node, score) tuples
        """
        retrieval_params = {
            'time_preference': temporal_focus,
            'temporal_decay_rate': decay_rate
        }
        return self.search_with_retrieval_params(query_text, retrieval_params, k)
    
    def search_with_directional_bias(self, query_text: str, direction: float, 
                                   strength: float = 0.3, k: int = 10) -> List[Tuple[Node, float]]:
        """
        Search with bias toward a specific direction in the polar coordinate space.
        
        Args:
            query_text: The query text
            direction: Preferred direction in radians
            strength: Strength of the directional bias (0-1)
            k: Maximum number of results
            
        Returns:
            List of (node, score) tuples
        """
        retrieval_params = {
            'directional_bias': {
                'direction': direction,
                'strength': strength
            }
        }
        return self.search_with_retrieval_params(query_text, retrieval_params, k)
    
    def validate_coordinate_config(self, query_config: dict) -> dict:
        """
        Validate query coordinate config against storage config to prevent mismatches.
        If critical parameters don't match, warns and returns storage configuration.
        
        Args:
            query_config: The coordinate configuration from the query
            
        Returns:
            The validated configuration to use (typically storage config if mismatch)
        """
        # Get storage configuration from the coordinate mapper
        storage_config = self.coordinate_mapper.get_config()
        
        # Check for critical parameter mismatches
        critical_params = ['use_embedding_coords', 'embedding_r_scale', 'embedding_theta_scale']
        has_mismatch = False
        
        for param in critical_params:
            query_param = param
            mapper_param = param
            
            # Handle difference in parameter naming between query and mapper
            if param == 'use_embedding_coords':
                mapper_param = 'use_embedding_for_coords'
            
            if query_param in query_config and mapper_param in storage_config:
                if query_config[query_param] != storage_config[mapper_param]:
                    logger.warning(f"Coordinate parameter mismatch: storage {mapper_param}={storage_config[mapper_param]}, "
                                  f"query {query_param}={query_config[query_param]}. Using storage value.")
                    has_mismatch = True
        
        if has_mismatch:
            logger.warning("Critical coordinate parameter mismatch detected. Using storage configuration to avoid retrieval issues.")
            # Convert use_embedding_for_coords to use_embedding_coords for query 
            adjusted_config = {
                'use_embedding_coords': storage_config['use_embedding_for_coords'],
                'embedding_r_scale': storage_config['embedding_r_scale'],
                'embedding_theta_scale': storage_config['embedding_theta_scale'],
            }
            return adjusted_config
        
        return query_config
    
    def search_with_hyde(self, 
                       query: str, 
                       hypothesis_prompt: str = None, 
                       llm_model: str = "gpt-3.5-turbo", 
                       k: int = 10) -> List[Tuple[Node, float]]:
        """
        Implement Hypothetical Document Embeddings (HyDE) retrieval.
        This method generates a hypothetical document that would answer the query,
        then embeds that document rather than the query for better semantic search.
        
        Args:
            query: The user's query
            hypothesis_prompt: Optional custom prompt for hypothesis generation
            llm_model: LLM model to use for generating hypothetical document
            k: Number of results to retrieve
            
        Returns:
            List of (node, score) tuples representing search results
        """
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage
        
        logger.info(f"Executing HyDE search for query: '{query}'")
        
        # Default prompt for generating a hypothetical answer
        if hypothesis_prompt is None:
            hypothesis_prompt = f"""
            Write a short passage that would answer the following question directly.
            Keep your response factual and concise, as if you were writing an encyclopedia entry.
            DO NOT include phrases like "the answer is" or "in conclusion".
            Just write the content that would contain the answer.
            
            Question: {query}
            """
        
        try:
            # Initialize LLM for hypothetical document generation
            llm = ChatOpenAI(model=llm_model, temperature=0.2)
            
            # Generate hypothetical document
            messages = [HumanMessage(content=hypothesis_prompt)]
            hypothetical_doc = llm.invoke(messages).content
            
            logger.info(f"Generated hypothetical document: {hypothetical_doc[:100]}...")
            
            # Embed the hypothetical document instead of the query
            results = self.find_similar_nodes(hypothetical_doc, k=k)
            
            # Adjust scores based on query-specific parameters if needed
            # For now, just use the raw similarity scores
            
            return results
            
        except Exception as e:
            logger.error(f"Error in HyDE search: {e}", exc_info=True)
            # Fall back to regular search if HyDE fails
            logger.info("Falling back to regular search after HyDE failure")
            return self.find_similar_nodes(query, k=k)

    def search_with_hybrid(self, query: str, keyword_weight: float = 0.3, k: int = 10) -> List[Tuple[Node, float]]:
        """
        Implement hybrid search combining semantic (embedding) search with keyword-based search.
        This addresses limitations of pure semantic search, especially for explicit keyword queries.
        
        Args:
            query: The user's query
            keyword_weight: Weight to give keyword matches (0-1)
            k: Number of results to retrieve
            
        Returns:
            List of (node, score) tuples representing search results
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        import re
        
        logger.info(f"Executing hybrid search for query: '{query}'")
        
        # Extract keywords from query using simple method
        def extract_keywords(text):
            # Remove stop words and extract key terms
            stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'if', 'then', 'else', 'when', 
                         'at', 'from', 'by', 'for', 'with', 'about', 'to', 'in', 'on', 'is', 'are'}
            words = re.findall(r'\b\w+\b', text.lower())
            return [w for w in words if w not in stop_words and len(w) > 2]
        
        query_keywords = extract_keywords(query)
        logger.info(f"Extracted keywords from query: {query_keywords}")
        
        # If no keywords extracted but the query is a single meaningful word, use it
        if not query_keywords and len(query.strip()) > 2:
            query_keywords = [query.strip().lower()]
            logger.info(f"Using full query as keyword: {query_keywords}")
        
        try:
            # 1. Get semantic search results
            semantic_results = self.find_similar_nodes(query, k=k*2)  # Get more for merging
            
            # 2. ENHANCED: Perform direct content search for exact keyword matches
            exact_matches = []
            
            # First, try exact string matching for each keyword
            for node_id, node in self.db.nodes.items():
                content_text = ""
                
                # Extract searchable text from node content
                if isinstance(node.content, dict):
                    if 'text' in node.content:
                        content_text = node.content['text'].lower()
                    else:
                        # Serialize other content fields
                        content_text = json.dumps(node.content).lower()
                else:
                    content_text = str(node.content).lower()
                
                # Check for exact matches of query keywords
                for keyword in query_keywords:
                    if keyword in content_text:
                        # Calculate a match score - higher if multiple occurrences
                        count = content_text.count(keyword)
                        match_score = 1.0 + (0.1 * min(count-1, 10))  # Cap bonus at 10 occurrences
                        exact_matches.append((node, match_score))
                        break  # Found one match, move to next node
            
            logger.info(f"Found {len(exact_matches)} exact keyword matches")
                
            # 3. Combine results using a weighted approach
            # First, combine semantic and exact match results
            all_results = {}
            
            # Add semantic results
            for node, score in semantic_results:
                all_results[node.id] = {
                    'node': node, 
                    'semantic_score': score,
                    'exact_score': 0.0,
                    'combined_score': (1.0 - keyword_weight) * score
                }
                
            # Add or update with exact match results    
            for node, score in exact_matches:
                if node.id in all_results:
                    all_results[node.id]['exact_score'] = score
                    all_results[node.id]['combined_score'] += keyword_weight * score
                else:
                    all_results[node.id] = {
                        'node': node,
                        'semantic_score': 0.0,
                        'exact_score': score,
                        'combined_score': keyword_weight * score
                    }
            
            # Sort by combined score and convert back to (node, score) tuples
            sorted_results = sorted(all_results.values(), key=lambda x: x['combined_score'], reverse=True)
            
            # Log detailed matching information for top results
            for i, result in enumerate(sorted_results[:min(3, len(sorted_results))]):
                logger.info(f"Top result {i+1}: node_id={result['node'].id}, semantic_score={result['semantic_score']:.3f}, "
                           f"exact_score={result['exact_score']:.3f}, combined_score={result['combined_score']:.3f}")
            
            return [(item['node'], item['combined_score']) for item in sorted_results[:k]]
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}", exc_info=True)
            # Fall back to regular search if hybrid search fails
            logger.info("Falling back to regular search after hybrid search failure")
            return semantic_results[:k] if semantic_results else []
    
    # --- End Phase 3: Retrieval Methods Implementation --- 
    
    # --- Begin Phase 8: Advanced Retrieval Enhancement ---
    
    def search_with_colbert(self, query: str, k: int = 10) -> List[Tuple[Node, float]]:
        """
        Search using ColBERT-style token-level retrieval for more precise matching.
        
        Args:
            query: The query text
            k: Number of results to return
            
        Returns:
            List of (node, score) tuples
        """
        from src.models.advanced_retrieval import ColBERTRetriever
        
        logger.info(f"Executing ColBERT search for query: '{query}'")
        
        try:
            # Initialize ColBERT retriever
            colbert = ColBERTRetriever(self.embedding_service)
            
            # We need to first pre-filter nodes to a reasonable number
            # since ColBERT processing is computationally expensive
            prefiltered_nodes = []
            
            # Use standard vector search to get a broader set of candidates
            candidate_results = self.find_similar_nodes(query, k=min(k*5, 100))
            prefiltered_nodes = [node for node, _ in candidate_results]
            
            logger.info(f"Pre-filtered to {len(prefiltered_nodes)} nodes for ColBERT processing")
            
            # Apply ColBERT retrieval on the pre-filtered nodes
            results = colbert.retrieve(query, prefiltered_nodes, k=k)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in ColBERT search: {e}", exc_info=True)
            # Fall back to regular search
            return self.find_similar_nodes(query, k=k)
    
    def search_with_reranking(self, query: str, k: int = 10, initial_k: int = 30) -> List[Tuple[Node, float]]:
        """
        Search with Cohere reranking for improved relevance ordering.
        
        Args:
            query: The query text
            k: Number of final results to return
            initial_k: Number of initial results to retrieve before reranking
            
        Returns:
            List of (node, score) tuples
        """
        from src.models.advanced_retrieval import CohereReranker
        
        logger.info(f"Executing search with Cohere reranking for query: '{query}'")
        
        try:
            # First get initial results with our standard retrieval method
            # We retrieve more results than needed for reranking
            initial_results = self.find_similar_nodes(query, k=initial_k)
            
            # Initialize the reranker
            reranker = CohereReranker()
            
            # Rerank the results
            reranked_results = reranker.rerank(query, initial_results, top_n=k)
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"Error in reranking search: {e}", exc_info=True)
            # Fall back to regular search
            return self.find_similar_nodes(query, k=k)
    
    def search_with_mmr(self, query: str, k: int = 10, lambda_param: float = 0.7) -> List[Tuple[Node, float]]:
        """
        Search with Maximal Marginal Relevance for diverse results.
        
        Args:
            query: The query text
            k: Number of results to return
            lambda_param: Diversity-relevance trade-off parameter (0-1)
                Higher values favor relevance, lower values favor diversity
            
        Returns:
            List of (node, score) tuples
        """
        from src.models.advanced_retrieval import MaximalMarginalRelevance
        
        logger.info(f"Executing MMR search for query: '{query}'")
        
        try:
            # Get query embedding
            query_embedding = np.array(self.embedding_service.embed_query(query))
            
            # First get a larger set of candidates
            initial_results = self.find_similar_nodes(query, k=min(k*3, 100))
            
            # Apply MMR reranking
            mmr = MaximalMarginalRelevance(lambda_param=lambda_param)
            diverse_results = mmr.rerank(query_embedding, initial_results, k=k)
            
            return diverse_results
            
        except Exception as e:
            logger.error(f"Error in MMR search: {e}", exc_info=True)
            # Fall back to regular search
            return self.find_similar_nodes(query, k=k)
    
    def search_with_rag_fusion(self, query: str, k: int = 10) -> List[Tuple[Node, float]]:
        """
        Search using RAG-Fusion to combine multiple retrieval methods.
        
        Args:
            query: The query text
            k: Number of results to return
            
        Returns:
            List of (node, score) tuples
        """
        from src.models.advanced_retrieval import RAGFusionRetriever
        
        logger.info(f"Executing RAG-Fusion search for query: '{query}'")
        
        try:
            # Define the retrievers to use in fusion
            retrievers = [
                # Standard semantic search
                lambda q: self.find_similar_nodes(q, k=k*2),
                
                # Hybrid search
                lambda q: self.search_with_hybrid(q, keyword_weight=0.3, k=k*2),
                
                # HyDE search
                lambda q: self.search_with_hyde(q, k=k*2)
            ]
            
            # Initialize RAG-Fusion retriever
            fusion_retriever = RAGFusionRetriever(retrievers)
            
            # Retrieve results
            results = fusion_retriever.retrieve(query, k=k)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in RAG-Fusion search: {e}", exc_info=True)
            # Fall back to regular search
            return self.find_similar_nodes(query, k=k)
    
    def search_with_weighted_ensemble(self, query: str, k: int = 10) -> List[Tuple[Node, float]]:
        """
        Search using a weighted ensemble of multiple retrieval methods.
        
        Args:
            query: The query text
            k: Number of results to return
            
        Returns:
            List of (node, score) tuples
        """
        from src.models.advanced_retrieval import weighted_fusion
        
        logger.info(f"Executing weighted ensemble search for query: '{query}'")
        
        try:
            # Get results from different retrieval methods
            results_semantic = self.find_similar_nodes(query, k=k*2)
            results_hybrid = self.search_with_hybrid(query, k=k*2)
            results_mmr = self.search_with_mmr(query, k=k*2)
            
            # Try to get results from ColBERT, but handle potential failure
            try:
                results_colbert = self.search_with_colbert(query, k=k*2)
            except Exception as e:
                logger.warning(f"ColBERT retrieval failed, excluding from ensemble: {e}")
                results_colbert = []
            
            # Define weights for each method
            # These can be tuned based on performance evaluation
            weights = []
            result_lists = []
            
            # Only include methods that returned results
            if results_semantic:
                result_lists.append(results_semantic)
                weights.append(0.3)  # Standard semantic search weight
                
            if results_hybrid:
                result_lists.append(results_hybrid)
                weights.append(0.3)  # Hybrid search weight
                
            if results_mmr:
                result_lists.append(results_mmr)
                weights.append(0.2)  # MMR search weight
                
            if results_colbert:
                result_lists.append(results_colbert)
                weights.append(0.2)  # ColBERT search weight
            
            # If we have multiple result types, perform weighted fusion
            if len(result_lists) > 1:
                # Normalize weights to sum to 1.0
                total_weight = sum(weights)
                normalized_weights = [w / total_weight for w in weights]
                
                # Perform weighted fusion
                results = weighted_fusion(result_lists, normalized_weights, k=k)
            elif len(result_lists) == 1:
                # If only one type of results, just use those
                results = result_lists[0][:k]
            else:
                # Fall back to standard search if no methods succeeded
                results = self.find_similar_nodes(query, k=k)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in weighted ensemble search: {e}", exc_info=True)
            # Fall back to regular search
            return self.find_similar_nodes(query, k=k)
    
    # --- End Phase 8: Advanced Retrieval Enhancement --- 