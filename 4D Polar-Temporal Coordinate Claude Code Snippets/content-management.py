"""
Content Management System for 4D Polar-Temporal Database

This module handles content ingestion, processing, and preparation for storage
in the 4D polar-temporal database. It transforms various content types into a
standardized format with 4D coordinates.
"""

import os
import json
import time
import hashlib
import re
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any, BinaryIO
from datetime import datetime
import logging
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Import helpers for specific file types
import docx
import PyPDF2
import markdown
import html2text
import csv


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ContentManagement')


class ContentProcessor:
    """
    Processes content for ingestion into the 4D database.
    """
    
    def __init__(self,
                 embedding_service,
                 angular_mapper,
                 relevance_calculator,
                 storage_manager,
                 processing_threads: int = 4,
                 max_queue_size: int = 1000,
                 input_dir: str = './input',
                 processed_dir: str = './processed',
                 failed_dir: str = './failed'):
        """
        Initialize the content processor.
        
        Args:
            embedding_service: Service for generating embeddings
            angular_mapper: Service for mapping content to angular positions
            relevance_calculator: Service for calculating relevance scores
            storage_manager: Storage manager for the 4D database
            processing_threads: Number of processing threads
            max_queue_size: Maximum size of processing queue
            input_dir: Directory for input files
            processed_dir: Directory for processed files
            failed_dir: Directory for failed files
        """
        self.embedding_service = embedding_service
        self.angular_mapper = angular_mapper
        self.relevance_calculator = relevance_calculator
        self.storage_manager = storage_manager
        
        self.processing_threads = processing_threads
        self.max_queue_size = max_queue_size
        
        # Create directories if they don't exist
        self.input_dir = input_dir
        self.processed_dir = processed_dir
        self.failed_dir = failed_dir
        
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        os.makedirs(failed_dir, exist_ok=True)
        
        # Processing queue
        self.queue = queue.Queue(maxsize=max_queue_size)
        
        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=processing_threads)
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'processing_time': 0,
            'by_type': {}
        }
        
        # Content type handlers
        self.handlers = {
            'text/plain': self._process_text,
            'text/markdown': self._process_markdown,
            'text/html': self._process_html,
            'application/pdf': self._process_pdf,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._process_docx,
            'application/json': self._process_json,
            'text/csv': self._process_csv,
            'text/x-python': self._process_code,
            'text/x-java': self._process_code,
            'text/x-c': self._process_code,
            'text/x-javascript': self._process_code,
            'application/xml': self._process_xml,
            'text/x-chat': self._process_chat
        }
        
        # File extension to content type mapping
        self.extension_mapping = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.markdown': 'text/markdown',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.json': 'application/json',
            '.csv': 'text/csv',
            '.py': 'text/x-python',
            '.java': 'text/x-java',
            '.c': 'text/x-c',
            '.cpp': 'text/x-c',
            '.js': 'text/x-javascript',
            '.xml': 'application/xml',
            '.chat': 'text/x-chat'
        }
        
        # Running flag
        self.running = False
        
    def start(self) -> None:
        """
        Start the content processing service.
        """
        if self.running:
            logger.warning("Content processor already running")
            return
            
        self.running = True
        
        # Start worker threads
        for _ in range(self.processing_threads):
            self.executor.submit(self._worker)
            
        logger.info(f"Content processor started with {self.processing_threads} workers")
        
    def stop(self) -> None:
        """
        Stop the content processing service.
        """
        if not self.running:
            logger.warning("Content processor already stopped")
            return
            
        self.running = False
        
        # Wait for queue to empty
        self.queue.join()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("Content processor stopped")
        
    def _worker(self) -> None:
        """
        Worker thread function.
        """
        while self.running:
            try:
                # Get item from queue with timeout
                task = self.queue.get(timeout=1.0)
                
                try:
                    # Process the item
                    self._process_item(task)
                except Exception as e:
                    logger.error(f"Error processing task {task.get('id', 'unknown')}: {e}")
                    
                    # Move file to failed directory if it's a file
                    if 'file_path' in task:
                        failed_path = os.path.join(self.failed_dir, os.path.basename(task['file_path']))
                        os.rename(task['file_path'], failed_path)
                        
                    # Update statistics
                    self.stats['failed'] += 1
                finally:
                    # Mark task as done
                    self.queue.task_done()
                    
            except queue.Empty:
                # Queue is empty, just continue
                continue
                
    def add_file(self, file_path: str, **kwargs) -> None:
        """
        Add a file to the processing queue.
        
        Args:
            file_path: Path to the file
            **kwargs: Additional processing parameters
        """
        # Create a unique ID based on file path and timestamp
        file_id = hashlib.md5(f"{file_path}_{time.time()}".encode()).hexdigest()
        
        # Determine content type from file extension
        ext = os.path.splitext(file_path)[1].lower()
        content_type = self.extension_mapping.get(ext, 'text/plain')
        
        # Create task
        task = {
            'id': file_id,
            'type': 'file',
            'file_path': file_path,
            'content_type': content_type,
            'timestamp': time.time(),
            'params': kwargs
        }
        
        # Add to queue
        self.queue.put(task)
        logger.debug(f"Added file to queue: {file_path}")
        
    def add_content(self, content: str, content_type: str, **kwargs) -> None:
        """
        Add raw content to the processing queue.
        
        Args:
            content: The content to process
            content_type: MIME type of the content
            **kwargs: Additional processing parameters
        """
        # Create a unique ID based on content hash and timestamp
        content_hash = hashlib.md5(content.encode()).hexdigest()
        content_id = f"{content_hash}_{int(time.time())}"
        
        # Create task
        task = {
            'id': content_id,
            'type': 'content',
            'content': content,
            'content_type': content_type,
            'timestamp': time.time(),
            'params': kwargs
        }
        
        # Add to queue
        self.queue.put(task)
        logger.debug(f"Added content to queue: {content_id}")
        
    def scan_input_directory(self) -> int:
        """
        Scan the input directory for files to process.
        
        Returns:
            Number of files added to the queue
        """
        count = 0
        
        for file_path in Path(self.input_dir).glob('**/*'):
            if file_path.is_file():
                self.add_file(str(file_path))
                count += 1
                
        logger.info(f"Added {count} files from input directory to queue")
        return count
        
    def _process_item(self, task: Dict[str, Any]) -> None:
        """
        Process a task from the queue.
        
        Args:
            task: Task dictionary
        """
        start_time = time.time()
        
        try:
            # Extract task information
            task_id = task['id']
            content_type = task['content_type']
            task_type = task['type']  # 'file' or 'content'
            
            logger.debug(f"Processing {task_type} {task_id} of type {content_type}")
            
            # Process file or content
            if task_type == 'file':
                file_path = task['file_path']
                
                # Read content from file
                with open(file_path, 'rb') as f:
                    result = self._process_file(f, content_type, task.get('params', {}))
                    
                # Move file to processed directory on success
                if result:
                    processed_path = os.path.join(self.processed_dir, os.path.basename(file_path))
                    os.rename(file_path, processed_path)
                else:
                    # Move to failed directory on failure
                    failed_path = os.path.join(self.failed_dir, os.path.basename(file_path))
                    os.rename(file_path, failed_path)
                    
            elif task_type == 'content':
                # Process raw content
                content = task['content']
                result = self._process_raw_content(content, content_type, task.get('params', {}))
                
            # Update statistics
            self.stats['total_processed'] += 1
            
            if content_type in self.stats['by_type']:
                self.stats['by_type'][content_type] += 1
            else:
                self.stats['by_type'][content_type] = 1
                
            if result:
                self.stats['successful'] += 1
            else:
                self.stats['failed'] += 1
                
            processing_time = time.time() - start_time
            self.stats['processing_time'] += processing_time
            
            logger.debug(f"Processed {task_type} {task_id} in {processing_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error in _process_item: {e}")
            self.stats['failed'] += 1
            
    def _process_file(self, file_obj: BinaryIO, content_type: str, params: Dict[str, Any]) -> bool:
        """
        Process a file based on its content type.
        
        Args:
            file_obj: File-like object
            content_type: MIME type of the content
            params: Additional processing parameters
            
        Returns:
            True if processing succeeded
        """
        # Get handler for content type
        handler = self.handlers.get(content_type)
        
        if not handler:
            logger.warning(f"No handler for content type: {content_type}")
            return False
            
        try:
            # Process with appropriate handler
            content_items = handler(file_obj, params)
            
            # Store items in database
            if content_items:
                for item in content_items:
                    self._store_content_item(item)
                return True
            else:
                logger.warning("Handler returned no content items")
                return False
                
        except Exception as e:
            logger.error(f"Error processing file with content type {content_type}: {e}")
            return False
            
    def _process_raw_content(self, content: str, content_type: str, params: Dict[str, Any]) -> bool:
        """
        Process raw content based on its content type.
        
        Args:
            content: Content string
            content_type: MIME type of the content
            params: Additional processing parameters
            
        Returns:
            True if processing succeeded
        """
        try:
            # For raw content, we use the same handlers but adapt the input
            if content_type in ['text/plain', 'text/markdown', 'text/html', 'application/json', 'text/csv', 'text/x-chat']:
                # Text content can be passed directly as a file-like object
                from io import StringIO
                file_obj = StringIO(content)
                
            else:
                # Binary content needs to be converted to bytes
                from io import BytesIO
                file_obj = BytesIO(content.encode('utf-8'))
                
            # Use the same processing as for files
            return self._process_file(file_obj, content_type, params)
            
        except Exception as e:
            logger.error(f"Error processing raw content of type {content_type}: {e}")
            return False
            
    def _store_content_item(self, item: Dict[str, Any]) -> bool:
        """
        Store a processed content item in the 4D database.
        
        Args:
            item: Processed content item
            
        Returns:
            True if storage succeeded
        """
        try:
            # Extract item components
            item_id = item['id']
            content = item['content']
            coordinates = item['coordinates']
            metadata = item.get('metadata', {})
            embedding = item.get('embedding')
            
            # Store in the database
            self.storage_manager.store_item(
                item_id=item_id,
                content=content,
                coordinates=coordinates,
                metadata=metadata,
                embedding=embedding
            )
            
            logger.debug(f"Stored item {item_id} in database")
            return True
            
        except Exception as e:
            logger.error(f"Error storing content item: {e}")
            return False
            
    def _process_text(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process plain text content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Read content
        content = file_obj.read().decode('utf-8')
        
        # Simple chunking for plain text - split by paragraphs
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
        
        # Create items from paragraphs
        items = []
        
        for i, paragraph in enumerate(paragraphs):
            # Skip if too short
            if len(paragraph) < 10:
                continue
                
            # Create item ID
            item_id = f"text_{hashlib.md5(paragraph.encode()).hexdigest()}"
            
            # Generate embedding
            embedding = self.embedding_service.get_embedding(paragraph)
            
            # Determine coordinates
            coordinates = self._calculate_coordinates(
                content=paragraph,
                embedding=embedding,
                params=params,
                item_index=i,
                total_items=len(paragraphs)
            )
            
            # Create metadata
            metadata = {
                'source': params.get('source', 'text'),
                'title': params.get('title', f"Paragraph {i+1}"),
                'order': i,
                'content_type': 'text/plain'
            }
            
            # Add any provided metadata
            if 'metadata' in params:
                metadata.update(params['metadata'])
                
            # Create content item
            items.append({
                'id': item_id,
                'content': paragraph,
                'coordinates': coordinates,
                'metadata': metadata,
                'embedding': embedding
            })
            
        return items
        
    def _process_markdown(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process Markdown content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Read content
        content = file_obj.read().decode('utf-8')
        
        # Split by headings and sections
        sections = []
        current_section = {"heading": "", "content": []}
        
        for line in content.split('\n'):
            # Check if line is a heading
            if line.startswith('#'):
                # Save previous section if not empty
                if current_section["content"]:
                    sections.append(current_section)
                    
                # Start a new section
                current_section = {
                    "heading": line.strip('# '),
                    "content": []
                }
            else:
                current_section["content"].append(line)
                
        # Add the last section
        if current_section["content"]:
            sections.append(current_section)
            
        # Create items from sections
        items = []
        
        for i, section in enumerate(sections):
            # Join section content
            section_content = '\n'.join(section["content"]).strip()
            
            # Skip if too short
            if len(section_content) < 10:
                continue
                
            # Create item ID using heading and content hash
            section_hash = hashlib.md5(section_content.encode()).hexdigest()
            item_id = f"md_{section_hash}"
            
            # Generate embedding
            embedding = self.embedding_service.get_embedding(section_content)
            
            # Determine coordinates
            coordinates = self._calculate_coordinates(
                content=section_content,
                embedding=embedding,
                params=params,
                item_index=i,
                total_items=len(sections)
            )
            
            # Create metadata
            metadata = {
                'source': params.get('source', 'markdown'),
                'title': section["heading"] or params.get('title', f"Section {i+1}"),
                'order': i,
                'content_type': 'text/markdown'
            }
            
            # Add any provided metadata
            if 'metadata' in params:
                metadata.update(params['metadata'])
                
            # Create content item
            items.append({
                'id': item_id,
                'content': section_content,
                'coordinates': coordinates,
                'metadata': metadata,
                'embedding': embedding
            })
            
        return items
        
    def _process_html(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process HTML content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Read content
        content = file_obj.read().decode('utf-8')
        
        # Convert HTML to plain text
        h2t = html2text.HTML2Text()
        h2t.ignore_links = False
        h2t.bypass_tables = False
        text = h2t.handle(content)
        
        # Use markdown processor since HTML2Text produces markdown
        from io import StringIO
        return self._process_markdown(StringIO(text), params)
        
    def _process_pdf(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process PDF content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Parse PDF
        pdf_reader = PyPDF2.PdfReader(file_obj)
        
        # Extract text from pages
        page_texts = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text.strip():
                page_texts.append(text)
                
        # Create items from pages
        items = []
        
        for i, page_text in enumerate(page_texts):
            # Skip if too short
            if len(page_text) < 10:
                continue
                
            # Create item ID
            page_hash = hashlib.md5(page_text.encode()).hexdigest()
            item_id = f"pdf_p{i}_{page_hash}"
            
            # Generate embedding
            embedding = self.embedding_service.get_embedding(page_text)
            
            # Determine coordinates
            coordinates = self._calculate_coordinates(
                content=page_text,
                embedding=embedding,
                params=params,
                item_index=i,
                total_items=len(page_texts)
            )
            
            # Create metadata
            metadata = {
                'source': params.get('source', 'pdf'),
                'title': params.get('title', f"Page {i+1}"),
                'page': i + 1,
                'content_type': 'application/pdf'
            }
            
            # Add document info if available
            if pdf_reader.metadata:
                for key, value in pdf_reader.metadata.items():
                    if key.startswith('/'):
                        meta_key = key[1:].lower()
                        metadata[meta_key] = value
                        
            # Add any provided metadata
            if 'metadata' in params:
                metadata.update(params['metadata'])
                
            # Create content item
            items.append({
                'id': item_id,
                'content': page_text,
                'coordinates': coordinates,
                'metadata': metadata,
                'embedding': embedding
            })
            
        return items
        
    def _process_docx(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process DOCX content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Parse DOCX
        doc = docx.Document(file_obj)
        
        # Extract paragraphs
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        # Create items from paragraphs
        items = []
        
        for i, paragraph in enumerate(paragraphs):
            # Skip if too short
            if len(paragraph) < 10:
                continue
                
            # Create item ID
            item_id = f"docx_{hashlib.md5(paragraph.encode()).hexdigest()}"
            
            # Generate embedding
            embedding = self.embedding_service.get_embedding(paragraph)
            
            # Determine coordinates
            coordinates = self._calculate_coordinates(
                content=paragraph,
                embedding=embedding,
                params=params,
                item_index=i,
                total_items=len(paragraphs)
            )
            
            # Create metadata
            metadata = {
                'source': params.get('source', 'docx'),
                'title': params.get('title', f"Paragraph {i+1}"),
                'order': i,
                'content_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
            
            # Add any provided metadata
            if 'metadata' in params:
                metadata.update(params['metadata'])
                
            # Create content item
            items.append({
                'id': item_id,
                'content': paragraph,
                'coordinates': coordinates,
                'metadata': metadata,
                'embedding': embedding
            })
            
        return items
        
    def _process_json(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process JSON content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Parse JSON
        content = file_obj.read().decode('utf-8')
        data = json.loads(content)
        
        # Process based on structure
        items = []
        
        # If it's a list, process each item
        if isinstance(data, list):
            for i, item in enumerate(data):
                # Convert item to string
                if isinstance(item, (dict, list)):
                    item_text = json.dumps(item, indent=2)
                else:
                    item_text = str(item)
                    
                # Skip if too short
                if len(item_text) < 10:
                    continue
                    
                # Create item ID
                item_id = f"json_{hashlib.md5(item_text.encode()).hexdigest()}"
                
                # Generate embedding
                embedding = self.embedding_service.get_embedding(item_text)
                
                # Determine coordinates
                coordinates = self._calculate_coordinates(
                    content=item_text,
                    embedding=embedding,
                    params=params,
                    item_index=i,
                    total_items=len(data)
                )
                
                # Create metadata
                metadata = {
                    'source': params.get('source', 'json'),
                    'title': params.get('title', f"Item {i+1}"),
                    'index': i,
                    'content_type': 'application/json'
                }
                
                # Add any provided metadata
                if 'metadata' in params:
                    metadata.update(params['metadata'])
                    
                # Create content item
                items.append({
                    'id': item_id,
                    'content': item_text,
                    'coordinates': coordinates,
                    'metadata': metadata,
                    'embedding': embedding
                })
                
        # If it's a dictionary, process each key-value pair
        elif isinstance(data, dict):
            for i, (key, value) in enumerate(data.items()):
                # Convert value to string
                if isinstance(value, (dict, list)):
                    value_text = json.dumps(value, indent=2)
                else:
                    value_text = str(value)
                    
                # Skip if too short
                if len(value_text) < 10:
                    continue
                    
                # Create item ID
                item_id = f"json_{key}_{hashlib.md5(value_text.encode()).hexdigest()}"
                
                # Generate embedding
                embedding = self.embedding_service.get_embedding(value_text)
                
                # Determine coordinates
                coordinates = self._calculate_coordinates(
                    content=value_text,
                    embedding=embedding,
                    params=params,
                    item_index=i,
                    total_items=len(data)
                )
                
                # Create metadata
                metadata = {
                    'source': params.get('source', 'json'),
                    'title': key,
                    'key': key,
                    'content_type': 'application/json'
                }
                
                # Add any provided metadata
                if 'metadata' in params:
                    metadata.update(params['metadata'])
                    
                # Create content item
                items.append({
                    'id': item_id,
                    'content': value_text,
                    'coordinates': coordinates,
                    'metadata': metadata,
                    'embedding': embedding
                })
                
        # If it's a simple value, process it directly
        else:
            item_text = str(data)
            
            # Skip if too short
            if len(item_text) < 10:
                return []
                
            # Create item ID
            item_id = f"json_{hashlib.md5(item_text.encode()).hexdigest()}"
            
            # Generate embedding
            embedding = self.embedding_service.get_embedding(item_text)
            
            # Determine coordinates
            coordinates = self._calculate_coordinates(
                content=item_text,
                embedding=embedding,
                params=params,
                item_index=0,
                total_items=1
            )
            
            # Create metadata
            metadata = {
                'source': params.get('source', 'json'),
                'title': params.get('title', 'JSON Value'),
                'content_type': 'application/json'
            }
            
            # Add any provided metadata
            if 'metadata' in params:
                metadata.update(params['metadata'])
                
            # Create content item
            items.append({
                'id': item_id,
                'content': item_text,
                'coordinates': coordinates,
                'metadata': metadata,
                'embedding': embedding
            })
            
        return items
        
    def _process_csv(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process CSV content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Parse CSV
        content = file_obj.read().decode('utf-8')
        
        # Reset file pointer to beginning
        file_obj.seek(0)
        
        # Read CSV
        reader = csv.reader(file_obj)
        rows = list(reader)
        
        if not rows:
            return []
            
        # Get headers (first row)
        headers = rows[0]
        
        # Process each row
        items = []
        
        for i, row in enumerate(rows[1:], 1):  # Skip header row
            # Skip rows with wrong number of columns
            if len(row) != len(headers):
                continue
                
            # Create row dictionary
            row_dict = dict(zip(headers, row))
            
            # Convert to string
            row_text = json.dumps(row_dict, indent=2)
            
            # Skip if too short
            if len(row_text) < 10:
                continue
                
            # Create item ID
            item_id = f"csv_r{i}_{hashlib.md5(row_text.encode()).hexdigest()}"
            
            # Generate embedding
            embedding = self.embedding_service.get_embedding(row_text)
            
            # Determine coordinates
            coordinates = self._calculate_coordinates(
                content=row_text,
                embedding=embedding,
                params=params,
                item_index=i,
                total_items=len(rows) - 1
            )
            
            # Create metadata
            metadata = {
                'source': params.get('source', 'csv'),
                'title': params.get('title', f"Row {i}"),
                'row': i,
                'headers': headers,
                'content_type': 'text/csv'
            }
            
            # Add any provided metadata
            if 'metadata' in params:
                metadata.update(params['metadata'])
                
            # Create content item
            items.append({
                'id': item_id,
                'content': row_text,
                'coordinates': coordinates,
                'metadata': metadata,
                'embedding': embedding
            })
            
        return items
        
    def _process_code(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process code content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Read content
        content = file_obj.read().decode('utf-8')
        
        # Identify language from content type
        content_type = params.get('content_type', 'text/x-python')
        language = content_type.split('/')[-1].replace('x-', '')
        
        # Split by functions/classes for some languages
        sections = []
        
        if language in ['python', 'java', 'javascript']:
            # Simple regex-based parsing for demonstration
            # In a production system, you'd use a proper AST parser
            
            # Function pattern
            if language == 'python':
                pattern = r'(def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*:(?:(?!\ndef\s+)[^\n]|\n(?!\s*def\s+)[^\n])*)'
            elif language in ['java', 'javascript']:
                pattern = r'((?:public|private|protected)?\s*(?:static\s+)?(?:function\s+)?[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*\{(?:[^{}]|\{[^{}]*\})*\})'
            else:
                pattern = None
                
            if pattern:
                # Find functions
                function_matches = re.finditer(pattern, content, re.DOTALL)
                
                # Extract matches and their positions
                matches = []
                positions = []
                
                for match in function_matches:
                    matches.append(match.group(0))
                    positions.append((match.start(), match.end()))
                    
                # Add functions as sections
                for i, (match, (start, end)) in enumerate(zip(matches, positions)):
                    sections.append({
                        'heading': f"Function {i+1}",
                        'content': match,
                        'start': start,
                        'end': end
                    })
                    
                # Add remaining code as sections
                if positions:
                    prev_end = 0
                    for start, end in sorted(positions):
                        if start > prev_end:
                            sections.append({
                                'heading': f"Code Block",
                                'content': content[prev_end:start],
                                'start': prev_end,
                                'end': start
                            })
                        prev_end = end
                        
                    # Add final section
                    if prev_end < len(content):
                        sections.append({
                            'heading': f"Code Block",
                            'content': content[prev_end:],
                            'start': prev_end,
                            'end': len(content)
                        })
                        
        # If no sections found, treat as a single code block
        if not sections:
            sections.append({
                'heading': f"Code Block",
                'content': content,
                'start': 0,
                'end': len(content)
            })
            
        # Create items from sections
        items = []
        
        for i, section in enumerate(sections):
            section_content = section['content'].strip()
            
            # Skip if too short
            if len(section_content) < 10:
                continue
                
            # Create item ID
            section_hash = hashlib.md5(section_content.encode()).hexdigest()
            item_id = f"code_{section_hash}"
            
            # Generate embedding
            embedding = self.embedding_service.get_embedding(section_content)
            
            # Determine coordinates
            coordinates = self._calculate_coordinates(
                content=section_content,
                embedding=embedding,
                params=params,
                item_index=i,
                total_items=len(sections)
            )
            
            # Create metadata
            metadata = {
                'source': params.get('source', 'code'),
                'title': section["heading"],
                'language': language,
                'start_pos': section['start'],
                'end_pos': section['end'],
                'content_type': content_type
            }
            
            # Add any provided metadata
            if 'metadata' in params:
                metadata.update(params['metadata'])
                
            # Create content item
            items.append({
                'id': item_id,
                'content': section_content,
                'coordinates': coordinates,
                'metadata': metadata,
                'embedding': embedding
            })
            
        return items
        
    def _process_xml(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process XML content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Import XML parser
        import xml.etree.ElementTree as ET
        
        # Parse XML
        tree = ET.parse(file_obj)
        root = tree.getroot()
        
        # Extract elements recursively
        items = []
        
        def process_element(element, path):
            # Get element text
            text = element.text.strip() if element.text else ""
            
            # Include child element text
            for child in element:
                if child.tail and child.tail.strip():
                    text += " " + child.tail.strip()
                    
            # Skip if too short
            if len(text) < 10:
                return
                
            # Create item ID
            element_hash = hashlib.md5(text.encode()).hexdigest()
            item_id = f"xml_{element_hash}"
            
            # Generate embedding
            embedding = self.embedding_service.get_embedding(text)
            
            # Determine coordinates
            coordinates = self._calculate_coordinates(
                content=text,
                embedding=embedding,
                params=params,
                item_index=len(items),
                total_items=100  # Approximate total
            )
            
            # Create metadata
            metadata = {
                'source': params.get('source', 'xml'),
                'title': path,
                'tag': element.tag,
                'attributes': dict(element.attrib),
                'content_type': 'application/xml'
            }
            
            # Add any provided metadata
            if 'metadata' in params:
                metadata.update(params['metadata'])
                
            # Create content item
            items.append({
                'id': item_id,
                'content': text,
                'coordinates': coordinates,
                'metadata': metadata,
                'embedding': embedding
            })
            
            # Process children
            for i, child in enumerate(element):
                child_path = f"{path}/{child.tag}[{i}]"
                process_element(child, child_path)
                
        # Start processing from root
        process_element(root, f"/{root.tag}")
        
        return items
        
    def _process_chat(self, file_obj: BinaryIO, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process chat content.
        
        Args:
            file_obj: File-like object
            params: Processing parameters
            
        Returns:
            List of processed content items
        """
        # Read content
        content = file_obj.read().decode('utf-8')
        
        # Parse chat format - expecting lines like "Name: Message"
        messages = []
        current_speaker = None
        current_message = []
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
                
            # Check if line starts a new message
            speaker_match = re.match(r'^([^:]+):\s*(.*)$', line)
            
            if speaker_match:
                # Save previous message if exists
                if current_speaker and current_message:
                    messages.append({
                        'speaker': current_speaker,
                        'message': '\n'.join(current_message)
                    })
                    
                # Start new message
                current_speaker = speaker_match.group(1).strip()
                message_start = speaker_match.group(2).strip()
                current_message = [message_start] if message_start else []
            else:
                # Continue previous message
                if current_speaker:
                    current_message.append(line)
                    
        # Add final message
        if current_speaker and current_message:
            messages.append({
                'speaker': current_speaker,
                'message': '\n'.join(current_message)
            })
            
        # Create items from messages
        items = []
        
        for i, msg in enumerate(messages):
            # Skip if too short
            if len(msg['message']) < 5:
                continue
                
            # Create item ID
            msg_hash = hashlib.md5(f"{msg['speaker']}_{msg['message']}".encode()).hexdigest()
            item_id = f"chat_{msg_hash}"
            
            # Generate embedding
            embedding = self.embedding_service.get_embedding(msg['message'])
            
            # Determine coordinates
            coordinates = self._calculate_coordinates(
                content=msg['message'],
                embedding=embedding,
                params=params,
                item_index=i,
                total_items=len(messages)
            )
            
            # Create metadata
            metadata = {
                'source': params.get('source', 'chat'),
                'title': f"{msg['speaker']} (message {i+1})",
                'speaker': msg['speaker'],
                'message_index': i,
                'content_type': 'text/x-chat'
            }
            
            # Add any provided metadata
            if 'metadata' in params:
                metadata.update(params['metadata'])
                
            # Create content item
            items.append({
                'id': item_id,
                'content': msg['message'],
                'coordinates': coordinates,
                'metadata': metadata,
                'embedding': embedding
            })
            
        return items
        
    def _calculate_coordinates(self,
                             content: str,
                             embedding: np.ndarray,
                             params: Dict[str, Any],
                             item_index: int,
                             total_items: int) -> Dict[str, float]:
        """
        Calculate 4D coordinates for a content item.
        
        Args:
            content: The content text
            embedding: Vector embedding of the content
            params: Processing parameters
            item_index: Index of the item in its sequence
            total_items: Total number of items in the sequence
            
        Returns:
            Dictionary with r, theta, t, z coordinates
        """
        # Calculate angular position (topic/category)
        if 'categories' in params:
            # Use specified categories
            theta = self.angular_mapper.calculate_category_angle(params['categories'])
        else:
            # Calculate from content
            theta = self.angular_mapper.calculate_embedding_angle(embedding)
            
        # Calculate radial position (relevance)
        if 'central_concept' in params:
            # Compare to a central concept
            central_embedding = self.embedding_service.get_embedding(params['central_concept'])
            r = self.relevance_calculator.calculate_semantic_relevance(central_embedding, embedding)
        else:
            # Use default moderate relevance
            r = 1.0
            
        # Calculate temporal position
        if 'timestamp' in params:
            # Use specified timestamp
            t = params['timestamp']
        elif 'date' in params:
            # Parse date string
            date_str = params['date']
            try:
                dt = datetime.fromisoformat(date_str)
                t = dt.timestamp()
            except (ValueError, TypeError):
                # Use sequence position as fallback
                t = time.time() - (total_items - item_index) * 3600  # 1 hour between items
        else:
            # Use sequence position
            t = time.time() - (total_items - item_index) * 3600  # 1 hour between items
            
        # Calculate context layer
        if 'context_layer' in params:
            # Use specified context layer
            z = params['context_layer']
        else:
            # Default to conceptual (middle) layer
            z = 2
            
        return {
            'r': r,
            'theta': theta,
            't': t,
            'z': z
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary of processing statistics
        """
        # Calculate average processing time
        if self.stats['total_processed'] > 0:
            avg_time = self.stats['processing_time'] / self.stats['total_processed']
        else:
            avg_time = 0
            
        # Add calculated stats
        stats = dict(self.stats)
        stats['avg_processing_time'] = avg_time
        stats['queue_size'] = self.queue.qsize()
        stats['running'] = self.running
        
        return stats


# Example usage with mock services
class MockEmbeddingService:
    def get_embedding(self, text):
        # Return random embedding for example
        return np.random.random(256).astype(np.float32)


class MockAngularMapper:
    def calculate_embedding_angle(self, embedding):
        # Return random angle for example
        return np.random.random() * 2 * np.pi
        
    def calculate_category_angle(self, categories):
        # Return random angle for example
        return np.random.random() * 2 * np.pi


class MockRelevanceCalculator:
    def calculate_semantic_relevance(self, query_embedding, item_embedding):
        # Return random relevance for example
        return np.random.random() * 2


class MockStorageManager:
    def store_item(self, item_id, content, coordinates, metadata, embedding):
        # Just log for example
        logger.info(f"Stored item {item_id} with coordinates {coordinates}")
        return True


# Example usage
if __name__ == "__main__":
    # Create mock services
    embedding_service = MockEmbeddingService()
    angular_mapper = MockAngularMapper()
    relevance_calculator = MockRelevanceCalculator()
    storage_manager = MockStorageManager()
    
    # Create content processor
    processor = ContentProcessor(
        embedding_service=embedding_service,
        angular_mapper=angular_mapper,
        relevance_calculator=relevance_calculator,
        storage_manager=storage_manager,
        input_dir='./test_input',
        processed_dir='./test_processed',
        failed_dir='./test_failed'
    )
    
    # Start processor
    processor.start()
    
    # Example: Add raw text content
    text_content = """
    This is an example text document.
    
    It has multiple paragraphs with different content.
    
    This paragraph talks about machine learning and AI.
    
    This one is about database systems and storage.
    """
    
    processor.add_content(
        content=text_content,
        content_type='text/plain',
        source='example',
        title='Example Text',
        central_concept='database systems'
    )
    
    # Example: Add markdown content
    markdown_content = """
    # Example Markdown Document
    
    ## Introduction
    
    This is an introduction to our topic.
    
    ## Main Concepts
    
    Here we discuss the main concepts of our topic.
    
    * Point one
    * Point two
    * Point three
    
    ## Conclusion
    
    In conclusion, the topic is very interesting.
    """
    
    processor.add_content(
        content=markdown_content,
        content_type='text/markdown',
        source='example',
        title='Example Markdown',
        categories=['documentation', 'example']
    )
    
    # Wait for processing to complete
    import time
    time.sleep(2)
    
    # Get stats
    stats = processor.get_stats()
    print("\nProcessing Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
        
    # Stop processor
    processor.stop()