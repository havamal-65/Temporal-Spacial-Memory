"""
Ingestion Pipeline Service

This module provides the main ingestion pipeline for processing documents into the 4D polar-temporal database.
It orchestrates document loading, chunking, entity extraction, and coordinate mapping.
"""

import os
import logging
import time
import uuid
import dotenv
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np

# Import LLM and Pydantic for structural analysis
from langchain_openai import ChatOpenAI
# Using V1BaseModel consistent with NlQueryParser in this project
from pydantic.v1 import BaseModel as V1BaseModel, Field as V1Field 

# Local imports
from src.utils.document_loader import DocumentLoader
from src.utils.text_chunker import TextChunker
from src.utils.entity_extractor import EntityExtractor
from src.utils.coordinate_mapper import CoordinateMapper
from src.utils.embedding_service import create_embedding_service
# Import NarrativeAtlas
from src.models.narrative_atlas import NarrativeAtlas
from src.models.polar_temporal_coordinate import PolarTemporalCoordinate # Import needed for updates
from src.services.steward_analyzer import StewardAnalyzer # <-- Added import

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('IngestionPipeline')


# --- Schema for LLM Structural Analysis Output ---
class StructuralMetadata(V1BaseModel):
    """Schema for extracting structural elements from a text chunk."""
    perspective: Optional[str] = V1Field(None, description="Identify the narrator's perspective or viewpoint, if explicitly different from the main narrative (e.g., 'Character A's view', 'Author's note').")
    layer_type: Optional[str] = V1Field(None, description="Classify the chunk's role if it deviates from the main narrative flow (e.g., 'FOOTNOTE', 'COMMENTARY', 'APPENDIX', 'MAIN'). Default to 'MAIN' if unsure.")
    version: Optional[str] = V1Field(None, description="Identify if this chunk represents a specific version or draft, if indicated (e.g., 'Draft 1', 'Final Version').")
    abstraction_level: Optional[str] = V1Field(None, description="Determine if this chunk is a summary or abstract of other content (e.g., 'SUMMARY', 'ABSTRACT', 'DETAILED'). Default to 'DETAILED'.")
    # Add other potential structural elements as needed based on analysis


