"""
Text Chunker Utility

This module provides utilities for splitting text documents into smaller chunks
for processing and storage in the 4D polar-temporal database.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TextChunker')


class TextChunker:
    """
    Class for splitting text documents into smaller chunks.
    """
    
    def __init__(self):
        """
        Initialize the text chunker.
        """
        pass
    
    def chunk_text(self, 
                  text: str, 
                  chunk_size: int = 1000, 
                  chunk_overlap: int = 200,
                  chunk_method: str = 'paragraph',
                  metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks.
        
        Args:
            text: The text content to split
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            chunk_method: Method to use for chunking ('paragraph', 'sentence', 'fixed')
            metadata: Metadata to include with each chunk
            
        Returns:
            List of dictionaries containing chunk content and metadata
        """
        if not text:
            logger.warning("Empty text provided to chunker")
            return []
        
        # Select chunking method
        if chunk_method == 'paragraph':
            chunks = self._chunk_by_paragraph(text, chunk_size, chunk_overlap)
        elif chunk_method == 'sentence':
            chunks = self._chunk_by_sentence(text, chunk_size, chunk_overlap)
        elif chunk_method == 'fixed':
            chunks = self._chunk_fixed_size(text, chunk_size, chunk_overlap)
        else:
            logger.warning(f"Unknown chunking method: {chunk_method}, using 'paragraph'")
            chunks = self._chunk_by_paragraph(text, chunk_size, chunk_overlap)
        
        # --- Calculate total chunks for this input text (page) --- 
        num_chunks_on_page = len(chunks)
        # --- End Calculation --- 
        
        # Create result with metadata
        result = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                'chunk_index': i,
                'total_chunks_on_page': num_chunks_on_page,
                'chunk_method': chunk_method,
                'chunk_size': len(chunk)
            }
            
            # Add provided metadata
            if metadata:
                chunk_metadata.update(metadata)
            
            result.append({
                'content': chunk,
                'metadata': chunk_metadata
            })
        
        return result
    
    def _chunk_by_paragraph(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Split text into chunks by paragraph boundaries.
        
        Args:
            text: Text to split
            chunk_size: Maximum chunk size
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Split text into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        
        return self._merge_splits(paragraphs, chunk_size, chunk_overlap)
    
    def _chunk_by_sentence(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Split text into chunks by sentence boundaries.
        
        Args:
            text: Text to split
            chunk_size: Maximum chunk size
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Simple sentence splitting (improved regex could be used)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        return self._merge_splits(sentences, chunk_size, chunk_overlap)
    
    def _chunk_fixed_size(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Split text into chunks of fixed size, regardless of content boundaries.
        
        Args:
            text: Text to split
            chunk_size: Maximum chunk size
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        chunks = []
        
        start = 0
        while start < len(text):
            # Calculate end position
            end = start + chunk_size
            
            # Add chunk
            chunks.append(text[start:end])
            
            # Move to next position, considering overlap
            start = end - chunk_overlap
        
        return chunks
    
    def _merge_splits(self, splits: List[str], chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Merge smaller text splits into chunks of appropriate size.
        
        Args:
            splits: List of text splits (paragraphs, sentences, etc.)
            chunk_size: Maximum chunk size
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of merged chunks
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        for split in splits:
            split_size = len(split)
            
            # If the split is larger than chunk_size, we need to handle it specially
            if split_size > chunk_size:
                # If we have content in current_chunk, add it to chunks
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Add the large split as its own chunk
                chunks.append(split)
                continue
            
            # If adding this split would exceed the chunk size, start a new chunk
            if current_size + split_size + len(current_chunk) > chunk_size:
                # Add current chunk to the list of chunks
                chunks.append(' '.join(current_chunk))
                
                # Calculate overlap
                overlap_splits = []
                overlap_size = 0
                
                # Add splits from the end of current chunk for overlap
                for s in reversed(current_chunk):
                    if overlap_size + len(s) > chunk_overlap:
                        break
                    overlap_splits.insert(0, s)
                    overlap_size += len(s) + 1  # +1 for space
                
                # Start a new chunk with the overlap
                current_chunk = overlap_splits
                current_size = overlap_size
            
            # Add the split to the current chunk
            current_chunk.append(split)
            current_size += split_size + (1 if current_chunk else 0)  # +1 for space
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks 