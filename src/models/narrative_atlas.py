import os
import json
import faiss
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import FakeEmbeddings
from langchain_community.docstore.in_memory import InMemoryDocstore
from src.models.spatial_temporal_db import SpatialTemporalDB, Node

@dataclass
class Node:
    id: str
    type: str
    content: dict
    temporal_coordinate: float
    spatial_coordinates: List[float]

class NarrativeAtlas:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.db = SpatialTemporalDB()
        self.embedding_dim = 384  # Default embedding dimension
        self.embeddings = FakeEmbeddings(size=self.embedding_dim)
        self.vector_store: Optional[FAISS] = None
        self.node_id_to_doc_id: Dict[str, str] = {}
        self.doc_id_to_node_id: Dict[str, str] = {}
        
        # Initialize vector store
        self._initialize_vector_store()
    
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
        
        # Wrap with IndexIDMap2
        new_faiss_index = faiss.IndexIDMap2(base_index)
        
        # Create an empty docstore
        docstore = InMemoryDocstore()
        
        # Initialize the LangChain FAISS wrapper
        vector_store = FAISS(
            embedding_function=self.embeddings,
            index=new_faiss_index,
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
                    embeddings=self.embeddings,
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
        """Get or create a character node."""
        node_id = f"character_{name.lower().replace(' ', '_')}"
        if node_id not in self.db.nodes:
            node = Node(
                id=node_id,
                type="character",
                content={"name": name},
                temporal_coordinate=temporal_coordinate,
                spatial_coordinates=[0.0, 0.0, 0.0]
            )
            self.db.nodes[node_id] = node
            # Refined text for embedding: Just the name for now
            text_to_embed = f"Character: {name}"
            self._add_or_update_embedding(node, text_to_embed)
        return node_id
    
    def _create_event(self, description: str, temporal_coordinate: float, participant_ids: List[str]) -> str:
        """Create an event node."""
        node_id = f"event_{description.lower().replace(' ', '_')}"
        node = Node(
            id=node_id,
            type="event",
            content={"description": description, "participants": participant_ids},
            temporal_coordinate=temporal_coordinate,
            spatial_coordinates=[0.0, 0.0, 0.0]
        )
        self.db.nodes[node_id] = node
        # Refined text for embedding: Description + Participant Names
        participant_names = []
        for p_id in participant_ids:
            if p_id in self.db.nodes and self.db.nodes[p_id].type == "character":
                participant_names.append(self.db.nodes[p_id].content.get("name", "Unknown"))
        
        text_to_embed = f"Event: {description}"
        if participant_names:
            text_to_embed += f"\nParticipants: {', '.join(participant_names)}"
            
        self._add_or_update_embedding(node, text_to_embed)
        return node_id
    
    def _get_or_create_location(self, name: str, temporal_coordinate: float) -> str:
        """Get or create a location node."""
        node_id = f"location_{name.lower().replace(' ', '_')}"
        if node_id not in self.db.nodes:
            node = Node(
                id=node_id,
                type="location",
                content={"name": name},
                temporal_coordinate=temporal_coordinate,
                spatial_coordinates=[0.0, 0.0, 0.0]
            )
            self.db.nodes[node_id] = node
            # Refined text for embedding: Just the name for now
            text_to_embed = f"Location: {name}"
            self._add_or_update_embedding(node, text_to_embed)
        return node_id
    
    def _add_or_update_embedding(self, node: Node, text_to_embed: Optional[str] = None):
        """Add or update a node's embedding in the vector store."""
        # If specific text isn't provided, create a default one
        if text_to_embed is None:
             text_to_embed = node.content.get('name', '') or node.content.get('description', '')
             if node.type == "character": text_to_embed = f"Character: {text_to_embed}"
             elif node.type == "event": text_to_embed = f"Event: {text_to_embed}"
             elif node.type == "location": text_to_embed = f"Location: {text_to_embed}"
        
        if node.id in self.node_id_to_doc_id:
            # Update existing embedding
            doc_id = self.node_id_to_doc_id[node.id]
            # Remove old document
            self.vector_store.delete([doc_id])
            del self.node_id_to_doc_id[node.id]
            del self.doc_id_to_node_id[doc_id]
        
        # Add new document
        doc_id = f"doc_{node.id}"
        self.vector_store.add_texts(
            texts=[text_to_embed],
            metadatas=[{"id": doc_id}]
        )
        self.node_id_to_doc_id[node.id] = doc_id
        self.doc_id_to_node_id[doc_id] = node.id
    
    def find_similar_nodes(self, query_text: str, k: int = 5) -> List[Tuple[Node, float]]:
        """Find nodes similar to the query text."""
        # Search the vector store
        docs = self.vector_store.similarity_search_with_score(query_text, k=k)
        
        # Convert results to nodes
        results = []
        for doc, score in docs:
            doc_id = doc.metadata["id"]
            if doc_id in self.doc_id_to_node_id:
                node_id = self.doc_id_to_node_id[doc_id]
                node = self.db.nodes[node_id]
                results.append((node, float(score)))
        
        return results
    
    def save(self):
        """Save the vector store and ID maps."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save vector store
        self.vector_store.save_local(self.storage_path)
        
        # Save ID maps
        with open(os.path.join(self.storage_path, "id_maps.json"), 'w') as f:
            json.dump({
                'node_id_to_doc_id': self.node_id_to_doc_id,
                'doc_id_to_node_id': self.doc_id_to_node_id
            }, f)
    
    def load(self):
        """Load the vector store and ID maps."""
        self._initialize_vector_store()

    def delete_node(self, node_id: str) -> bool:
        """Delete a node from the database, vector store, and ID maps.

        Args:
            node_id: The ID of the node to delete.

        Returns:
            True if the node was found and deletion was successful (or attempted), False otherwise.
        """
        # 1. Delete from the core database
        if not self.db.delete_node(node_id):
            print(f"Node {node_id} not found in database.")
            return False

        # 2. Delete from FAISS vector store and ID maps
        if node_id in self.node_id_to_doc_id:
            doc_id = self.node_id_to_doc_id[node_id]
            
            # Remove from FAISS index
            if self.vector_store:
                try:
                    success = self.vector_store.delete([doc_id])
                    if not success:
                         print(f"Warning: Failed to delete doc_id {doc_id} from vector store for node {node_id}.")
                except Exception as e:
                    print(f"Error deleting doc_id {doc_id} from vector store: {e}")
            
            # Remove from ID maps
            del self.node_id_to_doc_id[node_id]
            if doc_id in self.doc_id_to_node_id:
                 del self.doc_id_to_node_id[doc_id]
            
            print(f"Node {node_id} (doc_id {doc_id}) removed from vector store and maps.")
            return True
        else:
            print(f"Node {node_id} not found in vector store ID maps. Only removed from DB.")
            # Return True because it was successfully removed from the DB
            return True

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