class IngestionPipeline:
    """
    Pipeline for ingesting documents into the 4D polar-temporal database.
    """
    
    def __init__(self, 
                narrative_atlas: NarrativeAtlas, 
                input_dir: str = 'input',
                output_dir: str = 'output',
                chunk_size: int = None,
                chunk_overlap: int = None,
                embedding_service_type: str = None,
                embedding_model_name: str = None,
                embedding_cache_size: int = None):
        """
        Initialize the ingestion pipeline.
        
        Args:
            narrative_atlas: Instance of NarrativeAtlas for storage and indexing
            input_dir: Directory for input documents
            output_dir: Directory for processed output
            chunk_size: Maximum size of text chunks
            chunk_overlap: Overlap between chunks
            embedding_service_type: Type of embedding service ('mock', 'langchain', or 'cascading')
            embedding_model_name: Name of the embedding model (if using langchain)
            embedding_cache_size: Size of the embedding cache (if using langchain)
        """
        self.narrative_atlas = narrative_atlas 
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # Load configuration from environment variables, with fallbacks
        self.chunk_size = chunk_size or int(os.getenv('CHUNK_SIZE', 1000))
        self.chunk_overlap = chunk_overlap or int(os.getenv('CHUNK_OVERLAP', 200))
        embedding_service_type = embedding_service_type or os.getenv('EMBEDDING_SERVICE_TYPE', 'mock')
        embedding_model_name = embedding_model_name or os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
        embedding_cache_size = embedding_cache_size or int(os.getenv('EMBEDDING_CACHE_SIZE', 1000))
        
        # --- LLM for Structural Analysis ---
        # Ensure API key is loaded (should be done at entry point or via dotenv)
        if not os.getenv("OPENAI_API_KEY"):
             # Consider raising an error or logging a warning depending on whether analysis is critical
             logger.warning("OPENAI_API_KEY not set. Structural analysis via LLM will be skipped.")
             self.structural_analysis_llm = None
             self.structural_analysis_runnable = None
             self.steward_analyzer = None # <-- Initialize as None here too
        else:
             # Using a capable but potentially faster/cheaper model for chunk analysis if possible
             self.structural_analysis_llm = ChatOpenAI(model=os.getenv("STRUCTURAL_ANALYSIS_MODEL", "gpt-3.5-turbo"), temperature=0) 
             # Create the runnable using the Pydantic schema
             self.structural_analysis_runnable = self.structural_analysis_llm.with_structured_output(StructuralMetadata)
             # Initialize StewardAnalyzer here as well, using the designated model
             self.steward_analyzer = StewardAnalyzer(llm_model=os.getenv("STEWARD_ANALYSIS_MODEL", "gpt-4o")) # <-- Initialize StewardAnalyzer
        # --- End LLM Setup ---
        
        logger.info(f"Using embedding service: {embedding_service_type}, model: {embedding_model_name}")
        
        # Create directories if they don't exist
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components
        self.document_loader = DocumentLoader()
        self.text_chunker = TextChunker()
        self.entity_extractor = EntityExtractor()
        
        # Initialize embedding service with appropriate parameters
        kwargs = {}
        if embedding_service_type == 'langchain':
            kwargs['model_name'] = embedding_model_name
            kwargs['cache_size'] = embedding_cache_size
            
        self.embedding_service = create_embedding_service(
            service_type=embedding_service_type,
            **kwargs
        )
        
        # Initialize coordinate mapper
        self.coordinate_mapper = CoordinateMapper(
            embedding_service=self.embedding_service,
        )
        
        # Statistics for tracking ingestion
        self.stats = {
            'documents_processed': 0,
            'total_chunks_created': 0,
            'entities_extracted': 0,
            'errors': 0,
            'processing_time': 0
        }
        
        logger.info(f"Initialized ingestion pipeline with input_dir='{input_dir}', output_dir='{output_dir}'")
    
    def ingest_document(self, file_path: str) -> bool:
        """
        Process a single document through the full ingestion pipeline.
        Handles multi-page documents (like PDFs) by processing page by page.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            True if processing was successful, False otherwise
        """
        start_time = time.time()
        total_chunks_in_doc = 0
        
        try:
            logger.info(f"Starting ingestion of document: {file_path}")
            
            # Step 1: Load the document (returns list of pages/docs)
            pages = self.document_loader.load_document(file_path)
            if not pages:
                logger.warning(f"No content loaded from document: {file_path}")
                return False # Indicate failure if no pages loaded
            
            all_processed_chunks = [] # Collect chunks from all pages
            phase1_results = [] # <-- Initialize list to store phase 1 data for Steward LLM
            
            # --- Process Page by Page ---
            for page_data in pages:
                page_content = page_data['content']
                page_metadata = page_data['metadata']
                page_number = page_metadata.get('page_number', 0) # Get page number (0 if not PDF)
                
                if not page_content:
                    logger.debug(f"Skipping empty page {page_number} in {file_path}")
                    continue
                
                # Step 2: Split the current page content into chunks
                page_chunks = self.text_chunker.chunk_text(
                    text=page_content,
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    metadata=page_metadata # Pass page metadata to chunker
                )
                
                # Add page-specific chunk index to each chunk's metadata
                for i, chunk in enumerate(page_chunks):
                    chunk['metadata']['chunk_index_on_page'] = i # 0-based index within the page
                    all_processed_chunks.append(chunk) # Add to the overall list
            
            total_chunks_in_doc = len(all_processed_chunks)
            self.stats['total_chunks_created'] += total_chunks_in_doc # Update total count
            logger.info(f"Document '{os.path.basename(file_path)}' split into {total_chunks_in_doc} chunks across {len(pages)} pages.")
            
            # --- Process All Chunks for the Document ---
            if not all_processed_chunks:
                logger.warning(f"No chunks generated for document: {file_path}")
                return False # Indicate failure if no chunks generated
            
            for chunk_data in all_processed_chunks:
                chunk_content = chunk_data['content']
                chunk_metadata = chunk_data['metadata']
                chunk_idx_on_page = chunk_metadata.get('chunk_index_on_page', -1) # Retrieve chunk index
                
                # === START: Step 2.5 - Structural Analysis using LLM ===
                if self.structural_analysis_runnable:
                    try:
                        # Define a simple prompt (can be refined)
                        prompt = f"Analyze the following text chunk and identify its structural role based on the provided schema. Focus on perspective shifts, explicit layers (like footnotes), versions, or abstraction levels mentioned in the text itself.\n\nText Chunk:\n{chunk_content[:1500]} # Limit context sent to LLM if needed"
                        
                        logger.debug(f"Running structural analysis for chunk {chunk_idx_on_page}...")
                        structured_output = self.structural_analysis_runnable.invoke(prompt)
                        logger.debug(f"Structural analysis raw output: {structured_output}")

                        # Add extracted metadata to the chunk's metadata dictionary
                        if isinstance(structured_output, StructuralMetadata):
                            chunk_metadata['structural_perspective'] = structured_output.perspective
                            # Use a specific prefix to avoid potential key collisions
                            chunk_metadata['structural_layer_type'] = structured_output.layer_type if structured_output.layer_type else 'MAIN' # Default to MAIN
                            chunk_metadata['structural_version'] = structured_output.version
                            chunk_metadata['structural_abstraction_level'] = structured_output.abstraction_level if structured_output.abstraction_level else 'DETAILED' # Default to DETAILED
                            # Add others as needed
                            logger.debug(f"Updated chunk metadata with structural info: {chunk_metadata}")
                        else:
                            logger.warning(f"Structural analysis did not return expected StructuralMetadata object for chunk {chunk_idx_on_page}. Type was: {type(structured_output)}")
                    except Exception as e:
                        logger.error(f"Error during structural analysis for chunk {chunk_idx_on_page}: {e}", exc_info=True)
                        self.stats['errors'] += 1
                        # Assign default values if analysis fails?
                        chunk_metadata['structural_layer_type'] = 'MAIN' # Default
                        chunk_metadata['structural_abstraction_level'] = 'DETAILED' # Default
                else:
                    # If LLM is not configured, assign defaults
                    logger.debug("Structural analysis LLM not configured, assigning defaults.")
                    chunk_metadata['structural_layer_type'] = 'MAIN'
                    chunk_metadata['structural_abstraction_level'] = 'DETAILED'
                # === END: Step 2.5 - Structural Analysis using LLM ===
                
                # --- New Node ID Logic ---
                fragment_id = chunk_metadata.get('fragment_id')
                file_stem = Path(file_path).stem

                if fragment_id:
                    # If fragment_id exists (likely from JSON), use it for uniqueness
                    # Include chunk index if a fragment spans multiple chunks
                    node_id = f"frag_{fragment_id}_c{chunk_idx_on_page}"
                else:
                    # Fallback for non-JSON files or files without fragment_id
                    page_num = chunk_metadata.get('page_number', 0)
                    node_id = f"{file_stem}_p{page_num}_c{chunk_idx_on_page}"
                # --- End New Node ID Logic ---
                
                # === Store Phase 1 data for potential Steward Analysis ===
                phase1_results.append({
                    "node_id": node_id,
                    "metadata": chunk_metadata.copy(), # Store a copy of metadata
                    # Optional: Add chunk_content snippet if needed by Steward
                    "content_snippet": chunk_content[:200] # Example: first 200 chars
                })
                # === End Storing Phase 1 data ===
                
                # Step 3: Extract entities from the chunk (Optional - currently used for metadata)
                extracted_data = self.entity_extractor.extract_entities(chunk_content)
                
                # Count entities
                entity_count = (
                    len(extracted_data['entities']) + 
                    len(extracted_data['events']) + 
                    len(extracted_data['locations'])
                )
                self.stats['entities_extracted'] += entity_count
                
                # Step 4: Map to 4D coordinates (using the refactored CoordinateMapper)
                # This now primarily calculates structural coordinates and gets keywords.
                # It also requires the embedding to be passed in if pre-calculated,
                # or it can calculate it internally (though currently add_node does this).
                # Let's calculate the embedding here first.
                embedding_vector = self.embedding_service.embed_query(chunk_content)
                embedding_np = np.array(embedding_vector, dtype=np.float32)

                # Call the refactored mapper (mainly for keywords now, coords are calculated in add_node)
                mapping_result = self.coordinate_mapper.map_to_coordinates(
                    content=chunk_content,
                    metadata=chunk_metadata, # Pass AUGMENTED structural info
                    embedding=embedding_np # Pass embedding for completeness / potential future use
                )

                # Step 5: Add the node to the Narrative Atlas
                # Extract coordinates object and keywords from mapping result
                coordinates_obj = mapping_result.get('coordinate') # Get the PolarTemporalCoordinate object
                keywords_list = mapping_result.get('keywords', [])
                mapping_details_dict = mapping_result.get('mapping_details', {})
                
                # Ensure coordinates object exists before proceeding
                if coordinates_obj is None:
                    logger.error(f"Coordinate calculation failed for chunk {node_id}. Skipping node addition.")
                    self.stats['errors'] += 1
                    continue # Skip adding this node

                self.narrative_atlas.add_node(
                    node_id=node_id,
                    # Pass content as a dictionary with a 'text' key
                    content={'text': chunk_content}, 
                    embedding=embedding_np, # Use the pre-calculated embedding
                    metadata=chunk_metadata, # Pass AUGMENTED metadata
                    # Pass the PolarTemporalCoordinate object directly
                    coordinates=coordinates_obj, 
                    keywords=keywords_list, # Pass the list of keywords
                    mapping_details=mapping_details_dict, # Pass mapping details
                    parent_node_id=chunk_metadata.get('parent_node_id'), 
                    # Pass timestamp from metadata if available, otherwise None (add_node will handle default)
                    explicit_timestamp=chunk_metadata.get('timestamp') 
                    # context_layer is now derived from coordinates.z within add_node/Node creation
                )
            
            # Mark document as successfully processed
            self.stats['documents_processed'] += 1
            
            # Save processing time
            elapsed_time = time.time() - start_time
            self.stats['processing_time'] += elapsed_time
            
            logger.info(f"Successfully ingested document: {file_path} ({total_chunks_in_doc} chunks) in {elapsed_time:.2f} seconds")
            
            # === START: Step 5 - Steward LLM Reconfiguration ===
            if self.steward_analyzer and phase1_results:
                logger.info(f"Starting Steward LLM analysis for {len(phase1_results)} chunks in {os.path.basename(file_path)}...")
                try:
                    # Call the StewardAnalyzer to get reconfiguration suggestions
                    reconfiguration_updates = self.steward_analyzer.analyze_and_recommend_updates(phase1_results)
                    
                    if reconfiguration_updates and reconfiguration_updates.get("updates"):
                        updates_list = reconfiguration_updates["updates"]
                        logger.info(f"Steward LLM proposed {len(updates_list)} structural updates.")
                        
                        # Apply the updates
                        for update in updates_list:
                            node_id_to_update = update.get("node_id")
                            new_coords_dict = update.get("new_coordinates")
                            
                            if node_id_to_update and new_coords_dict:
                                try:
                                    # Create a new coordinate object from the dictionary
                                    # Ensure all required fields (r, theta, t, z, z_type) are present
                                    if all(k in new_coords_dict for k in ('r', 'theta', 't', 'z', 'z_type')):
                                        new_coordinate = PolarTemporalCoordinate(
                                            r=new_coords_dict['r'],
                                            theta=new_coords_dict['theta'],
                                            t=new_coords_dict['t'],
                                            z=new_coords_dict['z'],
                                            z_type=new_coords_dict['z_type']
                                        )
                                        
                                        # Call the actual update method directly now
                                        self.narrative_atlas.update_node_coordinates(node_id_to_update, new_coordinate)
                                        logger.debug(f"Applied Steward update to node {node_id_to_update}")
                                    else:
                                        logger.warning(f"Skipping update for node {node_id_to_update}: new_coordinates dictionary is missing required keys.")

                                except Exception as update_err:
                                    logger.error(f"Error applying Steward update to node {node_id_to_update}: {update_err}", exc_info=True)
                                    self.stats['errors'] += 1
                            else:
                                logger.warning(f"Skipping invalid update suggestion: {update}")
                    else:
                        logger.info("Steward LLM analysis completed, no updates proposed.")

                except Exception as steward_err:
                    logger.error(f"Error during Steward LLM analysis for document {file_path}: {steward_err}", exc_info=True)
                    self.stats['errors'] += 1
                    logger.warning("Skipping structural reconfiguration due to Steward LLM error. Using Phase 1 results.")
            elif not self.steward_analyzer:
                logger.info("Steward analyzer not configured. Skipping post-chunk reconfiguration.")
            # === END: Step 5 - Steward LLM Reconfiguration ===

            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest document {file_path}: {e}", exc_info=True)
            self.stats['errors'] += 1
            return False # Indicate failure
    
    def ingest_directory(self, directory: str = None) -> Dict[str, Any]:
        """
        Process all documents in a directory.
        
        Args:
            directory: Path to directory of documents (defaults to self.input_dir)
            
        Returns:
            Statistics dictionary with processing results
        """
        directory = directory or self.input_dir
        directory_path = Path(directory)
        
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return self.stats
        
        # Reset statistics
        self.stats = {
            'documents_processed': 0,
            'total_chunks_created': 0, # Use updated name
            'entities_extracted': 0,
            'errors': 0,
            'processing_time': 0,
            'files_attempted': 0,
            'files_skipped': 0
        }
        
        start_time = time.time()
        
        # Find all files in the directory
        for file_path in directory_path.glob('**/*'):
            if file_path.is_file():
                self.stats['files_attempted'] += 1
                
                # Check if the file extension is supported
                ext = file_path.suffix.lower()
                if ext not in self.document_loader.extension_mapping:
                    logger.warning(f"Skipping unsupported file type: {file_path}")
                    self.stats['files_skipped'] += 1
                    continue
                
                # Process the file - returns True/False
                success = self.ingest_document(str(file_path))
                if not success:
                    logger.warning(f"Failed to fully process document: {file_path}")
                    # Error already counted in ingest_document
        
        # Update total processing time
        self.stats['total_time'] = time.time() - start_time
        
        logger.info(f"Completed directory ingestion: {self.stats}")
        
        return self.stats
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current ingestion statistics.
        
        Returns:
            Statistics dictionary
        """
        return self.stats 