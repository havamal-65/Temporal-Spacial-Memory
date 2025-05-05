"""
Data Migration Utility

This module provides utilities for backing up and migrating data between different storage formats,
particularly for the transition to polar coordinate storage. It handles safe data transformation
while preserving original data and provides rollback capabilities.
"""

import os
import shutil
import json
import pickle
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Callable
import numpy as np
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataMigration')

class DataMigrator:
    """
    Utility for backing up and migrating data between storage formats.
    Focuses on safe transformation with backup and rollback capabilities.
    """
    
    def __init__(self, 
                storage_path: str,
                backup_path: Optional[str] = None,
                migration_log_file: Optional[str] = None):
        """
        Initialize the data migrator.
        
        Args:
            storage_path: Path to the main data storage directory
            backup_path: Path for storing backups (defaults to storage_path + '_backup_[timestamp]')
            migration_log_file: Path to log migration progress (defaults to backup_path + '/migration_log.json')
        """
        self.storage_path = os.path.abspath(storage_path)
        
        # Create default backup path if not provided
        if backup_path is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            self.backup_path = f"{self.storage_path}_backup_{timestamp}"
        else:
            self.backup_path = os.path.abspath(backup_path)
            
        # Create default migration log file if not provided
        if migration_log_file is None:
            self.migration_log_file = os.path.join(self.backup_path, 'migration_log.json')
        else:
            self.migration_log_file = os.path.abspath(migration_log_file)
            
        # Information about the current migration
        self.migration_log = {
            'started_at': None,
            'completed_at': None,
            'status': 'not_started',
            'backup_path': self.backup_path,
            'source_path': self.storage_path,
            'steps': [],
            'errors': []
        }
    
    def create_backup(self, selective: bool = False, include_patterns: Optional[List[str]] = None) -> bool:
        """
        Create a backup of the current data storage.
        
        Args:
            selective: If True, only backup files matching include_patterns
            include_patterns: List of filename patterns to include in selective backup
            
        Returns:
            True if backup was successful, False otherwise
        """
        if not os.path.exists(self.storage_path):
            logger.error(f"Source path does not exist: {self.storage_path}")
            return False
            
        # Create backup directory
        try:
            os.makedirs(self.backup_path, exist_ok=True)
            logger.info(f"Created backup directory: {self.backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup directory: {e}")
            return False
            
        # Start migration log
        self.migration_log['started_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.migration_log['status'] = 'backup_in_progress'
        self._save_migration_log()
        
        try:
            # Count total files for progress reporting
            total_files = sum([len(files) for _, _, files in os.walk(self.storage_path)])
            logger.info(f"Found {total_files} files to potentially backup")
            
            # Selective or full backup
            if selective and include_patterns:
                self._selective_backup(include_patterns)
                logger.info(f"Completed selective backup to {self.backup_path}")
            else:
                self._full_backup()
                logger.info(f"Completed full backup to {self.backup_path}")
                
            # Update migration log
            self.migration_log['status'] = 'backup_completed'
            self._save_migration_log()
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            self.migration_log['status'] = 'backup_failed'
            self.migration_log['errors'].append(str(e))
            self._save_migration_log()
            return False
    
    def _full_backup(self):
        """Perform a full recursive backup of the storage directory."""
        logger.info(f"Starting full backup from {self.storage_path} to {self.backup_path}")
        
        # Walk through the directory and copy all files
        for root, dirs, files in os.walk(self.storage_path):
            # Calculate relative path to maintain directory structure
            rel_path = os.path.relpath(root, self.storage_path)
            target_dir = os.path.join(self.backup_path, rel_path) if rel_path != '.' else self.backup_path
            
            # Create target directory
            os.makedirs(target_dir, exist_ok=True)
            
            # Copy each file
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                shutil.copy2(src_file, dst_file)
                logger.debug(f"Backed up: {src_file} -> {dst_file}")
    
    def _selective_backup(self, include_patterns: List[str]):
        """
        Perform a selective backup based on filename patterns.
        
        Args:
            include_patterns: List of patterns to match filenames for backup
        """
        logger.info(f"Starting selective backup with patterns: {include_patterns}")
        
        # Walk through the directory
        for root, dirs, files in os.walk(self.storage_path):
            # Calculate relative path
            rel_path = os.path.relpath(root, self.storage_path)
            target_dir = os.path.join(self.backup_path, rel_path) if rel_path != '.' else self.backup_path
            
            # Filter files based on patterns
            matched_files = []
            for file in files:
                if any(pattern in file for pattern in include_patterns):
                    matched_files.append(file)
            
            if matched_files:
                # Create target directory if there are matched files
                os.makedirs(target_dir, exist_ok=True)
                
                # Copy matched files
                for file in matched_files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(target_dir, file)
                    shutil.copy2(src_file, dst_file)
                    logger.debug(f"Selectively backed up: {src_file} -> {dst_file}")
    
    def migrate_database(self, transformation_fn: Callable[[Dict], Dict]) -> bool:
        """
        Migrate the database nodes with a custom transformation function.
        
        Args:
            transformation_fn: Function to transform each node in the database
            
        Returns:
            True if migration was successful, False otherwise
        """
        db_path = os.path.join(self.storage_path, "spatial_temporal_db.pkl")
        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}")
            return False
            
        # Update migration log
        self.migration_log['status'] = 'database_migration_in_progress'
        self.migration_log['steps'].append({
            'name': 'database_migration',
            'started_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'file': db_path
        })
        self._save_migration_log()
        
        try:
            # Load the database
            with open(db_path, 'rb') as f:
                nodes = pickle.load(f)
                
            logger.info(f"Loaded database with {len(nodes)} nodes")
            
            # Transform nodes
            transformed_nodes = {}
            for node_id, node in tqdm(nodes.items(), desc="Transforming nodes"):
                transformed_nodes[node_id] = transformation_fn(node)
                
            # Save transformed database
            with open(db_path, 'wb') as f:
                pickle.dump(transformed_nodes, f)
                
            logger.info(f"Successfully migrated database with {len(transformed_nodes)} nodes")
            
            # Update migration log
            self.migration_log['steps'][-1]['completed_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            self.migration_log['steps'][-1]['status'] = 'success'
            self._save_migration_log()
            return True
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            self.migration_log['steps'][-1]['status'] = 'failed'
            self.migration_log['steps'][-1]['error'] = str(e)
            self.migration_log['errors'].append(str(e))
            self._save_migration_log()
            return False
    
    def migrate_faiss_index(self, 
                          coordinate_mapper=None, 
                          dimension_reducer=None) -> bool:
        """
        Migrate the FAISS index to use polar coordinates.
        
        Args:
            coordinate_mapper: Instance of CoordinateMapper for coordinate transformation
            dimension_reducer: Optional dimension reducer for optimizing storage
            
        Returns:
            True if migration was successful, False otherwise
        """
        index_folder = self.storage_path
        index_file = os.path.join(index_folder, "vector_index.faiss")
        pkl_file = os.path.join(index_folder, "vector_index.pkl")
        
        if not os.path.exists(index_file) or not os.path.exists(pkl_file):
            logger.error(f"FAISS index files not found in {index_folder}")
            return False
            
        # Update migration log
        self.migration_log['status'] = 'faiss_migration_in_progress'
        self.migration_log['steps'].append({
            'name': 'faiss_migration',
            'started_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'files': [index_file, pkl_file]
        })
        self._save_migration_log()
        
        try:
            # This migration requires specialized handling via the main application
            # Just log the requirement here
            logger.info(f"FAISS index migration requires specialized handling")
            logger.info(f"Please use the NarrativeAtlas's migration methods to update FAISS indexes")
            
            if coordinate_mapper is None:
                logger.warning("No coordinate mapper provided for FAISS migration")
            if dimension_reducer is None:
                logger.info("No dimension reducer provided, using original dimensions")
                
            # Mark as requires attention
            self.migration_log['steps'][-1]['completed_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            self.migration_log['steps'][-1]['status'] = 'requires_attention'
            self.migration_log['steps'][-1]['message'] = "FAISS migration requires specialized handling via NarrativeAtlas"
            self._save_migration_log()
            return False  # Return False to indicate special handling required
        except Exception as e:
            logger.error(f"FAISS migration preparation failed: {e}")
            self.migration_log['steps'][-1]['status'] = 'failed'
            self.migration_log['steps'][-1]['error'] = str(e)
            self.migration_log['errors'].append(str(e))
            self._save_migration_log()
            return False
    
    def rollback(self) -> bool:
        """
        Rollback to the backup data.
        
        Returns:
            True if rollback was successful, False otherwise
        """
        if not os.path.exists(self.backup_path):
            logger.error(f"Backup path does not exist for rollback: {self.backup_path}")
            return False
            
        # Update migration log
        self.migration_log['status'] = 'rollback_in_progress'
        self.migration_log['steps'].append({
            'name': 'rollback',
            'started_at': time.strftime('%Y-%m-%d %H:%M:%S')
        })
        self._save_migration_log()
        
        try:
            # Create a temporary directory for the current state
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            temp_path = f"{self.storage_path}_pre_rollback_{timestamp}"
            
            # Move current state to temporary location
            if os.path.exists(self.storage_path):
                shutil.move(self.storage_path, temp_path)
                logger.info(f"Moved current state to: {temp_path}")
                
            # Create storage directory
            os.makedirs(self.storage_path, exist_ok=True)
            
            # Copy backup to storage path
            for root, dirs, files in os.walk(self.backup_path):
                # Skip the migration log file
                if os.path.basename(root) == os.path.basename(self.backup_path) and 'migration_log.json' in files:
                    files.remove('migration_log.json')
                    
                # Calculate relative path
                rel_path = os.path.relpath(root, self.backup_path)
                target_dir = os.path.join(self.storage_path, rel_path) if rel_path != '.' else self.storage_path
                
                # Create target directory
                os.makedirs(target_dir, exist_ok=True)
                
                # Copy each file
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(target_dir, file)
                    shutil.copy2(src_file, dst_file)
                    logger.debug(f"Restored: {src_file} -> {dst_file}")
                    
            logger.info(f"Successfully rolled back to backup")
            
            # Update migration log
            self.migration_log['steps'][-1]['completed_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            self.migration_log['steps'][-1]['status'] = 'success'
            self.migration_log['status'] = 'rolled_back'
            self._save_migration_log()
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            self.migration_log['steps'][-1]['status'] = 'failed'
            self.migration_log['steps'][-1]['error'] = str(e)
            self.migration_log['errors'].append(str(e))
            self.migration_log['status'] = 'rollback_failed'
            self._save_migration_log()
            return False
    
    def finalize_migration(self) -> bool:
        """
        Mark the migration as completed.
        
        Returns:
            True if finalization was successful, False otherwise
        """
        # Update migration log
        self.migration_log['completed_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.migration_log['status'] = 'completed'
        self._save_migration_log()
        
        logger.info(f"Migration finalized. Log saved to: {self.migration_log_file}")
        return True
    
    def _save_migration_log(self):
        """Save the current migration log to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.migration_log_file), exist_ok=True)
            
            with open(self.migration_log_file, 'w') as f:
                json.dump(self.migration_log, f, indent=2)
                
            logger.debug(f"Updated migration log at: {self.migration_log_file}")
        except Exception as e:
            logger.error(f"Failed to save migration log: {e}")
    
    @staticmethod
    def transform_to_polar_coordinates(node: Dict, coordinate_mapper=None) -> Dict:
        """
        Transform a node to use polar coordinates.
        
        Args:
            node: Node dictionary to transform
            coordinate_mapper: CoordinateMapper instance for coordinate transformation
            
        Returns:
            Transformed node dictionary
        """
        # If node already has polar coordinates, return as is
        if 'coordinates' in node and isinstance(node['coordinates'], Dict) and 'r' in node['coordinates']:
            return node
            
        # Handle case where node has no embedding or coordinate_mapper is not provided
        if 'embedding' not in node or node['embedding'] is None or coordinate_mapper is None:
            return node
            
        try:
            # Extract metadata for coordinate transformation
            metadata = node.get('metadata', {})
            
            # Create default metadata for temporal coordinate if not present
            if 'page_number' not in metadata and 'temporal_coordinate' in node:
                metadata['page_number'] = int(node['temporal_coordinate']) + 1
                metadata['chunk_index_on_page'] = 0
                metadata['total_chunks_on_page'] = 1
            
            # Transform embedding to polar coordinates
            embedding_array = np.array(node['embedding'])
            polar_coord = coordinate_mapper.transform_vector_to_polar_temporal(
                embedding=embedding_array,
                metadata=metadata
            )
            
            # Update node with polar coordinates
            node['coordinates'] = polar_coord.to_dict()
            
            # Add mapping details if not present
            if 'mapping_details' not in node:
                node['mapping_details'] = {
                    'calculation_method': 'embedding-based',
                    'temporal_basis': f"page {metadata.get('page_number', 0)} chunk {metadata.get('chunk_index_on_page', 0)}",
                    'radial_basis': f"embedding magnitude radius {polar_coord.r}",
                    'angular_basis': f"embedding direction angle {polar_coord.theta}",
                    'z_basis': f"{polar_coord.z_type} -> z={polar_coord.z}"
                }
                
            return node
        except Exception as e:
            logger.error(f"Failed to transform node to polar coordinates: {e}")
            return node  # Return original node if transformation fails
            
def backup_and_migrate(storage_path: str, 
                      coordinate_mapper=None, 
                      dimension_reducer=None,
                      selective_backup: bool = False,
                      finalize: bool = True) -> Optional[DataMigrator]:
    """
    Perform a backup and migration to polar coordinates.
    
    Args:
        storage_path: Path to the data storage directory
        coordinate_mapper: CoordinateMapper instance for coordinate transformation
        dimension_reducer: Optional DimensionReducer for optimizing storage
        selective_backup: If True, only backup essential files
        finalize: If True, finalize the migration after completion
        
    Returns:
        DataMigrator instance if successful, None otherwise
    """
    try:
        # Create migrator
        migrator = DataMigrator(storage_path)
        logger.info(f"Created data migrator for {storage_path}")
        
        # Create backup
        include_patterns = [".pkl", ".faiss", ".json"] if selective_backup else None
        if not migrator.create_backup(selective=selective_backup, include_patterns=include_patterns):
            logger.error("Backup failed, aborting migration")
            return None
            
        # Define transformation function
        def transform_node(node):
            return DataMigrator.transform_to_polar_coordinates(node, coordinate_mapper)
            
        # Migrate database
        if not migrator.migrate_database(transform_node):
            logger.error("Database migration failed")
            if not migrator.rollback():
                logger.error("Rollback failed, manual intervention required")
            return None
            
        # Migrate FAISS index (requires special handling)
        migrator.migrate_faiss_index(coordinate_mapper, dimension_reducer)
        logger.info("FAISS migration requires specialized handling via main application")
        
        # Finalize migration if requested
        if finalize:
            migrator.finalize_migration()
            
        return migrator
    except Exception as e:
        logger.error(f"Migration process failed: {e}")
        return None 