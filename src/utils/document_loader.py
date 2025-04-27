"""
Document Loader Utility

This module provides utilities for loading documents from various formats.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, BinaryIO
from pathlib import Path

# Document processing libraries
import pypdf
import docx2txt
import markdown
import html2text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DocumentLoader')


class DocumentLoader:
    """
    Class for loading documents from various file formats.
    """
    
    def __init__(self):
        """
        Initialize the document loader.
        """
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_tables = False
        
        # File extension to content type mapping
        self.extension_mapping = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.markdown': 'text/markdown',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.json': 'application/json',
            '.csv': 'text/csv'
        }
        
        # Content type handlers
        self.handlers = {
            'text/plain': self._load_text,
            'text/markdown': self._load_markdown,
            'text/html': self._load_html,
            'application/pdf': self._load_pdf,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._load_docx,
            'application/msword': self._load_docx,
            'application/json': self._load_json,
            'text/csv': self._load_csv,
        }
    
    def load_document(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load a document from a file path. For PDFs, returns a list of page dictionaries.
        For other types, returns a list containing a single document dictionary.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            A list of dictionaries, each containing page content and metadata.
            For non-PDFs, the list contains one dictionary for the whole document.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine content type from file extension
        ext = os.path.splitext(file_path)[1].lower()
        content_type = self.extension_mapping.get(ext)
        
        if content_type is None:
            logger.warning(f"Unknown file extension: {ext}. Treating as plain text.")
            content_type = 'text/plain'
        
        # Get the appropriate handler
        handler = self.handlers.get(content_type)
        
        if handler is None:
            raise ValueError(f"No handler for content type: {content_type}")
        
        # Base file metadata common to all pages/documents
        base_file_metadata = {
            'source': file_path,
            'filename': os.path.basename(file_path),
            'content_type': content_type,
            'size': os.path.getsize(file_path),
            'last_modified': os.path.getmtime(file_path)
        }
        
        # Process with the handler
        with open(file_path, 'rb') as f:
            # Handlers for non-PDFs return a single (content, metadata) tuple
            # PDF handler returns a list of (page_content, page_metadata) tuples
            handler_output = handler(f)
        
        # --- Process handler output ---
        results = []
        if content_type == 'application/pdf':
            # PDF handler returns a list of page results
            total_pages = len(handler_output)
            for page_content, page_specific_metadata in handler_output:
                # Merge base file metadata with page-specific metadata
                combined_metadata = {**base_file_metadata, **page_specific_metadata, 'total_pages': total_pages}
                results.append({
                    'content': page_content,
                    'metadata': combined_metadata
                })
        else:
            # Other handlers return a single result
            content, specific_metadata = handler_output
            # Merge base file metadata with handler-specific metadata
            combined_metadata = {**base_file_metadata, **specific_metadata}
            results.append({
                'content': content,
                'metadata': combined_metadata
            })
        
        return results
    
    def _load_text(self, file_obj: BinaryIO) -> tuple[str, Dict[str, Any]]:
        """
        Load plain text content.
        
        Args:
            file_obj: File-like object
            
        Returns:
            Tuple of (content, metadata)
        """
        try:
            content = file_obj.read().decode('utf-8')
            return content, {}
        except UnicodeDecodeError:
            # If UTF-8 fails, try with Latin-1 (which can decode any byte sequence)
            file_obj.seek(0)
            content = file_obj.read().decode('latin-1')
            return content, {'encoding': 'latin-1'}
    
    def _load_markdown(self, file_obj: BinaryIO) -> tuple[str, Dict[str, Any]]:
        """
        Load markdown content.
        
        Args:
            file_obj: File-like object
            
        Returns:
            Tuple of (content, metadata)
        """
        content = file_obj.read().decode('utf-8')
        
        # Extract title if available (assuming # Title format)
        title = None
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        metadata = {}
        if title:
            metadata['title'] = title
        
        return content, metadata
    
    def _load_html(self, file_obj: BinaryIO) -> tuple[str, Dict[str, Any]]:
        """
        Load HTML content.
        
        Args:
            file_obj: File-like object
            
        Returns:
            Tuple of (content, metadata)
        """
        html_content = file_obj.read().decode('utf-8')
        text_content = self.html_converter.handle(html_content)
        
        # Extract title from HTML if available
        title = None
        title_match = html_content.lower().find('<title>')
        if title_match != -1:
            title_end = html_content.lower().find('</title>', title_match)
            if title_end != -1:
                title = html_content[title_match + 7:title_end].strip()
        
        metadata = {}
        if title:
            metadata['title'] = title
        
        return text_content, metadata
    
    def _load_pdf(self, file_obj: BinaryIO) -> List[tuple[str, Dict[str, Any]]]:
        """
        Load PDF content page by page.
        
        Args:
            file_obj: File-like object
            
        Returns:
            A list of tuples, where each tuple contains (page_content, page_metadata).
            Page metadata includes 'page_number' (1-based).
        """
        results = []
        try:
            pdf_reader = pypdf.PdfReader(file_obj)
            num_pages = len(pdf_reader.pages)
            
            # Extract common metadata
            common_metadata = {}
            if pdf_reader.metadata:
                if pdf_reader.metadata.title:
                    common_metadata['title'] = pdf_reader.metadata.title
                if pdf_reader.metadata.author:
                    common_metadata['author'] = pdf_reader.metadata.author
                if pdf_reader.metadata.subject:
                    common_metadata['subject'] = pdf_reader.metadata.subject
            
            # Process each page
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                page_content = page.extract_text() or "" # Ensure empty string if extract_text returns None
                
                # Create metadata specific to this page
                page_metadata = {
                    **common_metadata, # Copy common metadata
                    'page_number': page_num + 1 # Add 1-based page number
                }
                results.append((page_content, page_metadata))
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}", exc_info=True)
            # Return an empty list or potentially raise the error
            return []
        
        return results
    
    def _load_docx(self, file_obj: BinaryIO) -> tuple[str, Dict[str, Any]]:
        """
        Load DOCX content.
        
        Args:
            file_obj: File-like object
            
        Returns:
            Tuple of (content, metadata)
        """
        # Save to a temporary file since docx2txt doesn't support file-like objects
        import tempfile
        temp_path = None # Initialize to None
        try:
            # Use 'with' for automatic cleanup if possible, though delete=False complicates it
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                temp_file.write(file_obj.read())
                temp_path = temp_file.name
            
            # Extract text
            content = docx2txt.process(temp_path)
            
            # Limited metadata for docx
            metadata = {}
            
            return content, metadata
        except Exception as e:
            logger.error(f"Error processing DOCX: {e}", exc_info=True)
            return "", {"error": f"Failed to process DOCX: {e}"}
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as unlink_e:
                    logger.error(f"Error removing temporary DOCX file {temp_path}: {unlink_e}")
    
    def _load_json(self, file_obj: BinaryIO) -> tuple[str, Dict[str, Any]]:
        """
        Load JSON content. Assumes JSON represents a single document or record.
        Converts the JSON structure to a string representation for embedding/chunking.
        
        Args:
            file_obj: File-like object
            
        Returns:
            Tuple of (content_string, metadata)
        """
        try:
            data = json.load(file_obj)
            # Convert JSON data to a pretty-printed string
            content_string = json.dumps(data, indent=2)
            # Metadata could potentially include keys from the JSON object itself
            metadata = {'json_keys': list(data.keys())} if isinstance(data, dict) else {}
            return content_string, metadata
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
            return "", {"error": f"Failed to decode JSON: {e}"}
        except Exception as e:
            logger.error(f"Error processing JSON file: {e}", exc_info=True)
            return "", {"error": f"Failed to process JSON: {e}"}
    
    def _load_csv(self, file_obj: BinaryIO) -> tuple[str, Dict[str, Any]]:
        """
        Load CSV content. Converts the entire CSV structure to a string.
        Consider using dedicated CSV libraries for more structured processing if needed.
        
        Args:
            file_obj: File-like object
            
        Returns:
            Tuple of (content_string, metadata)
        """
        try:
            # Read the whole CSV as text for simplicity in this context
            content_string = file_obj.read().decode('utf-8')
            # Simple metadata: maybe first line as header?
            header = content_string.split('\n', 1)[0] if '\n' in content_string else ""
            metadata = {'csv_header': header}
            return content_string, metadata
        except UnicodeDecodeError:
            file_obj.seek(0)
            content_string = file_obj.read().decode('latin-1')
            header = content_string.split('\n', 1)[0] if '\n' in content_string else ""
            metadata = {'csv_header': header, 'encoding': 'latin-1'}
            return content_string, metadata
        except Exception as e:
            logger.error(f"Error processing CSV file: {e}", exc_info=True)
            return "", {"error": f"Failed to process CSV: {e}"} 