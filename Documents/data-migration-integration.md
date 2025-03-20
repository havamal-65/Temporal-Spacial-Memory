# Data Migration and Integration Strategies

This document outlines approaches for migrating existing data into the temporal-spatial knowledge database and integrating it with existing systems.

## Migration Challenges

Migrating to the temporal-spatial knowledge database presents several unique challenges:

1. **Coordinate Assignment**: Determining appropriate (t, r, θ) coordinates for existing data
2. **Relationship Discovery**: Identifying connections between concepts that aren't explicitly linked
3. **Temporal Reconstruction**: Establishing accurate time coordinates for historical data
4. **Branch Identification**: Determining where natural branches exist in legacy data
5. **Delta Encoding**: Converting existing versioning to delta-based representation

## Migration Methodologies

### 1. Phased Migration Approach

Rather than migrating all data at once, a phased approach ensures stability:

```
┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ Phase 1:       │  │ Phase 2:       │  │ Phase 3:       │  │ Phase 4:       │
│ Core Content   │─▶│ Historical     │─▶│ Related        │─▶│ Peripheral     │
│ Migration      │  │ Versions       │  │ Content        │  │ Content        │
└────────────────┘  └────────────────┘  └────────────────┘  └────────────────┘
```

#### Phase 1: Core Content Migration

Focus on migrating the most important, active content first:

```python
def migrate_core_content(source_system, target_knowledge_base):
    """Migrate core content to the new knowledge base"""
    # Identify core content based on usage, importance metrics
    core_items = identify_core_content(source_system)
    
    # Create initial coordinate space
    coordinate_space = initialize_coordinate_space()
    
    # Migrate each core item
    for item in core_items:
        # Extract content and metadata
        content = extract_content(item)
        timestamp = extract_timestamp(item)
        
        # Calculate initial position (simple placement for core content)
        position = calculate_initial_position(item, coordinate_space)
        
        # Create node in new system
        node = target_knowledge_base.add_node(
            content=content,
            position=position,
            timestamp=timestamp
        )
        
        # Track mapping for later phases
        record_migration_mapping(item.id, node.id)
        
    return migration_mapping
```

#### Phase 2: Historical Versions

After core content is migrated, add historical versions:

```python
def migrate_historical_versions(source_system, target_knowledge_base, migration_mapping):
    """Migrate historical versions of content"""
    for original_id, node_id in migration_mapping.items():
        # Get current node in target system
        current_node = target_knowledge_base.get_node(node_id)
        
        # Get historical versions from source
        historical_versions = source_system.get_historical_versions(original_id)
        
        # Sort by timestamp (oldest first)
        historical_versions.sort(key=lambda v: v.timestamp)
        
        # Create a starting point if current node is not the oldest
        if historical_versions and historical_versions[0].timestamp < current_node.timestamp:
            oldest_version = historical_versions[0]
            origin_node = target_knowledge_base.add_node(
                content=extract_content(oldest_version),
                position=(oldest_version.timestamp, current_node.position[1], current_node.position[2]),
                timestamp=oldest_version.timestamp
            )
            # Set as origin for current node
            current_node.origin_reference = origin_node.id
            
            # Start delta chain from oldest
            previous_node = origin_node
            
            # Skip the oldest since we just added it
            historical_versions = historical_versions[1:]
        else:
            # Start delta chain from current node
            previous_node = current_node
        
        # Add each historical version as a delta
        for version in historical_versions:
            if version.timestamp == current_node.timestamp:
                continue  # Skip if same as current node
                
            # Calculate delta from previous version
            delta = calculate_delta(
                extract_content(version),
                previous_node.content
            )
            
            # Create delta node
            delta_node = target_knowledge_base.add_delta_node(
                original_node=previous_node,
                delta_content=delta,
                timestamp=version.timestamp
            )
            
            previous_node = delta_node
```

#### Phase 3: Related Content

Migrate content related to core items and establish connections:

