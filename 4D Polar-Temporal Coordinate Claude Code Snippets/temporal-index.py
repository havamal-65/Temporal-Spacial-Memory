"""
Temporal Index for 4D Polar-Temporal Database

This module implements specialized indexing for the temporal dimension (t).
It provides efficient querying for time ranges, temporal navigation,
and supports variable time-scale compression/expansion.
"""

import numpy as np
import bisect
import sqlite3
import pickle
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime
import time
import json
import os


class TemporalIndex:
    """
    Specialized index for the temporal dimension of the 4D database.
    """
    
    def __init__(self, 
                 in_memory: bool = False,
                 db_path: str = 'temporal_index.db',
                 use_compression: bool = True):
        """
        Initialize the temporal index.
        
        Args:
            in_memory: Whether to use an in-memory database
            db_path: Path to SQLite database file (if not in-memory)
            use_compression: Whether to use temporal compression
        """
        self.in_memory = in_memory
        self.db_path = db_path
        self.use_compression = use_compression
        
        # Connect to database
        if in_memory:
            self.conn = sqlite3.connect(':memory:')
        else:
            self.conn = sqlite3.connect(db_path)
            
        self.cursor = self.conn.cursor()
        self.initialize_database()
        
        # In-memory data structures for fast lookups
        self.time_points = []  # Sorted list of time points
        self.time_to_ids = {}  # Mapping from time points to item IDs
        self.id_to_time = {}   # Mapping from item IDs to time points
        
        # Temporal compression parameters
        self.compression_thresholds = []
        self.activity_windows = {}
        
        # Time landmarks for stable reference points
        self.landmarks = {}
        
    def initialize_database(self):
        """
        Initialize the SQLite database schema.
        """
        # Create items table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS temporal_items (
            id TEXT PRIMARY KEY,
            timestamp REAL,
            time_type TEXT,
            compressed_time REAL,
            metadata TEXT
        )
        ''')
        
        # Create index on timestamp
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON temporal_items(timestamp)
        ''')
        
        # Create index on compressed_time
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_compressed_time ON temporal_items(compressed_time)
        ''')
        
        # Create time ranges table (for events spanning time periods)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_ranges (
            id TEXT PRIMARY KEY,
            start_time REAL,
            end_time REAL,
            compressed_start REAL,
            compressed_end REAL,
            metadata TEXT
        )
        ''')
        
        # Create landmarks table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS landmarks (
            landmark_id TEXT PRIMARY KEY,
            timestamp REAL,
            description TEXT
        )
        ''')
        
        self.conn.commit()
        
    def add_item(self, 
                item_id: str, 
                timestamp: float, 
                time_type: str = 'creation',
                metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an item to the temporal index.
        
        Args:
            item_id: Unique identifier for the item
            timestamp: Temporal position (as Unix timestamp)
            time_type: Type of time (creation, modification, reference, etc.)
            metadata: Optional metadata about the temporal aspect
        """
        compressed_time = self.compress_time(timestamp) if self.use_compression else timestamp
        
        # Store in database
        self.cursor.execute(
            "INSERT OR REPLACE INTO temporal_items (id, timestamp, time_type, compressed_time, metadata) VALUES (?, ?, ?, ?, ?)",
            (item_id, timestamp, time_type, compressed_time, json.dumps(metadata or {}))
        )
        self.conn.commit()
        
        # Update in-memory structures
        bisect.insort(self.time_points, timestamp)
        if timestamp not in self.time_to_ids:
            self.time_to_ids[timestamp] = []
        self.time_to_ids[timestamp].append(item_id)
        self.id_to_time[item_id] = timestamp
        
        # Update activity windows for compression
        if self.use_compression:
            self.update_activity_window(timestamp)
            
    def add_time_range(self,
                      item_id: str,
                      start_time: float,
                      end_time: float,
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an item that spans a time range.
        
        Args:
            item_id: Unique identifier for the item
            start_time: Start of time range (as Unix timestamp)
            end_time: End of time range (as Unix timestamp)
            metadata: Optional metadata about the temporal range
        """
        compressed_start = self.compress_time(start_time) if self.use_compression else start_time
        compressed_end = self.compress_time(end_time) if self.use_compression else end_time
        
        # Store in database
        self.cursor.execute(
            "INSERT OR REPLACE INTO time_ranges (id, start_time, end_time, compressed_start, compressed_end, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, start_time, end_time, compressed_start, compressed_end, json.dumps(metadata or {}))
        )
        self.conn.commit()
        
        # Update in-memory structures for start and end points
        bisect.insort(self.time_points, start_time)
        bisect.insort(self.time_points, end_time)
        
        for t in [start_time, end_time]:
            if t not in self.time_to_ids:
                self.time_to_ids[t] = []
            self.time_to_ids[t].append(item_id)
            
        # Store both times for the item
        self.id_to_time[item_id] = (start_time, end_time)
        
        # Update activity windows for compression
        if self.use_compression:
            self.update_activity_window(start_time)
            self.update_activity_window(end_time)
            
    def update_activity_window(self, timestamp: float) -> None:
        """
        Update activity windows used for temporal compression.
        
        Args:
            timestamp: Time point to update
        """
        # Define window size (1 day in seconds)
        window_size = 86400
        
        # Calculate window key
        window_key = int(timestamp / window_size)
        
        # Initialize or increment window counter
        if window_key not in self.activity_windows:
            self.activity_windows[window_key] = 1
        else:
            self.activity_windows[window_key] += 1
            
        # Recalculate compression thresholds if enough new data
        if len(self.activity_windows) % 10 == 0:
            self.recalculate_compression_thresholds()
            
    def recalculate_compression_thresholds(self) -> None:
        """
        Recalculate temporal compression thresholds based on activity density.
        """
        # Sort windows by activity count
        sorted_windows = sorted(
            self.activity_windows.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Get top 20% most active windows
        top_n = max(1, int(len(sorted_windows) * 0.2))
        active_windows = sorted_windows[:top_n]
        
        # Convert window keys back to timestamps and sort
        self.compression_thresholds = sorted([w[0] * 86400 for w in active_windows])
        
    def compress_time(self, timestamp: float) -> float:
        """
        Apply temporal compression to transform a timestamp.
        
        Args:
            timestamp: Original timestamp
            
        Returns:
            Compressed timestamp
        """
        if not self.compression_thresholds:
            return timestamp
            
        # Find which thresholds the timestamp falls between
        idx = bisect.bisect(self.compression_thresholds, timestamp)
        
        # Adjust timestamp based on density
        if idx == 0:
            # Before first threshold - normal time
            return timestamp
        elif idx == len(self.compression_thresholds):
            # After last threshold - normal time
            return timestamp
        else:
            # Between thresholds - compress based on activity
            prev_threshold = self.compression_thresholds[idx - 1]
            next_threshold = self.compression_thresholds[idx]
            
            # Get activity levels
            prev_window = int(prev_threshold / 86400)
            next_window = int(next_threshold / 86400)
            
            prev_activity = self.activity_windows.get(prev_window, 1)
            next_activity = self.activity_windows.get(next_window, 1)
            
            # Calculate compression factor (higher activity = less compression)
            compression_factor = 1.0 - (0.5 * (prev_activity + next_activity) / 
                                       max(self.activity_windows.values()))
            
            # Apply compression: high activity periods expand, low activity periods compress
            time_span = next_threshold - prev_threshold
            position = (timestamp - prev_threshold) / time_span
            
            # Apply non-linear scaling
            if compression_factor < 0.5:
                # Compress this region (low activity)
                adjusted_position = position ** (1.0 / compression_factor)
            else:
                # Expand this region (high activity)
                adjusted_position = position ** compression_factor
                
            # Calculate compressed time
            compressed_time = prev_threshold + (adjusted_position * time_span)
            
            return compressed_time
            
    def decompress_time(self, compressed_time: float) -> float:
        """
        Reverse temporal compression to get original timestamp.
        
        Args:
            compressed_time: Compressed timestamp
            
        Returns:
            Original timestamp
        """
        if not self.compression_thresholds:
            return compressed_time
            
        # Find which thresholds the compressed time falls between
        idx = bisect.bisect(self.compression_thresholds, compressed_time)
        
        # Adjust timestamp based on density
        if idx == 0:
            # Before first threshold - normal time
            return compressed_time
        elif idx == len(self.compression_thresholds):
            # After last threshold - normal time
            return compressed_time
        else:
            # Between thresholds - decompress based on activity
            prev_threshold = self.compression_thresholds[idx - 1]
            next_threshold = self.compression_thresholds[idx]
            
            # Get activity levels
            prev_window = int(prev_threshold / 86400)
            next_window = int(next_threshold / 86400)
            
            prev_activity = self.activity_windows.get(prev_window, 1)
            next_activity = self.activity_windows.get(next_window, 1)
            
            # Calculate compression factor
            compression_factor = 1.0 - (0.5 * (prev_activity + next_activity) / 
                                       max(self.activity_windows.values()))
            
            # Apply decompression
            time_span = next_threshold - prev_threshold
            compressed_position = (compressed_time - prev_threshold) / time_span
            
            # Reverse non-linear scaling
            if compression_factor < 0.5:
                # Decompress this region
                original_position = compressed_position ** compression_factor
            else:
                # Contract this region
                original_position = compressed_position ** (1.0 / compression_factor)
                
            # Calculate original time
            original_time = prev_threshold + (original_position * time_span)
            
            return original_time
            
    def add_landmark(self, 
                    landmark_id: str, 
                    timestamp: float, 
                    description: str) -> None:
        """
        Add a time landmark for stable reference.
        
        Args:
            landmark_id: Unique identifier for the landmark
            timestamp: Time point for the landmark
            description: Description of the landmark
        """
        # Store in database
        self.cursor.execute(
            "INSERT OR REPLACE INTO landmarks (landmark_id, timestamp, description) VALUES (?, ?, ?)",
            (landmark_id, timestamp, description)
        )
        self.conn.commit()
        
        # Update in-memory structure
        self.landmarks[landmark_id] = {
            'timestamp': timestamp,
            'description': description
        }
        
    def get_items_in_time_range(self, 
                               start_time: float, 
                               end_time: float,
                               use_compressed: bool = True) -> List[str]:
        """
        Get items within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            use_compressed: Whether to use compressed time values
            
        Returns:
            List of item IDs within the range
        """
        if use_compressed and self.use_compression:
            # Query using compressed time
            compressed_start = self.compress_time(start_time)
            compressed_end = self.compress_time(end_time)
            
            self.cursor.execute(
                """
                SELECT id FROM temporal_items 
                WHERE compressed_time BETWEEN ? AND ?
                UNION
                SELECT id FROM time_ranges
                WHERE 
                    (compressed_start BETWEEN ? AND ?) OR 
                    (compressed_end BETWEEN ? AND ?) OR
                    (compressed_start <= ? AND compressed_end >= ?)
                """,
                (compressed_start, compressed_end, 
                 compressed_start, compressed_end,
                 compressed_start, compressed_end,
                 compressed_start, compressed_end)
            )
        else:
            # Query using original time
            self.cursor.execute(
                """
                SELECT id FROM temporal_items 
                WHERE timestamp BETWEEN ? AND ?
                UNION
                SELECT id FROM time_ranges
                WHERE 
                    (start_time BETWEEN ? AND ?) OR 
                    (end_time BETWEEN ? AND ?) OR
                    (start_time <= ? AND end_time >= ?)
                """,
                (start_time, end_time, 
                 start_time, end_time,
                 start_time, end_time,
                 start_time, end_time)
            )
            
        return [row[0] for row in self.cursor.fetchall()]
        
    def get_items_at_time_point(self, 
                               time_point: float, 
                               window: float = 1.0,
                               use_compressed: bool = True) -> List[str]:
        """
        Get items at a specific time point (with optional window).
        
        Args:
            time_point: Target time point
            window: Time window around the point (in seconds)
            use_compressed: Whether to use compressed time values
            
        Returns:
            List of item IDs at the time point
        """
        return self.get_items_in_time_range(
            time_point - window/2, 
            time_point + window/2,
            use_compressed
        )
        
    def get_timeline(self, 
                    start_time: float, 
                    end_time: float, 
                    max_points: int = 100) -> List[Dict[str, Any]]:
        """
        Get a timeline of events within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            max_points: Maximum number of time points to include
            
        Returns:
            List of {timestamp, items} dictionaries
        """
        # Get all time points in the range
        points = [t for t in self.time_points if start_time <= t <= end_time]
        
        # If too many points, sample the timeline
        if len(points) > max_points:
            # Simple sampling for now
            sample_step = len(points) / max_points
            points = [points[int(i * sample_step)] for i in range(max_points)]
            
        # Build timeline
        timeline = []
        for t in sorted(points):
            items = self.get_items_at_time_point(t, window=1.0)
            
            # Get metadata for items
            item_details = []
            for item_id in items:
                self.cursor.execute(
                    "SELECT time_type, metadata FROM temporal_items WHERE id = ?",
                    (item_id,)
                )
                row = self.cursor.fetchone()
                if row:
                    time_type, metadata_str = row
                    item_details.append({
                        'id': item_id,
                        'time_type': time_type,
                        'metadata': json.loads(metadata_str)
                    })
                    
            timeline.append({
                'timestamp': t,
                'readable_time': datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S'),
                'items': item_details
            })
            
        return timeline
        
    def get_nearest_time_point(self, 
                              timestamp: float, 
                              direction: str = 'both') -> Optional[float]:
        """
        Find the nearest time point to a given timestamp.
        
        Args:
            timestamp: Reference timestamp
            direction: Search direction ('before', 'after', or 'both')
            
        Returns:
            Nearest time point or None if no time points exist
        """
        if not self.time_points:
            return None
            
        # Find insertion point
        idx = bisect.bisect_left(self.time_points, timestamp)
        
        if direction == 'before':
            # Get previous time point
            if idx > 0:
                return self.time_points[idx - 1]
            return None
            
        elif direction == 'after':
            # Get next time point
            if idx < len(self.time_points):
                return self.time_points[idx]
            return None
            
        else:  # 'both'
            # Get closest of previous or next
            if idx == 0:
                # Only points after
                if self.time_points:
                    return self.time_points[0]
                return None
            elif idx == len(self.time_points):
                # Only points before
                return self.time_points[-1]
            else:
                # Points both before and after
                before = self.time_points[idx - 1]
                after = self.time_points[idx]
                
                if timestamp - before <= after - timestamp:
                    return before
                else:
                    return after
                    
    def get_time_clusters(self, 
                         start_time: float, 
                         end_time: float,
                         min_cluster_size: int = 3,
                         max_gap: float = 86400) -> List[Dict[str, Any]]:
        """
        Find clusters of activity within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            min_cluster_size: Minimum items to form a cluster
            max_gap: Maximum time gap between cluster items (in seconds)
            
        Returns:
            List of cluster information dictionaries
        """
        # Get all items in the time range
        self.cursor.execute(
            """
            SELECT id, timestamp FROM temporal_items 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp
            """,
            (start_time, end_time)
        )
        items = self.cursor.fetchall()
        
        # No items, no clusters
        if not items:
            return []
            
        # Initialize clusters
        clusters = []
        current_cluster = {
            'start_time': items[0][1],
            'end_time': items[0][1],
            'items': [items[0][0]],
            'count': 1
        }
        
        # Group items into clusters
        for item_id, timestamp in items[1:]:
            # Check if this item belongs to the current cluster
            if timestamp - current_cluster['end_time'] <= max_gap:
                # Add to current cluster
                current_cluster['items'].append(item_id)
                current_cluster['end_time'] = timestamp
                current_cluster['count'] += 1
            else:
                # End current cluster if it's valid
                if current_cluster['count'] >= min_cluster_size:
                    clusters.append(current_cluster)
                    
                # Start a new cluster
                current_cluster = {
                    'start_time': timestamp,
                    'end_time': timestamp,
                    'items': [item_id],
                    'count': 1
                }
                
        # Add final cluster if valid
        if current_cluster['count'] >= min_cluster_size:
            clusters.append(current_cluster)
            
        # Enrich cluster info
        for cluster in clusters:
            cluster['duration'] = cluster['end_time'] - cluster['start_time']
            cluster['start_readable'] = datetime.fromtimestamp(cluster['start_time']).strftime('%Y-%m-%d %H:%M:%S')
            cluster['end_readable'] = datetime.fromtimestamp(cluster['end_time']).strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate density
            if cluster['duration'] > 0:
                cluster['density'] = cluster['count'] / cluster['duration']
            else:
                cluster['density'] = cluster['count']
                
        return clusters
                
    def get_item_temporal_context(self, 
                                 item_id: str, 
                                 window_size: float = 86400) -> Dict[str, Any]:
        """
        Get temporal context around a specific item.
        
        Args:
            item_id: Item ID to get context for
            window_size: Size of context window (in seconds)
            
        Returns:
            Dictionary with temporal context information
        """
        # Get item's timestamp
        if item_id not in self.id_to_time:
            return {'error': 'Item not found'}
            
        timestamp = self.id_to_time[item_id]
        
        # Handle range vs. point
        if isinstance(timestamp, tuple):
            center_time = (timestamp[0] + timestamp[1]) / 2
            timespan = {
                'start': timestamp[0],
                'end': timestamp[1],
                'duration': timestamp[1] - timestamp[0]
            }
        else:
            center_time = timestamp
            timespan = None
            
        # Get items before
        self.cursor.execute(
            """
            SELECT id, timestamp, time_type FROM temporal_items 
            WHERE timestamp BETWEEN ? AND ? AND id != ?
            ORDER BY timestamp DESC
            LIMIT 5
            """,
            (center_time - window_size, center_time, item_id)
        )
        before_items = [{'id': row[0], 'timestamp': row[1], 'type': row[2]} for row in self.cursor.fetchall()]
        
        # Get items after
        self.cursor.execute(
            """
            SELECT id, timestamp, time_type FROM temporal_items 
            WHERE timestamp BETWEEN ? AND ? AND id != ?
            ORDER BY timestamp ASC
            LIMIT 5
            """,
            (center_time, center_time + window_size, item_id)
        )
        after_items = [{'id': row[0], 'timestamp': row[1], 'type': row[2]} for row in self.cursor.fetchall()]
        
        # Find nearest landmark
        nearest_landmark = None
        min_distance = float('inf')
        
        for landmark_id, info in self.landmarks.items():
            distance = abs(center_time - info['timestamp'])
            if distance < min_distance:
                min_distance = distance
                nearest_landmark = {
                    'id': landmark_id,
                    'timestamp': info['timestamp'],
                    'description': info['description'],
                    'distance': distance
                }
                
        # Build context
        context = {
            'item_id': item_id,
            'center_time': center_time,
            'readable_time': datetime.fromtimestamp(center_time).strftime('%Y-%m-%d %H:%M:%S'),
            'timespan': timespan,
            'before': before_items,
            'after': after_items,
            'nearest_landmark': nearest_landmark
        }
        
        return context
        
    def save(self, path: str) -> None:
        """
        Save the temporal index state to disk.
        
        Args:
            path: Directory path to save to
        """
        os.makedirs(path, exist_ok=True)
        
        # Commit any pending changes
        self.conn.commit()
        
        # If not in-memory, copy the database file
        if not self.in_memory:
            import shutil
            shutil.copy(self.db_path, os.path.join(path, 'temporal_index.db'))
        else:
            # For in-memory, create a file backup
            backup_conn = sqlite3.connect(os.path.join(path, 'temporal_index.db'))
            self.conn.backup(backup_conn)
            backup_conn.close()
            
        # Save in-memory structures
        with open(os.path.join(path, 'temporal_data.pkl'), 'wb') as f:
            pickle.dump({
                'time_points': self.time_points,
                'time_to_ids': self.time_to_ids,
                'id_to_time': self.id_to_time,
                'compression_thresholds': self.compression_thresholds,
                'activity_windows': self.activity_windows,
                'landmarks': self.landmarks,
                'use_compression': self.use_compression
            }, f)
            
        print(f"Temporal index saved to {path}")
        
    @classmethod
    def load(cls, path: str, in_memory: bool = False) -> 'TemporalIndex':
        """
        Load a temporal index from disk.
        
        Args:
            path: Directory path to load from
            in_memory: Whether to load into memory
            
        Returns:
            Loaded TemporalIndex instance
        """
        # Create instance
        db_path = os.path.join(path, 'temporal_index.db')
        instance = cls(in_memory=in_memory, db_path=db_path)
        
        # Connect to the saved database
        if in_memory:
            # Load database into memory
            file_conn = sqlite3.connect(db_path)
            file_conn.backup(instance.conn)
            file_conn.close()
        else:
            # Already connected to the file in __init__
            pass
            
        # Load in-memory structures
        with open(os.path.join(path, 'temporal_data.pkl'), 'rb') as f:
            data = pickle.load(f)
            
        instance.time_points = data['time_points']
        instance.time_to_ids = data['time_to_ids']
        instance.id_to_time = data['id_to_time']
        instance.compression_thresholds = data['compression_thresholds']
        instance.activity_windows = data['activity_windows']
        instance.landmarks = data['landmarks']
        instance.use_compression = data['use_compression']
        
        print(f"Temporal index loaded from {path}")
        return instance


# Example usage
if __name__ == "__main__":
    # Create a temporal index
    index = TemporalIndex(in_memory=True, use_compression=True)
    
    # Add some test items
    now = time.time()
    day_seconds = 86400
    
    # Add items with varying temporal density
    # High activity period
    for i in range(100):
        item_id = f"high_activity_{i}"
        # Items within a 2-day period
        timestamp = now - (2 * day_seconds) + (i * 30 * 60)  # Every 30 minutes
        index.add_item(item_id, timestamp, "creation")
        
    # Medium activity period
    for i in range(20):
        item_id = f"medium_activity_{i}"
        # Items within a 5-day period
        timestamp = now - (10 * day_seconds) + (i * 6 * 60 * 60)  # Every 6 hours
        index.add_item(item_id, timestamp, "creation")
        
    # Low activity period
    for i in range(5):
        item_id = f"low_activity_{i}"
        # Items within a 10-day period
        timestamp = now - (30 * day_seconds) + (i * 2 * day_seconds)  # Every 2 days
        index.add_item(item_id, timestamp, "creation")
        
    # Add a time range item
    index.add_time_range(
        "range_item_1",
        now - (5 * day_seconds),
        now - (3 * day_seconds),
        {"type": "project", "name": "Phase 1"}
    )
    
    # Add landmarks
    index.add_landmark(
        "landmark_1",
        now - (15 * day_seconds),
        "Project kickoff"
    )
    index.add_landmark(
        "landmark_2",
        now - (5 * day_seconds),
        "Major milestone"
    )
    
    # Test queries
    print("\nTesting time range query:")
    high_activity_range = index.get_items_in_time_range(
        now - (2 * day_seconds),
        now - (1 * day_seconds)
    )
    print(f"Found {len(high_activity_range)} items in high activity period")
    
    print("\nTesting time point query:")
    point_items = index.get_items_at_time_point(
        now - (2 * day_seconds) + (10 * 30 * 60),  # 10 items into high activity period
        window=60 * 60  # 1 hour window
    )
    print(f"Found {len(point_items)} items at time point")
    
    print("\nTesting time clusters:")
    clusters = index.get_time_clusters(
        now - (40 * day_seconds),
        now,
        min_cluster_size=5,
        max_gap=day_seconds
    )
    print(f"Found {len(clusters)} time clusters")
    for i, cluster in enumerate(clusters):
        print(f"Cluster {i+1}: {cluster['count']} items, " 
              f"density: {cluster['density']:.6f} items/sec, "
              f"duration: {cluster['duration']/3600:.1f} hours")
        
    print("\nTesting item temporal context:")
    context = index.get_item_temporal_context(
        "high_activity_50",
        window_size=day_seconds
    )
    print(f"Context for item: {context['readable_time']}")
    print(f"Items before: {len(context['before'])}")
    print(f"Items after: {len(context['after'])}")
    if context['nearest_landmark']:
        print(f"Nearest landmark: {context['nearest_landmark']['description']}")