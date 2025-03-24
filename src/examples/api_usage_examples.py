"""
Example usage patterns for the Temporal-Spatial Memory Database API.

This module demonstrates how to use the Python client SDK to interact with the database.
"""

import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.api.client_sdk import TemporalSpatialClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def basic_usage_example():
    """Basic usage of the client SDK."""
    # Create client
    client = TemporalSpatialClient(
        base_url="http://localhost:8000",
        username="demo",
        password="password"
    )
    
    try:
        # Create a node
        node = client.create_node(
            content="Example node",
            spatial_coordinates=[10.5, 20.3, 30.1],
            metadata={
                "tags": ["example", "basic"],
                "priority": "high"
            }
        )
        
        logger.info(f"Created node with ID: {node['id']}")
        
        # Get the node
        retrieved_node = client.get_node(node['id'])
        logger.info(f"Retrieved node: {retrieved_node['content']}")
        
        # Update the node
        updated_node = client.update_node(
            node_id=node['id'],
            content="Updated example node",
            spatial_coordinates=[11.5, 21.3, 31.1],
            metadata={
                "tags": ["example", "basic", "updated"],
                "priority": "medium"
            }
        )
        
        logger.info(f"Updated node version: {updated_node['version']}")
        
        # Delete the node
        client.delete_node(node['id'])
        logger.info(f"Deleted node with ID: {node['id']}")
        
    finally:
        # Close the client
        client.close()

def query_examples():
    """Examples of different query patterns."""
    # Create client
    client = TemporalSpatialClient(
        base_url="http://localhost:8000",
        username="demo",
        password="password"
    )
    
    try:
        # Create some sample nodes
        node_ids = []
        for i in range(10):
            # Random coordinates
            x = random.uniform(0, 100)
            y = random.uniform(0, 100)
            z = random.uniform(0, 100)
            
            # Random timestamp in the last 30 days
            timestamp = time.time() - random.uniform(0, 30 * 24 * 3600)
            
            node = client.create_node(
                content=f"Sample node {i}",
                spatial_coordinates=[x, y, z],
                temporal_coordinate=timestamp,
                metadata={
                    "tags": ["sample", f"group-{i % 3}"],
                    "value": random.randint(1, 100)
                }
            )
            
            node_ids.append(node['id'])
        
        logger.info(f"Created {len(node_ids)} sample nodes")
        
        # Spatial query example
        spatial_results = client.spatial_query(
            point=[50, 50, 50],
            distance=30.0,
            limit=5
        )
        
        logger.info(f"Spatial query returned {spatial_results['count']} results")
        
        # Temporal query example
        start_time = datetime.now() - timedelta(days=15)
        temporal_results = client.temporal_query(
            start_time=start_time,
            limit=5
        )
        
        logger.info(f"Temporal query returned {temporal_results['count']} results")
        
        # Combined query example
        combined_results = client.combined_query(
            spatial_criteria={
                "point": [50, 50, 50],
                "distance": 50.0
            },
            temporal_criteria={
                "start_time": time.time() - 20 * 24 * 3600,
                "end_time": time.time()
            },
            limit=5
        )
        
        logger.info(f"Combined query returned {combined_results['count']} results")
        
        # Query with sorting and pagination
        sorted_results = client.query(
            spatial_criteria={
                "point": [50, 50, 50],
                "distance": 100.0
            },
            sort_by="distance",
            sort_order="asc",
            limit=3,
            offset=0
        )
        
        logger.info(f"Sorted query (page 1) returned {sorted_results['count']} results")
        
        # Get next page
        next_page = client.query(
            spatial_criteria={
                "point": [50, 50, 50],
                "distance": 100.0
            },
            sort_by="distance",
            sort_order="asc",
            limit=3,
            offset=3
        )
        
        logger.info(f"Sorted query (page 2) returned {next_page['count']} results")
        
        # Clean up
        for node_id in node_ids:
            client.delete_node(node_id)
        
        logger.info("Deleted all sample nodes")
        
    finally:
        # Close the client
        client.close()

def error_handling_example():
    """Example of error handling with the client SDK."""
    # Create client
    client = TemporalSpatialClient(
        base_url="http://localhost:8000",
        username="demo",
        password="password",
        max_retries=3,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=10
    )
    
    try:
        # Try to get a non-existent node
        try:
            client.get_node("non-existent-id")
        except Exception as e:
            logger.error(f"Expected error: {str(e)}")
        
        # Try to update a non-existent node
        try:
            client.update_node(
                node_id="non-existent-id",
                content="Updated content"
            )
        except Exception as e:
            logger.error(f"Expected error: {str(e)}")
        
        # Try with invalid authentication
        try:
            invalid_client = TemporalSpatialClient(
                base_url="http://localhost:8000",
                username="invalid",
                password="invalid"
            )
        except ValueError as e:
            logger.error(f"Expected authentication error: {str(e)}")
        
    finally:
        # Close the client
        client.close()

