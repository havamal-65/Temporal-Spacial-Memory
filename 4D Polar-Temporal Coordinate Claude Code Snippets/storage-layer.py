"""
Storage Layer for 4D Polar-Temporal Database

This module implements the tiered storage system for the 4D polar-temporal database.
It manages hot, warm, and cold storage tiers with different performance characteristics,
and provides seamless persistence and retrieval of data across tiers.
"""

import os
import json
import pickle
import sqlite3
import time
import redis
import psycopg2
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any, Set
from datetime import datetime
import threading
import logging
from timescale.db import TimescaleDBClient  # Hypothetical TimescaleDB client


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('4D_Storage')


class StorageManager:
    """
    Manages tiered storage for the 4D polar-temporal database.
    """
    
    def __init__(self,
                 redis_host: str = 'localhost',
                 redis_port: int = 6379,
                 timescale_conn_str: str = 'postgresql://user:password@localhost:5432/timescaledb',
                 postgres_conn_str: str = 'postgresql://user:password@localhost:5432/postgres',
                 storage_path: str = './storage',
                 hot_cache_size: int = 10000,
                 warm_cache_size: int = 100000,
                 use_compression: bool = True):
        """
        Initialize the storage manager.
        
        Args:
            redis_host: Redis server hostname for hot tier
            redis_port: Redis server port
            timescale_conn_str: TimescaleDB connection string for warm tier
            postgres_conn_str: PostgreSQL connection string for cold tier
            storage_path: Path for file-based storage
            hot_cache_size: Maximum items in hot cache
            warm_cache_size: Maximum items in warm cache
            use_compression: Whether to use compression for storage
        """
        self.storage_path = storage_path
        self.hot_cache_size = hot_cache_size
        self.warm_cache_size = warm_cache_size
        self.use_compression = use_compression
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        # Connect to Redis for hot tier
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=False  # We need binary data for pickled objects
            )
            self.redis_available = True
            logger.info("Connected to Redis for hot storage tier")
        except Exception as e:
            logger.warning(f"Redis connection failed, hot tier will use in-memory fallback: {e}")
            self.redis_client = None
            self.redis_available = False
            # Use in-memory dictionary as fallback
            self.memory_cache = {}
            
        # Connect to TimescaleDB for warm tier
        try:
            self.timescale_client = TimescaleDBClient(timescale_conn_str)
            self.timescale_available = True
            logger.info("Connected to TimescaleDB for warm storage tier")
        except Exception as e:
            logger.warning(f"TimescaleDB connection failed, warm tier will use SQLite fallback: {e}")
            self.timescale_client = None
            self.timescale_available = False
            # Use SQLite as fallback
            sqlite_path = os.path.join(storage_path, 'warm_tier.db')
            self.sqlite_conn = sqlite3.connect(sqlite_path, check_same_thread=False)
            self.sqlite_cursor = self.sqlite_conn.cursor()
            self._initialize_sqlite()
            
        # Connect to PostgreSQL for cold tier
        try:
            self.pg_conn = psycopg2.connect(postgres_conn_str)
            self.pg_cursor = self.pg_conn.cursor()
            self.postgres_available = True
            self._initialize_postgres()
            logger.info("Connected to PostgreSQL for cold storage tier")
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed, cold tier will use file-based fallback: {e}")
            self.pg_conn = None
            self.pg_cursor = None
            self.postgres_available = False
            
        # In-memory structures for tracking item locations
        self.item_locations = {}  # item_id -> {'tier': 'hot|warm|cold', 'expires': timestamp}
        
        # Access counts for LRU eviction
        self.access_counts = {}
        self.access_lock = threading.Lock()
        
        # Storage statistics
        self.stats = {
            'hot_items': 0,
            'warm_items': 0,
            'cold_items': 0,
            'hot_hits': 0,
            'warm_hits': 0,
            'cold_hits': 0,
            'promotions': 0,
            'demotions': 0
        }
        
    def _initialize_sqlite(self):
        """
        Initialize SQLite database for warm tier fallback.
        """
        # Create items table
        self.sqlite_cursor.execute('''
        CREATE TABLE IF NOT EXISTS warm_items (
            id TEXT PRIMARY KEY,
            content BLOB,
            coordinates TEXT,
            metadata TEXT,
            access_time REAL,
            access_count INTEGER
        )
        ''')
        
        # Create indexes
        self.sqlite_cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_access_time ON warm_items(access_time)
        ''')
        
        self.sqlite_conn.commit()
        logger.info("Initialized SQLite for warm tier fallback")
        
    def _initialize_postgres(self):
        """
        Initialize PostgreSQL database for cold tier.
        """
        # Create extension for PostGIS if available
        try:
            self.pg_cursor.execute('CREATE EXTENSION IF NOT EXISTS postgis')
            self.postgis_available = True
        except Exception:
            self.postgis_available = False
            
        # Create extension for temporal queries if available
        try:
            self.pg_cursor.execute('CREATE EXTENSION IF NOT EXISTS timescaledb')
            self.pg_timescale_available = True
        except Exception:
            self.pg_timescale_available = False
            
        # Create schema
        self.pg_cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            r FLOAT,
            theta FLOAT,
            t FLOAT,
            z INTEGER,
            content TEXT,
            embedding BYTEA,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP
        )
        ''')
        
        # Create indexes
        self.pg_cursor.execute('CREATE INDEX IF NOT EXISTS idx_r ON items(r)')
        self.pg_cursor.execute('CREATE INDEX IF NOT EXISTS idx_theta ON items(theta)')
        self.pg_cursor.execute('CREATE INDEX IF NOT EXISTS idx_t ON items(t)')
        self.pg_cursor.execute('CREATE INDEX IF NOT EXISTS idx_z ON items(z)')
        self.pg_cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON items(last_accessed)')
        
        # Create PostGIS index if available
        if self.postgis_available:
            # Add geometry column for polar coordinates
            self.pg_cursor.execute('''
            ALTER TABLE items 
            ADD COLUMN IF NOT EXISTS geom geometry(POINT, 4326)
            ''')
            
            # Create spatial index
            self.pg_cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_geom ON items USING GIST(geom)
            ''')
            
        self.pg_conn.commit()
        logger.info("Initialized PostgreSQL for cold storage tier")
        
    def store_item(self,
                 item_id: str,
                 content: str,
                 coordinates: Dict[str, float],
                 metadata: Dict[str, Any] = None,
                 embedding: Optional[np.ndarray] = None,
                 tier: str = 'auto') -> None:
        """
        Store an item in the database.
        
        Args:
            item_id: Unique identifier for the item
            content: Text content of the item
            coordinates: 4D coordinates (r, theta, t, z)
            metadata: Optional metadata
            embedding: Optional vector embedding
            tier: Storage tier ('hot', 'warm', 'cold', or 'auto')
        """
        # Validate coordinates
        required_coords = ['r', 'theta', 't', 'z']
        if not all(key in coordinates for key in required_coords):
            raise ValueError(f"Coordinates must include all of: {required_coords}")
            
        # Prepare item data
        item_data = {
            'id': item_id,
            'content': content,
            'coordinates': coordinates,
            'metadata': metadata or {},
            'embedding': embedding.tobytes() if embedding is not None else None,
            'timestamp': time.time()
        }
        
        # Determine storage tier if auto
        if tier == 'auto':
            # Use temporal recency to help determine tier
            current_time = time.time()
            item_time = coordinates['t']
            time_age = current_time - item_time
            
            # Recent items go to hot tier, older to warm or cold
            if time_age < 7 * 86400:  # Less than a week old
                tier = 'hot'
            elif time_age < 90 * 86400:  # Less than 3 months old
                tier = 'warm'
            else:
                tier = 'cold'
                
        # Store based on tier
        if tier == 'hot':
            self._store_hot(item_id, item_data)
        elif tier == 'warm':
            self._store_warm(item_id, item_data)
        else:
            self._store_cold(item_id, item_data)
            
        # Update item location tracking
        self.item_locations[item_id] = {
            'tier': tier,
            'expires': time.time() + self._get_tier_ttl(tier)
        }
        
        # Update statistics
        self._update_stats(f"{tier}_items", 1)
        
    def _store_hot(self, item_id: str, item_data: Dict[str, Any]) -> None:
        """
        Store an item in the hot tier (Redis or in-memory).
        
        Args:
            item_id: Item ID
            item_data: Item data dictionary
        """
        # Serialize data
        serialized = pickle.dumps(item_data)
        
        if self.redis_available:
            # Store in Redis with TTL
            ttl = self._get_tier_ttl('hot')
            self.redis_client.setex(f"item:{item_id}", ttl, serialized)
            logger.debug(f"Stored item {item_id} in hot tier (Redis)")
        else:
            # Store in memory cache
            self.memory_cache[item_id] = item_data
            logger.debug(f"Stored item {item_id} in hot tier (memory)")
            
            # Check if we need to evict items
            if len(self.memory_cache) > self.hot_cache_size:
                self._evict_from_memory_cache()
                
    def _store_warm(self, item_id: str, item_data: Dict[str, Any]) -> None:
        """
        Store an item in the warm tier (TimescaleDB or SQLite).
        
        Args:
            item_id: Item ID
            item_data: Item data dictionary
        """
        if self.timescale_available:
            # Store in TimescaleDB
            coordinates = item_data['coordinates']
            self.timescale_client.insert_item(
                item_id=item_id,
                content=item_data['content'],
                r=coordinates['r'],
                theta=coordinates['theta'],
                t=coordinates['t'],
                z=coordinates['z'],
                metadata=json.dumps(item_data['metadata']),
                embedding=item_data['embedding'],
                timestamp=item_data['timestamp']
            )
            logger.debug(f"Stored item {item_id} in warm tier (TimescaleDB)")
        else:
            # Store in SQLite
            serialized_content = pickle.dumps(item_data['content'])
            coordinates_json = json.dumps(item_data['coordinates'])
            metadata_json = json.dumps(item_data['metadata'])
            
            self.sqlite_cursor.execute(
                "INSERT OR REPLACE INTO warm_items (id, content, coordinates, metadata, access_time, access_count) VALUES (?, ?, ?, ?, ?, ?)",
                (item_id, serialized_content, coordinates_json, metadata_json, time.time(), 0)
            )
            self.sqlite_conn.commit()
            logger.debug(f"Stored item {item_id} in warm tier (SQLite)")
            
    def _store_cold(self, item_id: str, item_data: Dict[str, Any]) -> None:
        """
        Store an item in the cold tier (PostgreSQL or files).
        
        Args:
            item_id: Item ID
            item_data: Item data dictionary
        """
        if self.postgres_available:
            # Store in PostgreSQL
            coordinates = item_data['coordinates']
            
            # Convert embedding to postgres binary format if present
            embedding_binary = (
                psycopg2.Binary(item_data['embedding']) 
                if item_data['embedding'] is not None else None
            )
            
            # Insert or update
            self.pg_cursor.execute(
                """
                INSERT INTO items (id, r, theta, t, z, content, embedding, metadata, last_accessed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    r = excluded.r,
                    theta = excluded.theta,
                    t = excluded.t,
                    z = excluded.z,
                    content = excluded.content,
                    embedding = excluded.embedding,
                    metadata = excluded.metadata,
                    last_accessed = NOW()
                """,
                (
                    item_id,
                    coordinates['r'],
                    coordinates['theta'],
                    coordinates['t'],
                    coordinates['z'],
                    item_data['content'],
                    embedding_binary,
                    json.dumps(item_data['metadata']),
                )
            )
            
            # Update geometry if PostGIS is available
            if self.postgis_available:
                # Convert polar to cartesian for storage
                # r and theta become x,y in a 2D plane
                x = coordinates['r'] * np.cos(coordinates['theta'])
                y = coordinates['r'] * np.sin(coordinates['theta'])
                
                self.pg_cursor.execute(
                    """
                    UPDATE items SET geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    WHERE id = %s
                    """,
                    (x, y, item_id)
                )
                
            self.pg_conn.commit()
            logger.debug(f"Stored item {item_id} in cold tier (PostgreSQL)")
        else:
            # Store as file
            file_path = os.path.join(self.storage_path, f"{item_id}.pickle")
            
            with open(file_path, 'wb') as f:
                pickle.dump(item_data, f)
                
            logger.debug(f"Stored item {item_id} in cold tier (file)")
            
    def get_item(self, item_id: str, promote: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from any tier.
        
        Args:
            item_id: Item ID to retrieve
            promote: Whether to promote the item to a higher tier on access
            
        Returns:
            Item data or None if not found
        """
        # Check item location if known
        known_location = self.item_locations.get(item_id)
        if known_location:
            tier = known_location['tier']
            
            # Check if location is expired
            if time.time() > known_location['expires']:
                # Location may have changed, clear it
                logger.debug(f"Location for {item_id} expired, searching all tiers")
                tier = None
            else:
                logger.debug(f"Using known location for {item_id}: {tier} tier")
        else:
            tier = None
            
        # Try retrieving from specific tier if known
        if tier == 'hot':
            item = self._get_hot(item_id)
            if item:
                self._update_stats('hot_hits', 1)
                return item
                
        if tier == 'warm' or tier is None:
            item = self._get_warm(item_id)
            if item:
                self._update_stats('warm_hits', 1)
                if promote:
                    self._promote_to_hot(item_id, item)
                return item
                
        if tier == 'cold' or tier is None:
            item = self._get_cold(item_id)
            if item:
                self._update_stats('cold_hits', 1)
                if promote:
                    self._promote_to_warm(item_id, item)
                return item
                
        # If we reached here and didn't find the item in 'hot', check it as a fallback
        if tier != 'hot' and tier is not None:
            item = self._get_hot(item_id)
            if item:
                self._update_stats('hot_hits', 1)
                return item
                
        # Item not found
        logger.debug(f"Item {item_id} not found in any tier")
        return None
        
    def _get_hot(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the hot tier.
        
        Args:
            item_id: Item ID
            
        Returns:
            Item data or None if not found
        """
        if self.redis_available:
            # Try Redis
            serialized = self.redis_client.get(f"item:{item_id}")
            if serialized:
                try:
                    # Update TTL on access
                    ttl = self._get_tier_ttl('hot')
                    self.redis_client.expire(f"item:{item_id}", ttl)
                    
                    # Deserialize and return
                    return pickle.loads(serialized)
                except Exception as e:
                    logger.error(f"Error deserializing item {item_id} from Redis: {e}")
                    return None
        else:
            # Try memory cache
            item = self.memory_cache.get(item_id)
            if item:
                # Update access time
                item['timestamp'] = time.time()
                
                # Update access count
                with self.access_lock:
                    self.access_counts[item_id] = self.access_counts.get(item_id, 0) + 1
                    
                return item
                
        return None
        
    def _get_warm(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the warm tier.
        
        Args:
            item_id: Item ID
            
        Returns:
            Item data or None if not found
        """
        if self.timescale_available:
            # Try TimescaleDB
            item = self.timescale_client.get_item(item_id)
            if item:
                # Update access time
                self.timescale_client.update_access_time(item_id)
                
                # Convert to standard format
                return self._convert_timescale_to_item(item)
        else:
            # Try SQLite
            self.sqlite_cursor.execute(
                "SELECT content, coordinates, metadata FROM warm_items WHERE id = ?",
                (item_id,)
            )
            row = self.sqlite_cursor.fetchone()
            
            if row:
                try:
                    # Update access count and time
                    self.sqlite_cursor.execute(
                        "UPDATE warm_items SET access_time = ?, access_count = access_count + 1 WHERE id = ?",
                        (time.time(), item_id)
                    )
                    self.sqlite_conn.commit()
                    
                    # Deserialize and return
                    content = pickle.loads(row[0])
                    coordinates = json.loads(row[1])
                    metadata = json.loads(row[2])
                    
                    return {
                        'id': item_id,
                        'content': content,
                        'coordinates': coordinates,
                        'metadata': metadata,
                        'timestamp': time.time()
                    }
                except Exception as e:
                    logger.error(f"Error deserializing item {item_id} from SQLite: {e}")
                    return None
                    
        return None
        
    def _get_cold(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the cold tier.
        
        Args:
            item_id: Item ID
            
        Returns:
            Item data or None if not found
        """
        if self.postgres_available:
            # Try PostgreSQL
            self.pg_cursor.execute(
                """
                SELECT r, theta, t, z, content, embedding, metadata, last_accessed
                FROM items WHERE id = %s
                """,
                (item_id,)
            )
            row = self.pg_cursor.fetchone()
            
            if row:
                # Update access time
                self.pg_cursor.execute(
                    "UPDATE items SET last_accessed = NOW() WHERE id = %s",
                    (item_id,)
                )
                self.pg_conn.commit()
                
                # Convert to standard format
                r, theta, t, z, content, embedding_binary, metadata_json, _ = row
                
                coordinates = {
                    'r': r,
                    'theta': theta,
                    't': t,
                    'z': z
                }
                
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                embedding = None
                if embedding_binary:
                    try:
                        embedding = np.frombuffer(embedding_binary, dtype=np.float32)
                    except Exception as e:
                        logger.error(f"Error parsing embedding for {item_id}: {e}")
                        
                return {
                    'id': item_id,
                    'content': content,
                    'coordinates': coordinates,
                    'metadata': metadata,
                    'embedding': embedding,
                    'timestamp': time.time()
                }
        else:
            # Try file-based storage
            file_path = os.path.join(self.storage_path, f"{item_id}.pickle")
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        return pickle.load(f)
                except Exception as e:
                    logger.error(f"Error loading item {item_id} from file: {e}")
                    return None
                    
        return None
        
    def _promote_to_hot(self, item_id: str, item_data: Dict[str, Any]) -> None:
        """
        Promote an item to the hot tier.
        
        Args:
            item_id: Item ID
            item_data: Item data
        """
        logger.debug(f"Promoting item {item_id} to hot tier")
        self._store_hot(item_id, item_data)
        
        # Update item location tracking
        self.item_locations[item_id] = {
            'tier': 'hot',
            'expires': time.time() + self._get_tier_ttl('hot')
        }
        
        # Update statistics
        self._update_stats('promotions', 1)
        
    def _promote_to_warm(self, item_id: str, item_data: Dict[str, Any]) -> None:
        """
        Promote an item to the warm tier.
        
        Args:
            item_id: Item ID
            item_data: Item data
        """
        logger.debug(f"Promoting item {item_id} to warm tier")
        self._store_warm(item_id, item_data)
        
        # Update item location tracking
        self.item_locations[item_id] = {
            'tier': 'warm',
            'expires': time.time() + self._get_tier_ttl('warm')
        }
        
        # Update statistics
        self._update_stats('promotions', 1)
        
    def _evict_from_memory_cache(self) -> None:
        """
        Evict least recently used items from memory cache.
        """
        # If less than 80% full, don't evict
        if len(self.memory_cache) < self.hot_cache_size * 0.8:
            return
            
        # Get items sorted by access time
        sorted_items = sorted(
            self.memory_cache.items(),
            key=lambda x: (self.access_counts.get(x[0], 0), x[1].get('timestamp', 0))
        )
        
        # Remove bottom 20%
        items_to_remove = sorted_items[:int(self.hot_cache_size * 0.2)]
        
        for item_id, item_data in items_to_remove:
            # Move to warm tier before removing
            self._store_warm(item_id, item_data)
            
            # Remove from hot tier
            del self.memory_cache[item_id]
            
            # Update location tracking
            self.item_locations[item_id] = {
                'tier': 'warm',
                'expires': time.time() + self._get_tier_ttl('warm')
            }
            
            # Update statistics
            self._update_stats('demotions', 1)
            
        logger.info(f"Evicted {len(items_to_remove)} items from hot tier to warm tier")
        
    def _get_tier_ttl(self, tier: str) -> int:
        """
        Get the time-to-live for a tier.
        
        Args:
            tier: Storage tier
            
        Returns:
            TTL in seconds
        """
        if tier == 'hot':
            return 3600  # 1 hour
        elif tier == 'warm':
            return 86400  # 1 day
        else:
            return 604800  # 1 week
            
    def _update_stats(self, stat_name: str, increment: int = 1) -> None:
        """
        Update usage statistics.
        
        Args:
            stat_name: Statistic name
            increment: Increment amount
        """
        if stat_name in self.stats:
            self.stats[stat_name] += increment
            
    def _convert_timescale_to_item(self, timescale_item) -> Dict[str, Any]:
        """
        Convert TimescaleDB item format to standard format.
        
        Args:
            timescale_item: Item from TimescaleDB
            
        Returns:
            Standardized item
        """
        # This would depend on the actual TimescaleDB client implementation
        return {
            'id': timescale_item['id'],
            'content': timescale_item['content'],
            'coordinates': {
                'r': timescale_item['r'],
                'theta': timescale_item['theta'],
                't': timescale_item['t'],
                'z': timescale_item['z']
            },
            'metadata': timescale_item['metadata'],
            'embedding': timescale_item.get('embedding'),
            'timestamp': timescale_item['timestamp']
        }
        
    def query_items(self,
                   r_min: float = 0,
                   r_max: float = float('inf'),
                   theta_min: float = 0,
                   theta_max: float = 2 * np.pi,
                   t_min: Optional[float] = None,
                   t_max: Optional[float] = None,
                   z: Optional[int] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query items based on coordinate constraints.
        
        Args:
            r_min, r_max: Radial range
            theta_min, theta_max: Angular range
            t_min, t_max: Temporal range
            z: Context layer
            limit: Maximum number of results
            
        Returns:
            List of matching items
        """
        results = []
        
        # Build the query differently for each storage tier
        if self.postgres_available:
            # Use PostgreSQL for primary query
            query = """
            SELECT id, r, theta, t, z, content, metadata
            FROM items
            WHERE r BETWEEN %s AND %s
            """
            params = [r_min, r_max]
            
            # Handle angular wrapping
            if theta_min <= theta_max:
                query += " AND theta BETWEEN %s AND %s"
                params.extend([theta_min, theta_max])
            else:
                query += " AND (theta >= %s OR theta <= %s)"
                params.extend([theta_min, theta_max])
                
            # Add temporal constraints if specified
            if t_min is not None:
                query += " AND t >= %s"
                params.append(t_min)
            if t_max is not None:
                query += " AND t <= %s"
                params.append(t_max)
                
            # Add context layer constraint if specified
            if z is not None:
                query += " AND z = %s"
                params.append(z)
                
            # Add limit
            query += " ORDER BY last_accessed DESC LIMIT %s"
            params.append(limit)
            
            # Execute query
            self.pg_cursor.execute(query, params)
            
            # Process results
            for row in self.pg_cursor.fetchall():
                item_id, r, theta, t, z, content, metadata_json = row
                
                # Build item data
                item = {
                    'id': item_id,
                    'content': content,
                    'coordinates': {
                        'r': r,
                        'theta': theta,
                        't': t,
                        'z': z
                    },
                    'metadata': json.loads(metadata_json) if metadata_json else {}
                }
                
                results.append(item)
                
        else:
            # Fallback to scanning warm and cold tiers
            # This is less efficient but works without PostgreSQL
            
            # Check warm tier via SQLite
            if not self.timescale_available:
                # Query SQLite warm tier
                self.sqlite_cursor.execute(
                    "SELECT id, content, coordinates, metadata FROM warm_items ORDER BY access_time DESC LIMIT ?",
                    (limit * 2,)  # Get more items to filter locally
                )
                
                for row in self.sqlite_cursor.fetchall():
                    try:
                        item_id, content_blob, coordinates_json, metadata_json = row
                        content = pickle.loads(content_blob)
                        coordinates = json.loads(coordinates_json)
                        metadata = json.loads(metadata_json)
                        
                        # Check constraints
                        if self._matches_constraints(
                            coordinates, r_min, r_max, theta_min, theta_max, t_min, t_max, z):
                            
                            results.append({
                                'id': item_id,
                                'content': content,
                                'coordinates': coordinates,
                                'metadata': metadata
                            })
                    except Exception as e:
                        logger.error(f"Error processing warm tier item: {e}")
                        
            # Check file-based cold tier if needed
            if len(results) < limit:
                # Scan files in storage directory
                for filename in os.listdir(self.storage_path):
                    if filename.endswith('.pickle'):
                        try:
                            file_path = os.path.join(self.storage_path, filename)
                            with open(file_path, 'rb') as f:
                                item = pickle.load(f)
                                
                            # Check constraints
                            if self._matches_constraints(
                                item['coordinates'], r_min, r_max, theta_min, theta_max, t_min, t_max, z):
                                
                                results.append(item)
                                
                                # Check limit
                                if len(results) >= limit:
                                    break
                        except Exception as e:
                            logger.error(f"Error processing cold tier file: {e}")
                            
        # Ensure we don't exceed limit
        return results[:limit]
        
    def _matches_constraints(self,
                           coordinates: Dict[str, float],
                           r_min: float,
                           r_max: float,
                           theta_min: float,
                           theta_max: float,
                           t_min: Optional[float],
                           t_max: Optional[float],
                           z: Optional[int]) -> bool:
        """
        Check if coordinates match the query constraints.
        
        Args:
            coordinates: Item coordinates
            r_min, r_max: Radial range
            theta_min, theta_max: Angular range
            t_min, t_max: Temporal range
            z: Context layer
            
        Returns:
            True if constraints are satisfied
        """
        # Check radial constraint
        r = coordinates.get('r', 0)
        if not (r_min <= r <= r_max):
            return False
            
        # Check angular constraint
        theta = coordinates.get('theta', 0)
        
        # Handle wrapping
        if theta_min <= theta_max:
            if not (theta_min <= theta <= theta_max):
                return False
        else:
            if not (theta >= theta_min or theta <= theta_max):
                return False
                
        # Check temporal constraint
        t = coordinates.get('t', 0)
        if t_min is not None and t < t_min:
            return False
        if t_max is not None and t > t_max:
            return False
            
        # Check context layer
        if z is not None and coordinates.get('z', 0) != z:
            return False
            
        return True
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary of storage statistics
        """
        # Update current counts
        if self.redis_available:
            redis_keys = self.redis_client.keys("item:*")
            self.stats['hot_items'] = len(redis_keys)
        else:
            self.stats['hot_items'] = len(self.memory_cache)
            
        # Add additional stats
        self.stats['total_items'] = sum([
            self.stats['hot_items'],
            self.stats['warm_items'],
            self.stats['cold_items']
        ])
        
        # Calculate hit rates
        total_hits = sum([
            self.stats['hot_hits'],
            self.stats['warm_hits'],
            self.stats['cold_hits']
        ])
        
        if total_hits > 0:
            self.stats['hot_hit_rate'] = self.stats['hot_hits'] / total_hits
            self.stats['warm_hit_rate'] = self.stats['warm_hits'] / total_hits
            self.stats['cold_hit_rate'] = self.stats['cold_hits'] / total_hits
        else:
            self.stats['hot_hit_rate'] = 0
            self.stats['warm_hit_rate'] = 0
            self.stats['cold_hit_rate'] = 0
            
        return self.stats
        
    def close(self) -> None:
        """
        Close all connections and clean up resources.
        """
        # Close Redis connection
        if self.redis_available:
            self.redis_client.close()
            
        # Close SQLite connection
        if not self.timescale_available:
            self.sqlite_conn.close()
            
        # Close PostgreSQL connection
        if self.postgres_available:
            self.pg_conn.close()
            
        logger.info("All storage connections closed")


# Example usage with mock TimescaleDB class
class TimescaleDBClient:
    """Mock TimescaleDB client for example purposes"""
    
    def __init__(self, conn_str):
        self.conn_str = conn_str
        self.items = {}
        
    def insert_item(self, item_id, content, r, theta, t, z, metadata, embedding, timestamp):
        """Mock insert method"""
        self.items[item_id] = {
            'id': item_id,
            'content': content,
            'r': r,
            'theta': theta,
            't': t,
            'z': z,
            'metadata': json.loads(metadata) if isinstance(metadata, str) else metadata,
            'embedding': embedding,
            'timestamp': timestamp
        }
        
    def get_item(self, item_id):
        """Mock get method"""
        return self.items.get(item_id)
        
    def update_access_time(self, item_id):
        """Mock update access time method"""
        if item_id in self.items:
            self.items[item_id]['timestamp'] = time.time()


# Example usage
if __name__ == "__main__":
    # Initialize storage manager with local settings
    storage = StorageManager(
        redis_host='localhost',
        redis_port=6379,
        storage_path='./storage_test',
        hot_cache_size=100,
        warm_cache_size=1000,
        use_compression=True
    )
    
    # Create test items
    for i in range(10):
        item_id = f"test_item_{i}"
        content = f"This is test content for item {i}"
        
        # Create coordinates with varying values
        r = (i % 3) + 0.5
        theta = (i / 10) * 2 * np.pi
        t = time.time() - (i * 86400)  # Varying ages
        z = (i % 3) + 1
        
        # Add metadata
        metadata = {
            'title': f"Test Item {i}",
            'tags': [f"tag_{j}" for j in range(i % 5)]
        }
        
        # Store with different tiers
        if i < 3:
            tier = 'hot'
        elif i < 7:
            tier = 'warm'
        else:
            tier = 'cold'
            
        # Store the item
        storage.store_item(
            item_id=item_id,
            content=content,
            coordinates={'r': r, 'theta': theta, 't': t, 'z': z},
            metadata=metadata,
            tier=tier
        )
        
    # Test retrieval
    print("\nTesting retrieval:")
    for i in range(10):
        item_id = f"test_item_{i}"
        item = storage.get_item(item_id, promote=True)
        
        if item:
            print(f"Retrieved {item_id} from storage")
        else:
            print(f"Failed to retrieve {item_id}")
            
    # Test query
    print("\nTesting query:")
    results = storage.query_items(
        r_min=0,
        r_max=2,
        theta_min=0,
        theta_max=np.pi,
        z=1,
        limit=5
    )
    
    print(f"Query returned {len(results)} items")
    for item in results:
        print(f"  {item['id']}: r={item['coordinates']['r']}, "
              f"θ={item['coordinates']['theta']}, z={item['coordinates']['z']}")
        
    # Show stats
    print("\nStorage statistics:")
    stats = storage.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
        
    # Clean up
    storage.close()