```python
def migrate_related_content(source_system, target_knowledge_base, migration_mapping):
    """Migrate content related to already migrated items"""
    # Identify related content not yet migrated
    related_items = identify_related_content(source_system, migration_mapping.keys())
    
    # Migrate each related item
    for item in related_items:
        # Skip if already migrated
        if item.id in migration_mapping:
            continue
            
        # Extract content and metadata
        content = extract_content(item)
        timestamp = extract_timestamp(item)
        
        # Find related nodes already in target system
        related_nodes = find_related_migrated_nodes(item, migration_mapping)
        
        # Calculate position based on related nodes
        position = calculate_position_from_related(
            item, 
            related_nodes,
            target_knowledge_base
        )
        
        # Create node in new system
        node = target_knowledge_base.add_node(
            content=content,
            position=position,
            timestamp=timestamp
        )
        
        # Create connections to related nodes
        for related_node in related_nodes:
            relationship = determine_relationship_type(item, related_node)
            target_knowledge_base.connect_nodes(
                node.id, 
                related_node.id,
                relationship_type=relationship
            )
        
        # Update mapping
        migration_mapping[item.id] = node.id
```

#### Phase 4: Peripheral Content

Finally, migrate remaining content with connections to the existing structure:

```python
def migrate_peripheral_content(source_system, target_knowledge_base, migration_mapping):
    """Migrate remaining peripheral content"""
    # Identify remaining content
    remaining_items = identify_remaining_content(source_system, migration_mapping.keys())
    
    # Group by clusters for batch processing
    content_clusters = cluster_remaining_content(remaining_items)
    
    for cluster in content_clusters:
        # Choose representative item as potential branch center
        center_item = select_cluster_center(cluster)
        
        # Check if this should form a branch
        if should_form_branch(center_item, cluster, target_knowledge_base):
            # Migrate as new branch
            migrate_as_branch(
                center_item,
                cluster,
                source_system,
                target_knowledge_base,
                migration_mapping
            )
        else:
            # Migrate as peripheral nodes
            for item in cluster:
                migrate_single_item(
                    item,
                    source_system,
                    target_knowledge_base,
                    migration_mapping
                )
```

### 2. Vector Embedding Approach for Coordinate Assignment

A key challenge is assigning appropriate coordinates. Vector embeddings provide a solution:

```python
def assign_coordinates_using_embeddings(items, embedding_model):
    """Assign coordinates based on semantic embeddings"""
    # Generate embeddings for all items
    embeddings = {}
    for item in items:
        text_content = extract_text(item)
        embeddings[item.id] = embedding_model.encode(text_content)
    
    # Reduce dimensionality for angular coordinate
    angular_coordinates = reduce_to_angular(embeddings)
    
    # Calculate relevance coordinates based on centrality
    relevance_coordinates = calculate_relevance_coordinates(embeddings)
    
    # Combine with timestamps for complete coordinates
    coordinates = {}
    for item in items:
        coordinates[item.id] = (
            extract_timestamp(item),
            relevance_coordinates[item.id],
            angular_coordinates[item.id]
        )
    
    return coordinates

def reduce_to_angular(embeddings):
    """Reduce high-dimensional embeddings to angular coordinates"""
    # Use dimensionality reduction technique (e.g., UMAP, t-SNE)
    # to project embeddings to 2D
    reduced = dimensionality_reduction(embeddings.values())
    
    # Convert 2D coordinates to angles
    angles = {}
    for i, item_id in enumerate(embeddings.keys()):
        x, y = reduced[i]
        angle = math.atan2(y, x)
        if angle < 0:
            angle += 2 * math.pi
        angles[item_id] = angle
    
    return angles

def calculate_relevance_coordinates(embeddings):
    """Calculate relevance coordinates based on centrality"""
    # Compute centroid of all embeddings
    all_embeddings = np.array(list(embeddings.values()))
    centroid = np.mean(all_embeddings, axis=0)
    
    # Calculate distances from centroid
    relevance = {}
    for item_id, embedding in embeddings.items():
        distance = np.linalg.norm(embedding - centroid)
        # Normalize and invert (closer to centroid = more relevant)
        normalized = transform_to_relevance_coordinate(distance)
        relevance[item_id] = normalized
    
    return relevance
```