def real_time_tracking_example():
    """Example of using the API for real-time location tracking."""
    # Create client
    client = TemporalSpatialClient(
        base_url="http://localhost:8000",
        username="demo",
        password="password"
    )
    
    try:
        # Create a device
        device = client.create_node(
            content={
                "device_id": "device-001",
                "device_type": "gps_tracker",
                "status": "active"
            },
            spatial_coordinates=[0, 0, 0],
            metadata={
                "battery": 100,
                "owner": "user-123"
            }
        )
        
        device_id = device['id']
        logger.info(f"Created device with ID: {device_id}")
        
        # Simulate location updates
        for i in range(5):
            # Simulate movement
            x = i * 10
            y = i * 5
            z = 0
            
            # Update device location
            device = client.update_node(
                node_id=device_id,
                content={
                    "device_id": "device-001",
                    "device_type": "gps_tracker",
                    "status": "active"
                },
                spatial_coordinates=[x, y, z],
                metadata={
                    "battery": 100 - i * 5,
                    "owner": "user-123",
                    "last_update": time.time()
                }
            )
            
            logger.info(f"Updated device location: [{x}, {y}, {z}]")
            time.sleep(1)
        
        # Query device history
        history = client.temporal_query(
            start_time=time.time() - 3600,
            limit=10
        )
        
        logger.info(f"Device history has {history['count']} entries")
        
        # Clean up
        client.delete_node(device_id)
        logger.info(f"Deleted device with ID: {device_id}")
        
    finally:
        # Close the client
        client.close()

def geospatial_analysis_example():
    """Example of using the API for geospatial analysis."""
    # Create client
    client = TemporalSpatialClient(
        base_url="http://localhost:8000",
        username="demo",
        password="password"
    )
    
    try:
        # Create some points of interest
        poi_ids = []
        poi_types = ["restaurant", "store", "park", "hospital", "school"]
        
        for i in range(20):
            # Random location
            x = random.uniform(0, 100)
            y = random.uniform(0, 100)
            z = 0
            
            poi_type = random.choice(poi_types)
            
            poi = client.create_node(
                content={
                    "name": f"{poi_type.capitalize()} {i}",
                    "type": poi_type,
                    "rating": random.uniform(1, 5)
                },
                spatial_coordinates=[x, y, z],
                metadata={
                    "visitors": random.randint(100, 1000),
                    "open_hours": "9AM-5PM"
                }
            )
            
            poi_ids.append(poi['id'])
        
        logger.info(f"Created {len(poi_ids)} points of interest")
        
        # Find all points of interest within 20 units of center
        center = [50, 50, 0]
        nearby = client.spatial_query(
            point=center,
            distance=20.0,
            limit=10
        )
        
        logger.info(f"Found {nearby['count']} POIs within 20 units of center")
        
        # Find restaurants with rating > 4
        all_pois = client.query(
            spatial_criteria={
                "point": center,
                "distance": 100.0  # Include all
            },
            limit=100
        )
        
        restaurants = []
        for poi in all_pois['results']:
            content = poi['content']
            if content.get('type') == 'restaurant' and content.get('rating', 0) > 4:
                restaurants.append(poi)
        
        logger.info(f"Found {len(restaurants)} highly-rated restaurants")
        
        # Clean up
        for poi_id in poi_ids:
            client.delete_node(poi_id)
        
        logger.info("Deleted all points of interest")
        
    finally:
        # Close the client
        client.close()

def time_series_visualization_example():
    """Example of using the API for time series data visualization."""
    # Create client
    client = TemporalSpatialClient(
        base_url="http://localhost:8000",
        username="demo",
        password="password"
    )
    
    try:
        # Create a sensor
        sensor = client.create_node(
            content={
                "sensor_id": "sensor-001",
                "sensor_type": "temperature"
            },
            spatial_coordinates=[50, 50, 0],
            metadata={
                "unit": "celsius",
                "location": "Building A"
            }
        )
        
        sensor_id = sensor['id']
        logger.info(f"Created sensor with ID: {sensor_id}")
        
        # Simulate sensor readings over time
        reading_ids = []
        start_time = time.time() - 24 * 3600  # 1 day ago
        
        for i in range(24):  # 24 hourly readings
            timestamp = start_time + i * 3600
            temperature = 20 + 5 * math.sin(i / 12 * math.pi) + random.uniform(-1, 1)
            
            reading = client.create_node(
                content={
                    "sensor_id": "sensor-001",
                    "value": temperature,
                    "hour": i
                },
                spatial_coordinates=[50, 50, 0],
                temporal_coordinate=timestamp,
                metadata={
                    "unit": "celsius",
                    "is_anomaly": temperature > 25 or temperature < 15
                }
            )
            
            reading_ids.append(reading['id'])
        
        logger.info(f"Created {len(reading_ids)} temperature readings")
        
        # Query all readings
        readings = client.temporal_query(
            start_time=start_time,
            end_time=time.time(),
            limit=100
        )
        
        logger.info(f"Retrieved {readings['count']} temperature readings")
        
        # Extract time series data
        times = []
        values = []
        
        for reading in readings['results']:
            times.append(reading['coordinates']['temporal'])
            values.append(reading['content']['value'])
        
        logger.info("Extracted time series data for visualization")
        
        # Simulate generating visualization (just print some stats)
        logger.info(f"Time series statistics:")
        logger.info(f"  Average temperature: {sum(values) / len(values):.2f}°C")
        logger.info(f"  Min temperature: {min(values):.2f}°C")
        logger.info(f"  Max temperature: {max(values):.2f}°C")
        
        # Clean up
        for reading_id in reading_ids:
            client.delete_node(reading_id)
        
        client.delete_node(sensor_id)
        logger.info("Deleted sensor and all readings")
        
    finally:
        # Close the client
        client.close()

if __name__ == "__main__":
    import math  # Required for the time_series_visualization_example
    
    print("Running basic usage example...")
    basic_usage_example()
    
    print("\nRunning query examples...")
    query_examples()
    
    print("\nRunning error handling example...")
    error_handling_example()
    
    print("\nRunning real-time tracking example...")
    real_time_tracking_example()
    
    print("\nRunning geospatial analysis example...")
    geospatial_analysis_example()
    
    print("\nRunning time series visualization example...")
    time_series_visualization_example()
    
    print("\nAll examples completed.") 