import os
import json
import faiss
import numpy as np
import shutil
import pickle
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.docstore.in_memory import InMemoryDocstore
from src.models.spatial_temporal_db import SpatialTemporalDB, Node
from src.utils.embedding_service import EmbeddingService
from src.utils.coordinate_mapper import CoordinateMapper
import time
import hashlib

@dataclass
class Node:
    id: str
    type: str
    content: dict
    temporal_coordinate: float
    spatial_coordinates: List[float]

class NarrativeAtlas:
    def __init__(self, storage_path: str, embedding_service: EmbeddingService):
        self.storage_path = storage_path
        self.db = SpatialTemporalDB()
        self.embedding_service = embedding_service
        self.coordinate_mapper = CoordinateMapper(
            embedding_service=self.embedding_service,
            default_chunk_layer=2,
            base_radius=0.9
        )
        self.embedding_dim = self.embedding_service.embedding_dim
        self.vector_store: Optional[FAISS] = None
        self.node_id_to_doc_id: Dict[str, str] = {}
        self.doc_id_to_node_id: Dict[str, str] = {}
        
        # Initialize vector store (loads FAISS index and ID maps if they exist)
        self._initialize_vector_store()
        
        # Explicitly load the DB nodes after initializing
        self.load()
    
    def _create_new_hnsw_index(self) -> FAISS:
        """Creates a new FAISS vector store with an HNSW index."""
        print("Creating new FAISS index with HNSW.")
        M = 32  # Number of connections for HNSW
        # ef_construction = 64 # Optional: Index build quality
        # ef_search = 32 # Optional: Search quality
        
        # Define the HNSW index
        base_index = faiss.IndexHNSWFlat(self.embedding_dim, M, faiss.METRIC_L2)
        # Optional: Set construction parameter
        # base_index.hnsw.efConstruction = ef_construction
        
        # --- Remove IndexIDMap2 wrapper --- 
        # new_faiss_index = faiss.IndexIDMap2(base_index)
        
        # Create an empty docstore
        docstore = InMemoryDocstore()
        
        # Initialize the LangChain FAISS wrapper using the base index
        vector_store = FAISS(
            embedding_function=self.embedding_service, 
            # Use the base HNSW index directly
            index=base_index, 
            docstore=docstore,
            index_to_docstore_id={}
        )
        # Optional: Set search parameter (can also be done per-search)
        # vector_store.index.hnsw.efSearch = ef_search
        return vector_store

    def _initialize_vector_store(self):
        """Initialize or load the FAISS vector store."""
        index_folder = os.path.join(self.storage_path)
        index_file = os.path.join(index_folder, "index.faiss") # Default Langchain FAISS file
        id_maps_path = os.path.join(self.storage_path, "id_maps.json")
        
        try:
            # Check if the specific index file exists, not just the folder
            if os.path.exists(index_file):
                print(f"Loading existing FAISS index from {index_folder}")
                self.vector_store = FAISS.load_local(
                    folder_path=index_folder,
                    embeddings=self.embedding_service,
                    index_name="index", # Langchain default index base name
                    allow_dangerous_deserialization=True
                )
                # Load ID maps
                if os.path.exists(id_maps_path):
                    with open(id_maps_path, 'r') as f:
                        maps = json.load(f)
                        self.node_id_to_doc_id = maps.get('node_id_to_doc_id', {})
                        self.doc_id_to_node_id = maps.get('doc_id_to_node_id', {})
                else:
                     print("Warning: Index found but id_maps.json missing.")
                     self.node_id_to_doc_id = {}
                     self.doc_id_to_node_id = {}

                # Optional: Configure HNSW search parameters on load if needed
                # if isinstance(self.vector_store.index, faiss.IndexHNSW):
                #    self.vector_store.index.hnsw.efSearch = 64
                
            else:
                # Create a new index if the file doesn't exist
                self.vector_store = self._create_new_hnsw_index()
                self.node_id_to_doc_id = {}
                self.doc_id_to_node_id = {}
                
        except Exception as e:
            print(f"Error loading or creating vector store: {e}. Creating new HNSW index.")
            # If any error occurs (loading or creating), fallback to creating a new index
            self.vector_store = self._create_new_hnsw_index()
            self.node_id_to_doc_id = {}
            self.doc_id_to_node_id = {}
    
    def _get_or_create_character(self, name: str, temporal_coordinate: float) -> str:
        """Get or create a character node (stores in DB only)."""
        node_id = f"character_{name.lower().replace(' ', '_')}"
        if node_id not in self.db.nodes:
            node = Node(
                id=node_id,
                type="character",
                content={"name": name},
                temporal_coordinate=temporal_coordinate,
                spatial_coordinates=[0.0, 0.0, 0.0] # Placeholder coords
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
            temporal_coordinate=temporal_coordinate,
            spatial_coordinates=[0.0, 0.0, 0.0] # Placeholder coords
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
                temporal_coordinate=temporal_coordinate,
                spatial_coordinates=[0.0, 0.0, 0.0] # Placeholder coords
            )
            self.db.nodes[node_id] = node
            # No call to _add_or_update_embedding here
        return node_id

    def _add_or_update_embedding(self,
                               node: Node,
                               text_to_embed: Optional[str] = None,
                               precomputed_embedding: Optional[np.ndarray] = None):
        """Add or update a node's embedding in the vector store."""
        # If specific text isn't provided, use node content
        if text_to_embed is None:
             # Assuming content dict has 'text' for chunks, or make generic
             text_to_embed = node.content.get('text', json.dumps(node.content))

        # Ensure text_to_embed is not empty for embedding calculation
        if not text_to_embed and precomputed_embedding is None:
            print(f"Warning: Cannot add embedding for node {node.id} with empty text and no precomputed embedding.")
            return

        doc_id_to_use = f"doc_{node.id}" # Use node ID for consistency
        # Basic metadata for FAISS doc
        metadata_for_doc = {"node_id": node.id, "node_type": node.type}

        # Check if node already exists in the vector store mappings
        existing_doc_id = self.node_id_to_doc_id.get(node.id)
        if existing_doc_id:
            # We ideally need a way to *update* vectors in FAISS via Langchain,
            # or delete and re-add. `add_texts` might handle overwrites if `ids` are stable.
            # For simplicity, we assume add_texts with the same ID updates or handles it.
            # If duplicates appear, a delete mechanism would be needed.
            print(f"Info: Node {node.id} might already exist in vector store (doc_id: {existing_doc_id}). Attempting update/add.")
            # Clean up old mapping just in case ID changed (shouldn't with doc_{node.id})
            del self.node_id_to_doc_id[node.id]
            if existing_doc_id in self.doc_id_to_node_id:
                del self.doc_id_to_node_id[existing_doc_id]

        # --- Add new document to FAISS --- 
        target_embedding: Optional[np.ndarray] = None
        if precomputed_embedding is not None:
            if isinstance(precomputed_embedding, list):
                target_embedding = np.array(precomputed_embedding, dtype=np.float32)
            else:
                 target_embedding = precomputed_embedding # Assume it's already ndarray
            # Ensure embedding has the correct shape (N, D)
            if target_embedding is not None and target_embedding.ndim == 1:
                target_embedding = np.expand_dims(target_embedding, axis=0)
        elif text_to_embed: # Only calculate if no precomputed one exists
            embedding_list = self.embedding_service.embed_query(text_to_embed)
            target_embedding = np.array(embedding_list, dtype=np.float32)
            if target_embedding.ndim == 1:
                 target_embedding = np.expand_dims(target_embedding, axis=0)
        else:
             print(f"Warning: Skipping embedding addition for node {node.id} due to missing text/embedding.")
             return # Don't update mappings if nothing was added

        # Add text and embedding using add_embeddings for direct control
        if target_embedding is not None and text_to_embed is not None:
             # Langchain's add_embeddings expects list of texts and list of embeddings
             # Correction: It likely expects a list of (text, embedding) tuples
             try:
                 # Ensure embedding is a list of floats
                 embedding_list = target_embedding.tolist()[0]
                 # Format as list of tuples: [(text, embedding)]
                 text_embedding_pair = (text_to_embed, embedding_list)
                 
                 # Use the explicit IDs feature
                 added_ids = self.vector_store.add_embeddings(
                     # Pass the list of (text, embedding) tuples
                     text_embeddings=[text_embedding_pair], 
                     metadatas=[metadata_for_doc],
                     ids=[doc_id_to_use]
                 )
                 # Update mappings only if addition seems successful
                 if added_ids and added_ids[0] == doc_id_to_use:
                      self.node_id_to_doc_id[node.id] = doc_id_to_use
                      self.doc_id_to_node_id[doc_id_to_use] = node.id
                 else:
                     # This case might indicate an issue with add_embeddings or ID handling
                     print(f"Warning: add_embeddings did not return expected ID for node {node.id}. Mappings not updated.")
             except Exception as e:
                 print(f"Error adding embedding for node {node.id} via add_embeddings: {e}")
        else:
             print(f"Warning: Could not add embedding for node {node.id} due to missing embedding or text.")

    def add_node(self,
                 node_id: str,
                 content: Dict[str, Any],
                 context_layer: int,
                 embedding: Optional[np.ndarray] = None,
                 metadata: Optional[Dict] = None,
                 parent_node_id: Optional[str] = None,
                 explicit_timestamp: Optional[float] = None
                ) -> str:
        """
        Adds a node to the database and vector store, calculating coordinates based on structure.

        Args:
            node_id: Unique ID for the new node.
            content: Dictionary representing the node's primary content (e.g., {'text': '...'}).
            context_layer: The explicit Z-layer for this node.
            embedding: Optional pre-computed embedding.
            metadata: Dictionary containing structural info (page_number, chunk_index_on_page, etc.)
                      and any other relevant metadata.
            parent_node_id: Optional ID of the parent node for structural linking (future use).
            explicit_timestamp: Optional timestamp to override sequential calculation.

        Returns:
            The ID of the added node.
        """
        if node_id in self.db.nodes:
             print(f"Warning: Node {node_id} already exists. Overwriting.")
             # Consider deleting old vector/node data first if needed

        # Ensure metadata exists
        if metadata is None:
            metadata = {}

        # 1. Ensure embedding exists (calculate if needed and not provided)
        final_embedding = embedding
        if final_embedding is None:
             text_to_embed = content.get('text', json.dumps(content)) # Get text or stringify dict
             if text_to_embed:
                 embedding_list = self.embedding_service.embed_query(text_to_embed)
                 final_embedding = np.array(embedding_list, dtype=np.float32)
             else:
                 print(f"Warning: Cannot generate embedding for node {node_id} due to missing content.")
                 # Assign a zero embedding? Or handle error?
                 final_embedding = np.zeros(self.embedding_dim, dtype=np.float32)

        # 2. Calculate Coordinates using CoordinateMapper (Phase 1 - Structural)
        # The mapper now primarily uses metadata for coordinate calculation
        # Pass content mainly for keyword extraction, pass the calculated embedding
        text_content_for_mapper = content.get('text', '') # Mapper might need text for keywords
        mapping_result = self.coordinate_mapper.map_to_coordinates(
            content=text_content_for_mapper,
            metadata=metadata, # Pass combined metadata (structural etc.)
            embedding=final_embedding # Pass embedding mainly for passthrough
        )
        new_coordinates = mapping_result['coordinate']

        # 3. Create Node Object
        # Combine core content with all metadata for storage in the node
        combined_content = {**content, **metadata, 'keywords': mapping_result['keywords']}

        node = Node(
            id=node_id,
            type=metadata.get('node_type', 'chunk'), # Get type from metadata or default
            content=combined_content,
            temporal_coordinate=new_coordinates.t,
            spatial_coordinates=[new_coordinates.r, new_coordinates.theta, new_coordinates.z]
        )
        self.db.nodes[node_id] = node

        # 4. Add/Update Embedding in Vector Store
        # Pass the node, its primary text content, and the embedding
        self._add_or_update_embedding(
            node=node,
            text_to_embed=content.get('text', json.dumps(content)), # Use primary text or stringified content
            precomputed_embedding=final_embedding
        )

        # Optional: Link to parent (for future graph operations)
        if parent_node_id and parent_node_id in self.db.nodes:
             # self.db.add_relationship(parent_node_id, node_id, type="SEQUENTIAL" or "BRANCH")
             pass # Requires SpatialTemporalDB to support relationships

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
                    'node_id_to_doc_id': self.node_id_to_doc_id,
                    'doc_id_to_node_id': self.doc_id_to_node_id
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
        self.node_id_to_doc_id = {}
        self.doc_id_to_node_id = {}
        
        # 2. Reset FAISS index to a new empty one
        print("Resetting FAISS index...")
        self.vector_store = self._create_new_hnsw_index()
        
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
        if node_id in self.node_id_to_doc_id:
            doc_id = self.node_id_to_doc_id[node_id]
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
            del self.node_id_to_doc_id[node_id]
            if doc_id in self.doc_id_to_node_id:
                 del self.doc_id_to_node_id[doc_id]
            
            return True
        else:
            print(f"Warning: Node {node_id} found in DB but not in FAISS mappings.")
            return True # Node deleted from DB, but vector inconsistency noted

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
            formatted_context += f"Temporal Coordinate: {node.temporal_coordinate}\n"
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