### 3. Branch Detection for Existing Data

Identifying natural branches in existing data:

```python
def detect_branches_in_legacy_data(items, coordinates, similarity_threshold=0.7):
    """Detect natural branches in legacy data"""
    potential_branches = []
    
    # Group items by time periods
    time_periods = group_by_time_periods(items)
    
    for period, period_items in time_periods.items():
        # Skip periods with too few items
        if len(period_items) < MIN_ITEMS_FOR_BRANCH:
            continue
        
        # Get coordinates for these items
        period_coordinates = {item_id: coordinates[item_id] for item_id in period_items}
        
        # Cluster items based on coordinates
        clusters = cluster_by_coordinates(period_coordinates)
        
        # Analyze each cluster as potential branch
        for cluster in clusters:
            # Skip small clusters
            if len(cluster) < MIN_ITEMS_FOR_BRANCH:
                continue
                
            # Identify potential center
            center_id = identify_cluster_center(cluster, coordinates)
            
            # Calculate cluster metrics
            coherence = calculate_cluster_coherence(cluster, coordinates)
            isolation = calculate_cluster_isolation(cluster, period_items - cluster, coordinates)
            
            # Check if this should be a branch
            if coherence > similarity_threshold and isolation > ISOLATION_THRESHOLD:
                potential_branches.append({
                    'center_id': center_id,
                    'member_ids': cluster,
                    'coherence': coherence,
                    'isolation': isolation,
                    'time_period': period
                })
    
    # Sort branches by quality metrics
    potential_branches.sort(key=lambda b: b['coherence'] * b['isolation'], reverse=True)
    
    return potential_branches
```

## Integration Strategies

### 1. Hybrid Storage Architecture

Rather than migrating everything, use a hybrid approach:

```
┌───────────────────────────────┐
│ Application Layer             │
├───────────────────────────────┤
│ Unified Query Interface       │
├───────────┬───────────────────┤
│ Temporal- │ Legacy Systems    │
│ Spatial DB│ Adapters          │
├───────────┼───────────────────┤
│ New Data  │ Legacy Data       │
└───────────┴───────────────────┘
```

```python
class HybridQueryExecutor:
    def __init__(self, temporal_spatial_db, legacy_adapters):
        self.temporal_spatial_db = temporal_spatial_db
        self.legacy_adapters = legacy_adapters
        
    def execute_query(self, query):
        """Execute a query across both new and legacy systems"""
        # Determine where the query should be executed
        if should_query_new_system(query):
            # Query the temporal-spatial DB
            new_results = self.temporal_spatial_db.execute_query(query)
            
            # If needed, also query legacy systems for supplementary data
            if should_query_legacy_systems(query):
                legacy_results = self._query_legacy_systems(query)
                
                # Merge results
                return merge_results(new_results, legacy_results)
            
            return new_results
        else:
            # Only query legacy systems
            return self._query_legacy_systems(query)
    
    def _query_legacy_systems(self, query):
        """Execute query against legacy systems"""
        results = []
        
        for adapter in self.legacy_adapters:
            if adapter.can_handle(query):
                adapter_results = adapter.execute_query(query)
                results.append(adapter_results)
        
        return combine_legacy_results(results)
```

### 2. Synchronization Mechanisms

Keep legacy systems and the new database in sync during transition:

