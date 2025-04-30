import os
import json
import faiss
import numpy as np
import shutil
import pickle
from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field, asdict
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from src.models.spatial_temporal_db import SpatialTemporalDB
from src.utils.embedding_service import EmbeddingService
from src.coordinates import PolarTemporalCoordinate
import time
import hashlib
import logging
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from src.nl_parser import CoordinateFilters, NlQueryParser, ParsedQuery

# --- Add Logger Setup ---
logging.basicConfig(
    level=logging.INFO, # Or use level from env var/config
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('NarrativeAtlas') # Create logger instance
# --- End Logger Setup ---

if TYPE_CHECKING:
    from src.services.embedding_service import EmbeddingService
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
        self.db = SpatialTemporalDB()
        self.embedding_service = embedding_service
        from src.utils.coordinate_mapper import CoordinateMapper
        self.coordinate_mapper = CoordinateMapper(
            embedding_service=self.embedding_service,
            default_chunk_layer=int(os.getenv('DEFAULT_CHUNK_LAYER', 2)),
            base_radius=float(os.getenv('BASE_RADIUS', 0.9))
        )
        self.embedding_dim = self.embedding_service.embedding_dim
        
        # Langchain FAISS wrapper (still used for search/docstore)
        self.vector_store: Optional[FAISS] = None
        # Raw FAISS index (for direct adding)
        self.raw_faiss_index: Optional[faiss.Index] = None
        
        # Mappings for direct FAISS interaction
        self.node_id_to_faiss_id: Dict[str, int] = {}
        self.faiss_id_to_node_id: Dict[int, str] = {}
        self.next_faiss_id: int = 0 # Counter for next available FAISS integer ID

        # Keep NL Parser
        self.nl_parser = NlQueryParser()
        
        self._initialize_vector_store()
        self.load()
    
    def _create_new_hnsw_index(self) -> Tuple[faiss.Index, FAISS]:
        """Creates a new raw FAISS HNSW index and its Langchain wrapper."""
        print("Creating new FAISS index with HNSW.")
        M = 32  # Number of connections for HNSW
        
        # Define the HNSW index
        raw_index = faiss.IndexHNSWFlat(self.embedding_dim, M, faiss.METRIC_L2)
        
        # --- IMPORTANT: FAISS requires an ID map for add_with_ids --- 
        # Wrap the HNSW index with IndexIDMap2. This maps external 64-bit IDs
        # to internal sequential IDs used by the HNSW structure.
        index_with_ids = faiss.IndexIDMap2(raw_index)
        
        # Create an empty docstore for the Langchain wrapper
        docstore = InMemoryDocstore()
        
        # Initialize the LangChain FAISS wrapper
        vector_store_wrapper = FAISS(
            embedding_function=self.embedding_service, 
            index=index_with_ids, # Pass the index wrapped with IDMap2
            docstore=docstore,
            index_to_docstore_id={}
        )
        return index_with_ids, vector_store_wrapper # Return both

    def _initialize_vector_store(self):
        """Initialize or load the FAISS vector store (raw index and Langchain wrapper)."""
        index_folder = os.path.join(self.storage_path)
        index_file = os.path.join(index_folder, "index.faiss") # Path for raw FAISS index
        id_maps_path = os.path.join(self.storage_path, "id_maps.json")
        docstore_file = os.path.join(index_folder, "index.pkl") # Default Langchain FAISS docstore file

        try:
            if os.path.exists(index_file) and os.path.exists(docstore_file):
                print(f"Loading existing FAISS index from {index_file}")
                # Load raw FAISS index directly
                self.raw_faiss_index = faiss.read_index(index_file)
                self.next_faiss_id = self.raw_faiss_index.ntotal
                print(f"Raw index loaded. ntotal: {self.next_faiss_id}")

                # Load the Langchain wrapper (primarily for docstore and search methods)
                # We pass the *already loaded* raw index to avoid re-reading
                # Also need to load the docstore and index_to_docstore_id mapping explicitly
                # because load_local usually handles this.
                print(f"Loading Langchain FAISS wrapper components from {index_folder}")
                with open(docstore_file, "rb") as f:
                     docstore, index_to_docstore_id = pickle.load(f)
                     
                self.vector_store = FAISS(
                     embedding_function=self.embedding_service,
                     index=self.raw_faiss_index, # Use the loaded raw index
                     docstore=docstore,
                     index_to_docstore_id=index_to_docstore_id
                )
                print(f"Langchain wrapper initialized with loaded index and docstore (docstore size: {len(index_to_docstore_id)}).")

                # Load ID maps (node_id <-> faiss_id)
                if os.path.exists(id_maps_path):
                    with open(id_maps_path, 'r') as f:
                        maps = json.load(f)
                        self.node_id_to_faiss_id = maps.get('node_id_to_faiss_id', {})
                        # Convert JSON string keys back to integers for faiss_id_to_node_id
                        self.faiss_id_to_node_id = {int(k): v for k, v in maps.get('faiss_id_to_node_id', {}).items()}
                        # Load the next ID counter if saved (optional, recalculating from ntotal is safer)
                        # self.next_faiss_id = maps.get('next_faiss_id', self.raw_faiss_index.ntotal)
                else:
                     print("Warning: Index files found but id_maps.json missing.")
                     # Attempt to reconstruct maps if possible? Risky.
                     self.node_id_to_faiss_id = {}
                     self.faiss_id_to_node_id = {}
                     # Reset next_faiss_id based on loaded index size
                     self.next_faiss_id = self.raw_faiss_index.ntotal
            else:
                print("Index files not found, creating new HNSW index.")
                # Create a new index and wrapper
                self.raw_faiss_index, self.vector_store = self._create_new_hnsw_index()
                self.node_id_to_faiss_id = {}
                self.faiss_id_to_node_id = {}
                self.next_faiss_id = 0 # Start counter at 0 for new index
                
        except Exception as e:
            print(f"Error loading or creating vector store: {e}. Creating new HNSW index.")
            # Fallback to creating a new index and wrapper
            self.raw_faiss_index, self.vector_store = self._create_new_hnsw_index()
            self.node_id_to_faiss_id = {}
            self.faiss_id_to_node_id = {}
            self.next_faiss_id = 0
    
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
            self.db.nodes[node_id] = node
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
        self.db.nodes[node_id] = node
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
            self.db.nodes[node_id] = node
            # No call to _add_or_update_embedding here
        return node_id

    def _add_or_update_embedding(self,
                               node: Node,
                               text_to_embed: Optional[str] = None,
                               precomputed_embedding: Optional[np.ndarray] = None):
        """
        Adds or updates the node's embedding in the FAISS index and the node object itself.
        Handles both precomputed embeddings and generating them from text.
        Uses direct FAISS index manipulation (add_with_ids).
        Also updates the Langchain FAISS docstore for compatibility.
        """
        if self.raw_faiss_index is None or self.vector_store is None:
            logger.error("FAISS index or vector store not initialized. Cannot add embedding.")
            return

        embedding_to_add = None
        if precomputed_embedding is not None:
            embedding_to_add = precomputed_embedding
        elif text_to_embed:
            try:
                # Get embedding from service
                embedding_to_add = self.embedding_service.get_embedding(text_to_embed)
                # Ensure it's a numpy array of float32
                if embedding_to_add is not None:
                    embedding_to_add = np.array(embedding_to_add, dtype=np.float32)
            except Exception as e:
                logger.error(f"Error getting embedding for node {node.id}: {e}")
                # Decide if we should proceed without embedding or raise error
                return # Do not proceed without embedding
        
        # Ensure we have an embedding vector
        if embedding_to_add is None:
            logger.warning(f"No embedding available for node {node.id}. Cannot add to FAISS.")
            return
            
        # Ensure embedding dimension matches index
        if embedding_to_add.shape[0] != self.embedding_dim:
             logger.error(f"Embedding dimension mismatch for node {node.id}. Expected {self.embedding_dim}, got {embedding_to_add.shape[0]}.")
             return

        # Update the node object with the embedding
        node.embedding = embedding_to_add

        # Assign or get the FAISS integer ID for this node_id
        if node.id in self.node_id_to_faiss_id:
            faiss_id = self.node_id_to_faiss_id[node.id]
            # FAISS HNSW doesn't easily support updates, so we treat this as an add
            # Note: This means duplicate vectors if called multiple times for the same node.id
            # Proper update would require removing the old ID and adding the new one.
            logger.warning(f"Node {node.id} already has FAISS ID {faiss_id}. Re-adding (potential duplicate vector).")
            # For simplicity in this example, we just add it again with the same ID
        else:
            # Assign the next available integer ID
            faiss_id = self.next_faiss_id
            self.node_id_to_faiss_id[node.id] = faiss_id
            self.faiss_id_to_node_id[faiss_id] = node.id
            self.next_faiss_id += 1 # Increment for the next node

        # Add the vector to the raw FAISS index using the assigned integer ID
        vector_np = embedding_to_add.reshape(1, -1) # Reshape for FAISS
        ids_np = np.array([faiss_id], dtype=np.int64)
        try:
            self.raw_faiss_index.add_with_ids(vector_np, ids_np)
            logger.debug(f"Added embedding for node {node.id} with FAISS ID {faiss_id}")
        except Exception as e:
            logger.error(f"FAISS add_with_ids failed for node {node.id} (FAISS ID {faiss_id}): {e}", exc_info=True)
            # Should we revert the ID mapping if add fails?
            # For now, log the error and continue, but the mappings might be inconsistent.
            return
        
        # === Update Langchain Docstore ===
        # Create/update the Document object for Langchain's docstore
        # This ensures metadata filtering works correctly with Langchain methods
        # and keeps the docstore consistent with the raw index.
        doc_metadata = node.metadata.copy() if node.metadata else {}
        # Add coordinate info to the document metadata
        doc_metadata["coord_r"] = node.coordinates.r
        doc_metadata["coord_theta"] = node.coordinates.theta
        doc_metadata["coord_t"] = node.coordinates.t
        doc_metadata["coord_z"] = node.coordinates.z
        doc_metadata["coord_z_type"] = node.coordinates.z_type
        doc_metadata["node_type"] = node.type # Ensure node type is in metadata
        doc_metadata["timestamp"] = node.timestamp
        doc_metadata["keywords"] = ",".join(node.keywords) if node.keywords else ""
        # Add other potentially useful fields from Node
        doc_metadata["mapping_details"] = json.dumps(node.mapping_details) # Serialize dict
        if node.parent_node_id:
             doc_metadata["parent_node_id"] = node.parent_node_id

        # Determine page_content for the Document (use 'text' field if available)
        page_content = node.content.get('text', json.dumps(node.content))
        
        # Create the Langchain Document
        doc = Document(page_content=page_content, metadata=doc_metadata)
        
        # Add/update the document in the docstore using the node.id
        # and map the Langchain internal index ID to this node.id
        internal_docstore_id = node.id # Use node.id as the key for Langchain's docstore
        self.vector_store.docstore.add({internal_docstore_id: doc})
        
        # Map the FAISS integer ID (faiss_id) to the Langchain docstore ID (node.id)
        # Find the internal index (sequential ID) used by FAISS wrapper for the given faiss_id.
        # This mapping is tricky because Langchain's FAISS wrapper assumes sequential integer IDs
        # starting from 0 when adding documents via its own add_documents method.
        # Since we are using add_with_ids on the raw index, the Langchain wrapper's internal
        # index_to_docstore_id map might not naturally align with our faiss_id.
        
        # WORKAROUND: We directly manage the index_to_docstore_id map.
        # This map links the sequential index position (0, 1, 2...) assumed by Langchain 
        # search results to our node.id (which is used as the docstore key).
        # However, the raw FAISS index returns our custom `faiss_id` during search. 
        # There's a mismatch here. Langchain's standard FAISS assumes the index position
        # *is* the ID added, or maps it sequentially.
        
        # Let's update index_to_docstore_id assuming the size implies the next sequential index.
        # This relies on the assumption that adds happen sequentially, which is true
        # with our self.next_faiss_id counter *if* no deletes occur or IDs are reused.
        current_lc_index_count = len(self.vector_store.index_to_docstore_id)
        # Check if the faiss_id matches the expected next sequential ID
        # If not, log a warning, as Langchain search might return unexpected docstore IDs
        if faiss_id != current_lc_index_count:
            logger.warning(f"FAISS ID {faiss_id} does not match expected next Langchain index {current_lc_index_count}. Langchain search results mapping might be inconsistent.")
            # Option: Try to find an existing entry for faiss_id and update? Risky.
            # Option: Force the mapping anyway? Might overwrite existing map entry.
        
        # Update the mapping - associating the current sequential position with the node.id
        self.vector_store.index_to_docstore_id[current_lc_index_count] = internal_docstore_id
        # logger.debug(f"Updated Langchain index_to_docstore_id: map[{current_lc_index_count}] = {internal_docstore_id}")
        # === End Update Langchain Docstore ===

    def add_node(self,
                 node_id: str,
                 content: Dict[str, Any],
                 embedding: Optional[np.ndarray],
                 metadata: Dict,
                 coordinates: PolarTemporalCoordinate,
                 keywords: Optional[List[str]],
                 mapping_details: Dict,
                 parent_node_id: Optional[str] = None,
                 explicit_timestamp: Optional[float] = None
                ) -> str:
        """
        Adds a node to the Narrative Atlas, storing it in the DB and adding/updating
        its embedding in the vector store with coordinates in metadata.

        Args:
            node_id: Unique ID for the new node.
            content: Dictionary representing the node's primary content (e.g., {'text': '...'}).
            embedding: Pre-computed embedding (numpy array).
            metadata: Dictionary containing structural info (page_number, chunk_index_on_page, etc.)
                      and any other relevant metadata.
            coordinates: Pre-calculated PolarTemporalCoordinate object for the node.
            keywords: List of extracted keywords for the node.
            mapping_details: Dictionary describing how coordinates were mapped.
            parent_node_id: Optional ID of the parent node for structural linking.
            explicit_timestamp: Optional timestamp to override node creation time.

        Returns:
            The ID of the added node.
        """
        print(f"--- NARRATIVE ATLAS: ADDING NODE {node_id} ---") # DEBUG
        # Validate coordinates
        if not isinstance(coordinates, PolarTemporalCoordinate):
            raise TypeError(f"Expected PolarTemporalCoordinate for coordinates, got {type(coordinates)}")

        # Create Node object
        timestamp = explicit_timestamp if explicit_timestamp is not None else time.time()
        node_obj = Node(
            id=node_id,
            type=metadata.get("node_type", "unknown"), # Extract type from metadata if possible
            content=content,
            coordinates=coordinates, # Store the coordinate object
            embedding=embedding, # Store the embedding (can be None)
            keywords=keywords,
            metadata=metadata, # Store original metadata
            parent_node_id=parent_node_id,
            timestamp=timestamp,
            mapping_details=mapping_details
        )

        # Store node data in the spatial-temporal DB
        self.db.nodes[node_id] = node_obj
        print(f"--- NARRATIVE ATLAS: Node {node_id} added to self.db.nodes ---") # DEBUG

        # Add/update embedding in the vector store
        # Determine text to embed (e.g., from content['text'])
        text_for_embedding = content.get("text", json.dumps(content)) # Fallback to json
        if text_for_embedding or embedding is not None: # Only add if there's text or precomputed embedding
             self._add_or_update_embedding(node=node_obj, text_to_embed=text_for_embedding, precomputed_embedding=embedding)
        else:
             print(f"Warning: Node {node_id} has no text content or precomputed embedding; skipping vector store add.")

        print(f"--- NARRATIVE ATLAS: Finished adding node {node_id} ---") # DEBUG
        return node_id

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
        """Save the atlas data (DB nodes, FAISS index, ID maps)."""
        index_folder = os.path.join(self.storage_path)
        id_maps_path = os.path.join(self.storage_path, "id_maps.json")
        db_path = os.path.join(self.storage_path, "spatial_temporal_db.pkl") # Path for SpatialTemporalDB data

        os.makedirs(index_folder, exist_ok=True)
        
        try:
            # Save FAISS index
            if self.vector_store:
                self.vector_store.save_local(folder_path=index_folder, index_name="index")
            
            # Save ID maps
            with open(id_maps_path, 'w') as f:
                json.dump({
                    'node_id_to_faiss_id': self.node_id_to_faiss_id,
                    'faiss_id_to_node_id': self.faiss_id_to_node_id
                }, f)
            
            # Save SpatialTemporalDB nodes (simple pickle for now)
            with open(db_path, 'wb') as f:
                pickle.dump(self.db.nodes, f)
                
            print(f"Narrative Atlas saved successfully to {self.storage_path}")

        except Exception as e:
            print(f"Error saving Narrative Atlas: {e}")
            raise

    def load(self):
        """Load the atlas data (DB nodes, FAISS index, ID maps)."""
        # Note: Loading of FAISS index and ID maps happens in _initialize_vector_store
        # We only need to load the SpatialTemporalDB nodes here.
        db_path = os.path.join(self.storage_path, "spatial_temporal_db.pkl")
        
        if os.path.exists(db_path):
            try:
                with open(db_path, 'rb') as f:
                    self.db.nodes = pickle.load(f)
                print(f"Loaded SpatialTemporalDB nodes from {db_path}. Count: {len(self.db.nodes)}")
            except Exception as e:
                print(f"Error loading SpatialTemporalDB nodes: {e}. Starting with empty DB.")
                self.db.nodes = {}
        else:
             print(f"SpatialTemporalDB file not found at {db_path}. Starting with empty DB.")
             self.db.nodes = {}
             
        # Re-initialize vector store to load FAISS index and ID maps
        # This ensures consistency after loading the DB nodes
        self._initialize_vector_store()

    def clear(self):
        """Clears the database, vector index, and mappings, and removes persisted files."""
        print(f"Clearing Narrative Atlas data in {self.storage_path}...")
        
        # 1. Clear in-memory data
        self.db.nodes = {}
        self.node_id_to_faiss_id = {}
        self.faiss_id_to_node_id = {}
        
        # 2. Reset FAISS index to a new empty one
        print("Resetting FAISS index...")
        self.raw_faiss_index, self.vector_store = self._create_new_hnsw_index()
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
        # 1. Remove from DB
        if node_id not in self.db.nodes:
            return False
        del self.db.nodes[node_id]

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

    def _get_ids_matching_filters(self, filters: CoordinateFilters) -> Optional[List[str]]:
        """
        Filters node IDs based on coordinate ranges (r, theta, t, z) and z_type.
        Returns a list of node IDs that match the filters, or None if no store.
        """
        if self.vector_store is None:
            logger.warning("Vector store not initialized, cannot filter IDs.")
            return None
        
        matching_ids = []
        # Check if docstore exists and has the _dict attribute
        if not hasattr(self.vector_store.docstore, '_dict'):
            logger.warning("Docstore is not the expected InMemoryDocstore or lacks _dict.")
            return []
            
        # Iterate through the Langchain docstore to access metadata
        for node_id, doc in self.vector_store.docstore._dict.items():
            # Ensure doc has metadata
            if not hasattr(doc, 'metadata') or not isinstance(doc.metadata, dict):
                logger.debug(f"Skipping node {node_id} due to missing or invalid metadata.")
                continue
            
            metadata = doc.metadata
            match = True # Assume match initially
            
            # Retrieve coordinates from metadata
            coord_r = metadata.get('coord_r')
            coord_theta = metadata.get('coord_theta')
            coord_t = metadata.get('coord_t')
            coord_z = metadata.get('coord_z')
            coord_z_type = metadata.get('coord_z_type')
            
            # --- Apply Filters --- 
            # R filter
            if filters.r_min is not None and (coord_r is None or coord_r < filters.r_min):
                match = False
            if match and filters.r_max is not None and (coord_r is None or coord_r > filters.r_max):
                match = False
                
            # T filter
            if match and filters.t_min is not None and (coord_t is None or coord_t < filters.t_min):
                match = False
            if match and filters.t_max is not None and (coord_t is None or coord_t > filters.t_max):
                match = False
                
            # Theta filter (handle wraparound if necessary - simple check here)
            if match and filters.theta_min is not None and (coord_theta is None or coord_theta < filters.theta_min):
                 match = False # Simplified check, assumes no range wraps around 2pi
            if match and filters.theta_max is not None and (coord_theta is None or coord_theta > filters.theta_max):
                 match = False # Simplified check
                 
            # Z filter
            if match and filters.z_min is not None and (coord_z is None or coord_z < filters.z_min):
                 match = False
            if match and filters.z_max is not None and (coord_z is None or coord_z > filters.z_max):
                 match = False
                 
            # Z Type filter
            if match and filters.z_type is not None and (coord_z_type is None or coord_z_type != filters.z_type):
                 match = False
            # --- End Filters --- 
            
            if match:
                matching_ids.append(node_id)
                
        logger.info(f"Filter matched {len(matching_ids)} nodes out of {len(self.vector_store.docstore._dict)} total.")
        return matching_ids
    
    def search_with_nl_query(self, nl_query: str, k: int = 10) -> List[Tuple[Node, float]]:
        """Processes a natural language query, applies coordinate filters, 
           and performs vector search on the filtered results.

        Args:
            nl_query: The natural language query string.
            k: The maximum number of final results to return after filtering and ranking.

        Returns:
            A list of (Node, score) tuples representing the final ranked results.
        """
        print(f"--- NARRATIVE ATLAS: Starting NL Query Search for: '{nl_query}' with k={k} ---")
        
        # 1. Parse the Natural Language Query
        try:
            parsed_params: ParsedQuery = self.nl_parser.parse(nl_query)
            print(f"--- NARRATIVE ATLAS: Parsed Query Params: {parsed_params} ---")
        except Exception as e:
            print(f"Error parsing NL query: {e}. Returning empty results.")
            # logger.error(f"Error parsing NL query '{nl_query}': {e}", exc_info=True)
            return []

        # 2. Get Candidate IDs matching Coordinate Filters
        # This returns None if no filters are specified, meaning use all docs.
        candidate_doc_ids: Optional[List[str]] = self._get_ids_matching_filters(parsed_params.filters)
        
        if candidate_doc_ids is not None and not candidate_doc_ids:
            print("--- NARRATIVE ATLAS: No documents matched coordinate filters. Returning empty results. ---")
            return [] # No candidates survived filtering

        # 3. Perform Vector Search (Potentially Restricted)
        query_embedding = self.embedding_service.embed_query(parsed_params.query_text)
        
        # Prepare for FAISS search
        # FAISS similarity_search_with_score_by_vector expects the vector itself.
        # We need a way to filter by the `candidate_doc_ids`.
        # Langchain's default FAISS wrapper doesn't directly support filtering by arbitrary IDs during search.
        # We might need to retrieve a larger set and then filter *after* the similarity search,
        # or potentially use a more advanced FAISS feature/wrapper if available.

        # --- Option A: Search broadly, then filter (Simpler for now) ---
        # Retrieve more results initially to account for filtering post-search
        initial_k = k * 5 # Heuristic: Retrieve more initially
        if candidate_doc_ids:
            # If we have candidates, maybe fetch even more initially?
            # This is inefficient but works with current LC FAISS limitations.
            initial_k = max(initial_k, len(candidate_doc_ids)) 
        
        print(f"--- NARRATIVE ATLAS: Performing initial vector search with k={initial_k} ---")
        try:
            # Use similarity_search_by_vector_with_scores if embedding is precomputed
            initial_docs_with_scores = self.vector_store.similarity_search_by_vector_with_relevance_scores(
                embedding=query_embedding,
                k=initial_k
            )
            print(f"--- NARRATIVE ATLAS: Initial vector search returned {len(initial_docs_with_scores)} results ---")
        except Exception as e:
            print(f"Error during initial vector search: {e}. Returning empty results.")
            # logger.error(f"Error during vector search for '{parsed_params.query_text}': {e}", exc_info=True)
            return []

        # --- Filter the initial results based on candidate_doc_ids (if applicable) ---
        filtered_results_with_scores = []
        if candidate_doc_ids is None: # No coordinate filtering was done
            filtered_results_with_scores = initial_docs_with_scores
        else:
            candidate_set = set(candidate_doc_ids)
            for doc, score in initial_docs_with_scores:
                doc_id = doc.metadata.get("id") # Langchain FAISS might store the ID here
                if doc_id and doc_id in candidate_set:
                     filtered_results_with_scores.append((doc, score))
            print(f"--- NARRATIVE ATLAS: Filtered vector search results down to {len(filtered_results_with_scores)} based on coordinate filters ---")

        # --- Limit to final k and format results ---
        final_results = []
        # Sort by score (relevance scores: higher is better, distances: lower is better - check score type)
        # Assuming similarity_search_..._relevance_scores returns higher=better
        # Sort descending by score
        filtered_results_with_scores.sort(key=lambda item: item[1], reverse=True) 
        
        for doc, score in filtered_results_with_scores[:k]: # Take top k
            node_id = doc.metadata.get("node_id")
            if node_id and node_id in self.db.nodes:
                final_results.append((self.db.nodes[node_id], float(score)))
            elif node_id:
                 print(f"Warning: Found node_id {node_id} in final results but not in DB.")
            else:
                 print(f"Warning: Final result metadata missing 'node_id': {doc.metadata}")

        print(f"--- NARRATIVE ATLAS: Returning {len(final_results)} final results for NL Query ---")
        return final_results

    def answer_query_with_context(self, user_query: str, k: int = 3) -> str:
        """Find relevant nodes, format context, and construct a prompt for RAG.

        Args:
            user_query: The user's question.
            k: The number of relevant nodes to retrieve.

        Returns:
            A string containing the formatted context and the prompt for an LLM,
            or a message indicating no context was found.
        """
        # 1. Retrieve Context
        similar_nodes = self.find_similar_nodes(query_text=user_query, k=k)

        # 2. Handle Empty Context
        if not similar_nodes:
            return "No relevant context found for your query."

        # 3. Format Context
        formatted_context = """
--- CONTEXT START ---
"""
        for node, score in similar_nodes:
            formatted_context += f"\nNode Type: {node.type}\n"
            formatted_context += f"Node ID: {node.id}\n"
            content_str = json.dumps(node.content, indent=2)
            formatted_context += f"Content:\n{content_str}\n"
            formatted_context += f"Temporal Coordinate: {node.coordinates['t']}\n"
            #formatted_context += f"(Similarity Score: {score:.4f})\n"
            formatted_context += "---"
        
        formatted_context += "\n--- CONTEXT END ---"

        # 4. Construct Prompt
        prompt = f"""
Based ONLY on the following context:
{formatted_context}

Answer the question: {user_query}
"""

        # 5. LLM Call (Placeholder) - Return the prompt for now
        # llm_response = llm_client.generate(prompt) # Example placeholder
        # return llm_response
        
        return prompt 