```python
class SynchronizationManager:
    def __init__(self, temporal_spatial_db, legacy_systems, mapping):
        self.temporal_spatial_db = temporal_spatial_db
        self.legacy_systems = legacy_systems
        self.mapping = mapping
        self.change_queue = Queue()
        self.lock = threading.Lock()
        
    def start_sync_workers(self, num_workers=5):
        """Start worker threads for synchronization"""
        self.workers = []
        for _ in range(num_workers):
            worker = threading.Thread(target=self._sync_worker)
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
    
    def _sync_worker(self):
        """Worker thread to process synchronization tasks"""
        while True:
            change = self.change_queue.get()
            try:
                if change['source'] == 'new':
                    self._sync_to_legacy(change)
                else:
                    self._sync_to_new(change)
            except Exception as e:
                log_sync_error(e, change)
            finally:
                self.change_queue.task_done()
    
    def register_new_system_change(self, node_id, change_type):
        """Register a change in the new system"""
        self.change_queue.put({
            'source': 'new',
            'node_id': node_id,
            'change_type': change_type,
            'timestamp': time.time()
        })
    
    def register_legacy_system_change(self, system_id, item_id, change_type):
        """Register a change in a legacy system"""
        self.change_queue.put({
            'source': 'legacy',
            'system_id': system_id,
            'item_id': item_id,
            'change_type': change_type,
            'timestamp': time.time()
        })
    
    def _sync_to_legacy(self, change):
        """Synchronize a change from new system to legacy systems"""
        node = self.temporal_spatial_db.get_node(change['node_id'])
        
        # Find mappings to legacy systems
        legacy_mappings = self.mapping.get_legacy_mappings(change['node_id'])
        
        for system_id, item_id in legacy_mappings:
            # Get the appropriate adapter
            adapter = self.get_adapter(system_id)
            
            # Apply the change to legacy system
            with self.lock:  # Prevent sync loops
                adapter.apply_change(item_id, change['change_type'], node)
    
    def _sync_to_new(self, change):
        """Synchronize a change from legacy system to new system"""
        system_id = change['system_id']
        item_id = change['item_id']
        
        # Get the adapter for this system
        adapter = self.get_adapter(system_id)
        
        # Get the item from legacy system
        item = adapter.get_item(item_id)
        
        # Find mapping to new system
        node_id = self.mapping.get_node_id(system_id, item_id)
        
        if node_id:
            # Update existing node
            with self.lock:  # Prevent sync loops
                self.temporal_spatial_db.update_node(
                    node_id,
                    adapter.extract_updates(item)
                )
        else:
            # Create new node
            # This is a simplified version - actual implementation would be more complex
            content = adapter.extract_content(item)
            timestamp = adapter.extract_timestamp(item)
            position = calculate_position_for_new_item(item)
            
            with self.lock:
                node = self.temporal_spatial_db.add_node(
                    content=content,
                    position=position,
                    timestamp=timestamp
                )
                
                # Update mapping
                self.mapping.add_mapping(system_id, item_id, node.id)
```

### 3. API Integration Layer

Create adapters to translate between systems:

```python
class LegacySystemAdapter:
    def __init__(self, system_id, connection_details):
        self.system_id = system_id
        self.connection = self._establish_connection(connection_details)
        
    def _establish_connection(self, details):
        """Establish connection to legacy system"""
        # Implementation depends on the specific legacy system
        
    def can_handle(self, query):
        """Check if this adapter can handle the query"""
        # Implementation depends on query capabilities
        
    def execute_query(self, query):
        """Execute a query against the legacy system"""
        # Transform query to legacy format
        legacy_query = self._transform_query(query)
        
        # Execute against legacy system
        raw_results = self._execute_raw_query(legacy_query)
        
        # Transform results to standard format
        return self._transform_results(raw_results)
    
    def get_item(self, item_id):
        """Get a specific item from the legacy system"""
        # Implementation depends on legacy system
        
    def extract_content(self, item):
        """Extract content from legacy item"""
        # Implementation depends on item structure
        
    def extract_timestamp(self, item):
        """Extract timestamp from legacy item"""
        # Implementation depends on item structure
        
    def extract_updates(self, item):
        """Extract updates from changed item"""
        # Implementation depends on item structure
        
    def apply_change(self, item_id, change_type, node):
        """Apply a change from the new system to legacy item"""
        # Implementation depends on change type and legacy system
```

## Practical Migration Patterns

### 1. Content Type Migration Patterns

Different content types require specialized approaches:

#### Document Migration

```python
def migrate_documents(documents, target_kb):
    """Migrate document-type content"""
    for doc in documents:
        # Extract metadata
        title = doc.get('title', '')
        creation_time = doc.get('created_at', time.time())
        author = doc.get('author', '')
        
        # Extract key concepts and create embeddings
        concepts = extract_key_concepts(doc['content'])
        embedding = embedding_model.encode(doc['content'])
        
        # Calculate position
        position = calculate_position_from_embedding(embedding)
        
        # Create the node
        node = target_kb.add_node(
            content={
                'title': title,
                'text': doc['content'],
                'author': author,
                'concepts': concepts,
                'metadata': doc.get('metadata', {})
            },
            position=position,
            timestamp=creation_time
        )
        
        # If document has versions, add them as deltas
        if 'versions' in doc:
            previous_node = node
            for version in sorted(doc['versions'], key=lambda v: v['timestamp']):
                delta = calculate_text_delta(previous_node.content['text'], version['content'])
                delta_node = target_kb.add_delta_node(
                    original_node=previous_node,
                    delta_content={
                        'text_delta': delta,
                        'modified_by': version.get('author', ''),
                        'reason': version.get('comment', '')
                    },
                    timestamp=version['timestamp']
                )
                previous_node = delta_node
```

#### Conversation Migration

```python
def migrate_conversations(conversations, target_kb):
    """Migrate conversation-type content"""
    for conversation in conversations:
        # Create a conversation container node
        conv_node = target_kb.add_node(
            content={
                'title': conversation.get('title', 'Conversation'),
                'participants': conversation.get('participants', []),
                'summary': generate_summary(conversation['messages']),
                'metadata': conversation.get('metadata', {})
            },
            position=calculate_conversation_position(conversation),
            timestamp=get_conversation_start_time(conversation)
        )
        
        # Track topics through the conversation
        topics = {}
        
        # Process messages in temporal order
        for msg in sorted(conversation['messages'], key=lambda m: m['timestamp']):
            # Extract topics from this message
            msg_topics = extract_topics(msg['content'])
            
            # Update or create topic nodes
            for topic in msg_topics:
                if topic in topics:
                    # Update existing topic with delta
                    topic_node = topics[topic]
                    topic_update = extract_topic_update(msg, topic)
                    
                    delta_node = target_kb.add_delta_node(
                        original_node=topic_node,
                        delta_content=topic_update,
                        timestamp=msg['timestamp']
                    )
                    
                    topics[topic] = delta_node
                else:
                    # Create new topic node
                    topic_node = target_kb.add_node(
                        content={
                            'topic': topic,
                            'first_mentioned_by': msg['sender'],
                            'context': extract_context(msg, topic),
                            'examples': [extract_excerpt(msg, topic)]
                        },
                        position=calculate_topic_position(topic, conv_node.position),
                        timestamp=msg['timestamp']
                    )
                    
                    # Connect to conversation node
                    target_kb.connect_nodes(
                        topic_node.id,
                        conv_node.id,
                        relationship_type='mentioned_in'
                    )
                    
                    topics[topic] = topic_node
```

#### Structured Data Migration

```python
def migrate_structured_data(datasets, target_kb):
    """Migrate structured data (databases, tables, etc.)"""
    for dataset in datasets:
        # Create dataset container node
        dataset_node = target_kb.add_node(
            content={
                'name': dataset['name'],
                'description': dataset.get('description', ''),
                'schema': dataset.get('schema', {}),
                'source': dataset.get('source', ''),
                'metadata': dataset.get('metadata', {})
            },
            position=calculate_dataset_position(dataset),
            timestamp=dataset.get('created_at', time.time())
        )
        
        # Process tables/collections
        for table in dataset.get('tables', []):
            table_node = target_kb.add_node(
                content={
                    'name': table['name'],
                    'description': table.get('description', ''),
                    'schema': table.get('schema', {}),
                    'row_count': table.get('row_count', 0),
                    'sample_data': table.get('sample_data', [])
                },
                position=calculate_table_position(table, dataset_node.position),
                timestamp=table.get('created_at', dataset_node.timestamp)
            )
            
            # Connect table to dataset
            target_kb.connect_nodes(
                table_node.id,
                dataset_node.id,
                relationship_type='belongs_to'
            )
            
            # Process key entities or concepts from the table
            for entity in extract_key_entities(table):
                entity_node = target_kb.add_node(
                    content={
                        'entity': entity['name'],
                        'description': entity.get('description', ''),
                        'attributes': entity.get('attributes', {}),
                        'examples': entity.get('examples', [])
                    },
                    position=calculate_entity_position(entity, table_node.position),
                    timestamp=table_node.timestamp
                )
                
                # Connect entity to table
                target_kb.connect_nodes(
                    entity_node.id,
                    table_node.id,
                    relationship_type='defined_in'
                )
```

### 2. Incremental Synchronization Patterns

For ongoing synchronization during transition periods:

```python
class IncrementalSynchronizer:
    def __init__(self, source_system, target_kb, mapping):
        self.source_system = source_system
        self.target_kb = target_kb
        self.mapping = mapping
        self.last_sync_time = None
        
    def synchronize(self):
        """Perform an incremental synchronization"""
        current_time = time.time()
        
        # Get changes since last sync
        if self.last_sync_time:
            changes = self.source_system.get_changes_since(self.last_sync_time)
        else:
            # First sync, get everything
            changes = self.source_system.get_all_items()
        
        # Process changes
        for change in changes:
            self._process_change(change)
        
        # Update last sync time
        self.last_sync_time = current_time
        
    def _process_change(self, change):
        """Process a single change"""
        item_id = change['id']
        
        # Check if this item has been migrated before
        node_id = self.mapping.get_node_id(self.source_system.id, item_id)
        
        if change['type'] == 'create' or not node_id:
            # New item or not previously migrated
            self._handle_new_item(change)
        elif change['type'] == 'update':
            # Update to existing item
            self._handle_update(change, node_id)
        elif change['type'] == 'delete':
            # Item was deleted
            self._handle_delete(change, node_id)
    
    def _handle_new_item(self, change):
        """Handle a new item"""
        # Extract content and metadata
        content = self.source_system.extract_content(change['item'])
        timestamp = self.source_system.extract_timestamp(change['item'])
        
        # Calculate position
        position = calculate_position_for_item(change['item'])
        
        # Create new node
        node = self.target_kb.add_node(
            content=content,
            position=position,
            timestamp=timestamp
        )
        
        # Update mapping
        self.mapping.add_mapping(self.source_system.id, change['id'], node.id)
        
        # Process relationships
        for rel in self.source_system.extract_relationships(change['item']):
            # Check if related item is already migrated
            related_node_id = self.mapping.get_node_id(
                self.source_system.id, 
                rel['related_id']
            )
            
            if related_node_id:
                # Create connection
                self.target_kb.connect_nodes(
                    node.id,
                    related_node_id,
                    relationship_type=rel['type']
                )
    
    def _handle_update(self, change, node_id):
        """Handle an update to existing item"""
        # Get current node
        current_node = self.target_kb.get_node(node_id)
        
        # Extract updates
        updates = self.source_system.extract_updates(change['item'])
        timestamp = self.source_system.extract_timestamp(change['item'])
        
        # Create a delta node
        self.target_kb.add_delta_node(
            original_node=current_node,
            delta_content=updates,
            timestamp=timestamp
        )
    
    def _handle_delete(self, change, node_id):
        """Handle a deleted item"""
        # Options:
        # 1. Mark as deleted but keep in knowledge base
        self.target_kb.mark_as_deleted(node_id)
        
        # 2. Or actually remove if that's appropriate
        # self.target_kb.remove_node(node_id)
        
        # Update mapping
        self.mapping.remove_mapping(self.source_system.id, change['id'])
```

## Conclusion

Migrating to the temporal-spatial knowledge database requires a thoughtful, phased approach that addresses the unique challenges of coordinate assignment, relationship discovery, and branch identification. By using techniques like vector embeddings for positioning and implementing a hybrid architecture during transition, organizations can leverage the benefits of the new system while preserving their investment in existing data.

The integration strategies outlined provide a framework for connecting the temporal-spatial database with legacy systems, enabling a smooth transition path that minimizes disruption while maximizing the value of historical knowledge. Through careful planning and the appropriate use of these patterns, organizations can successfully adopt this innovative knowledge representation approach.
