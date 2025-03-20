# Branch Formation Implementation Details

This document outlines the implementation considerations for adding branch formation capabilities to the temporal-spatial knowledge database.

## Modified Data Structures

### Enhanced Node Class

```python
class Node:
    def __init__(self, id, topic, timestamp, content, position):
        # Original attributes
        self.id = id
        self.topic = topic
        self.timestamp = timestamp
        self.content = content
        self.position = position  # Local branch coordinates (t, r, θ)
        self.connections = []
        self.origin_reference = None
        self.delta_information = {}
        
        # Branch-related attributes
        self.global_position = None  # Coordinates in global space
        self.branch_id = None        # Which branch this node belongs to
        self.is_branch_center = False # Whether this node is a branch center
```

### Branch Class

```python
class Branch:
    def __init__(self, center_node, parent_branch=None):
        self.id = generate_unique_id()
        self.center_node = center_node
        self.parent_branch = parent_branch
        self.child_branches = []
        self.creation_time = center_node.timestamp
        self.nodes = [center_node]
        self.threshold_distance = 90  # Default threshold for branch formation
        
        # Set the center node's branch attributes
        center_node.branch_id = self.id
        center_node.is_branch_center = True
        
        # Connection to parent branch
        if parent_branch:
            self.parent_connection = {
                'from_node': center_node,
                'to_node': self.find_closest_in_parent(),
                'strength': 1.0
            }
            parent_branch.child_branches.append(self)
```

## Core Algorithms

### Branch Detection

```python
def detect_branch_candidates(knowledge_base, min_satellites=5, connection_threshold=0.5):
    """Identify nodes that are candidates for becoming new branch centers"""
    candidates = []
    
    for branch in knowledge_base.branches:
        # Get the branch's threshold distance for branching
        threshold = branch.threshold_distance
        
        # Find nodes that exceed the threshold distance from center
        distant_nodes = [
            node for node in branch.nodes 
            if calculate_distance(node.position, (0, 0, node.position[0])) > threshold
            and not node.is_branch_center
        ]
        
        for node in distant_nodes:
            # Find connected nodes that would form the satellite cluster
            connected_nodes = [
                conn.target for conn in node.connections
                if conn.strength >= connection_threshold
                and conn.target.branch_id == branch.id
            ]
            
            # Check if there are enough connected nodes
            if len(connected_nodes) >= min_satellites:
                candidates.append({
                    'node': node,
                    'branch': branch,
                    'satellites': connected_nodes,
                    'branching_score': calculate_branching_score(node, connected_nodes)
                })
    
    return candidates
```

### Branch Creation

```python
def create_branch(knowledge_base, candidate, satellites):
    """Create a new branch from a candidate node and its satellites"""
    parent_branch = candidate['branch']
    node = candidate['node']
    
    # Create new branch with the candidate as center
    new_branch = Branch(
        center_node=node,
        parent_branch=parent_branch
    )
    
    # Store global position before converting to local coordinates
    node.global_position = node.position
    
    # Set node as new branch center at (t, 0, 0) in local coordinates
    node.position = (node.position[0], 0, 0)
    
    # Add satellites to the new branch
    for satellite in satellites:
        # Store global coordinates
        satellite.global_position = satellite.position
        
        # Calculate position relative to new center
        local_position = global_to_local_coordinates(
            satellite.position,
            node.global_position
        )
        
        # Update satellite's position and branch
        satellite.position = local_position
        satellite.branch_id = new_branch.id
        
        # Add to branch's nodes list
        new_branch.nodes.append(satellite)
    
    # Remove these nodes from parent branch
    parent_branch.nodes = [n for n in parent_branch.nodes if n.branch_id != new_branch.id]
    
    # Add branch to knowledge base
    knowledge_base.branches.append(new_branch)
    
    return new_branch
```

### Coordinate Transformation

```python
def global_to_local_coordinates(global_coords, branch_center_global_coords):
    """Transform global coordinates to branch-local coordinates"""
    t_global, r_global, θ_global = global_coords
    t_center, r_center, θ_center = branch_center_global_coords
    
    # Time coordinate remains consistent
    t_local = t_global
    
    # Calculate distance from center
    dx = r_global * math.cos(θ_global) - r_center * math.cos(θ_center)
    dy = r_global * math.sin(θ_global) - r_center * math.sin(θ_center)
    r_local = math.sqrt(dx*dx + dy*dy)
    
    # Calculate angle relative to center
    θ_local = math.atan2(dy, dx)
    if θ_local < 0:
        θ_local += 2 * math.pi  # Normalize to 0-2π
    
    return (t_local, r_local, θ_local)
```

```python
def local_to_global_coordinates(local_coords, branch_center_global_coords):
    """Transform branch-local coordinates to global coordinates"""
    t_local, r_local, θ_local = local_coords
    t_center, r_center, θ_center = branch_center_global_coords
    
    # Time coordinate remains consistent
    t_global = t_local
    
    # Convert to Cartesian offsets
    dx = r_local * math.cos(θ_local)
    dy = r_local * math.sin(θ_local)
    
    # Add to center's Cartesian coordinates
    x_center = r_center * math.cos(θ_center)
    y_center = r_center * math.sin(θ_center)
    
    x_global = x_center + dx
    y_global = y_center + dy
    
    # Convert back to polar
    r_global = math.sqrt(x_global*x_global + y_global*y_global)
    θ_global = math.atan2(y_global, x_global)
    if θ_global < 0:
        θ_global += 2 * math.pi  # Normalize to 0-2π
    
    return (t_global, r_global, θ_global)
```

## Integration with Existing System

### Modified Knowledge Base Class

```python
class KnowledgeBase:
    def __init__(self, name):
        self.name = name
        self.nodes = []
        self.branches = []
        
        # Create root branch (global space)
        self.root_branch = self.create_root_branch()
        self.branches.append(self.root_branch)
    
    def create_root_branch(self):
        """Create the root branch with a core node"""
        root_node = Node(
            id="root",
            topic="Core",
            timestamp=0,
            content={"description": "Root knowledge node"},
            position=(0, 0, 0)
        )
        
        self.nodes.append(root_node)
        
        return Branch(center_node=root_node)
    
    def add_node(self, topic, content, connections=None, branch_id=None):
        """Add a new node to the knowledge base"""
        # Determine which branch to add to
        if branch_id is None:
            branch = self.root_branch
        else:
            branch = next((b for b in self.branches if b.id == branch_id), self.root_branch)
        
        # Calculate position based on connections
        if connections:
            connected_nodes = [self.get_node(conn_id) for conn_id in connections]
            position = self.calculate_position(connected_nodes, branch)
        else:
            position = self.calculate_default_position(branch)
        
        # Create the node
        node = Node(
            id=generate_unique_id(),
            topic=topic,
            timestamp=get_current_time(),
            content=content,
            position=position
        )
        
        node.branch_id = branch.id
        
        # Add to collections
        self.nodes.append(node)
        branch.nodes.append(node)
        
        # Create connections
        if connections:
            for conn_id in connections:
                self.connect_nodes(node.id, conn_id)
        
        # Check if the new node or its connections might trigger branching
        self.check_for_branch_formation()
        
        return node
    
    def check_for_branch_formation(self):
        """Check if any nodes qualify for forming new branches"""
        candidates = detect_branch_candidates(self)
        
        if candidates:
            # Sort by branching score and take the top candidate
            candidates.sort(key=lambda c: c['branching_score'], reverse=True)
            top_candidate = candidates[0]
            
            # If score is above threshold, create a new branch
            if top_candidate['branching_score'] > BRANCH_THRESHOLD:
                create_branch(self, top_candidate, top_candidate['satellites'])
```

### Extended Query Interface

```python
def find_related_concepts(knowledge_base, topic, search_scope='branch'):
    """Find concepts related to the given topic"""
    # Find the node matching the topic
    node = knowledge_base.find_node_by_topic(topic)
    if not node:
        return []
    
    # Get the branch this node belongs to
    branch = next((b for b in knowledge_base.branches if b.id == node.branch_id), None)
    if not branch:
        return []
    
    if search_scope == 'branch':
        # Search only within this branch
        candidates = branch.nodes
    elif search_scope == 'branch+parent':
        # Search in this branch and its parent
        candidates = branch.nodes.copy()
        if branch.parent_branch:
            candidates.extend(branch.parent_branch.nodes)
    elif search_scope == 'global':
        # Search across all branches (more expensive)
        candidates = knowledge_base.nodes
    else:
        candidates = branch.nodes
    
    # Calculate relevance to the query node
    results = []
    for candidate in candidates:
        if candidate.id == node.id:
            continue  # Skip the query node itself
        
        # Calculate relevance score based on position and connections
        relevance = calculate_relevance(node, candidate, branch)
        
        results.append({
            'node': candidate,
            'relevance': relevance
        })
    
    # Sort by relevance and return
    results.sort(key=lambda r: r['relevance'], reverse=True)
    return results
```

## Performance Considerations

### Caching Branch Structures

```python
class BranchCache:
    def __init__(self, max_size=10):
        self.cache = {}
        self.max_size = max_size
        self.access_count = {}
    
    def get_branch(self, branch_id):
        """Get a branch from cache if available"""
        if branch_id in self.cache:
            self.access_count[branch_id] += 1
            return self.cache[branch_id]
        return None
    
    def add_branch(self, branch):
        """Add a branch to cache, evicting least used if necessary"""
        if len(self.cache) >= self.max_size:
            # Find least accessed branch
            least_accessed = min(self.access_count.items(), key=lambda x: x[1])[0]
            del self.cache[least_accessed]
            del self.access_count[least_accessed]
        
        # Add to cache
        self.cache[branch.id] = branch
        self.access_count[branch.id] = 1
```

### Optimized Branch Detection

To avoid checking all nodes for branch formation after every update:

```python
def check_nodes_for_branching(knowledge_base, affected_nodes):
    """Check only affected nodes for potential branch formation"""
    candidates = []
    
    for node in affected_nodes:
        # Skip nodes that are already branch centers
        if node.is_branch_center:
            continue
            
        branch = knowledge_base.get_branch(node.branch_id)
        threshold = branch.threshold_distance
        
        # Check if node exceeds threshold
        if calculate_distance(node.position, (0, 0, node.position[0])) > threshold:
            # Find connected nodes
            connected_nodes = [
                conn.target for conn in node.connections
                if conn.target.branch_id == branch.id
            ]
            
            if len(connected_nodes) >= MIN_SATELLITES:
                candidates.append({
                    'node': node,
                    'branch': branch,
                    'satellites': connected_nodes,
                    'branching_score': calculate_branching_score(node, connected_nodes)
                })
    
    return candidates
```

## Visualization Support

### Multi-Level Visualization

```python
def render_knowledge_structure(knowledge_base, view_mode='global', focus_branch=None):
    """Render the knowledge structure based on view mode"""
    if view_mode == 'global':
        # Render the entire structure with simplified branches
        render_global_view(knowledge_base)
    
    elif view_mode == 'branch' and focus_branch:
        # Render detailed view of a specific branch
        branch = knowledge_base.get_branch(focus_branch)
        if branch:
            render_branch_view(branch)
    
    elif view_mode == 'multi':
        # Render focused branch with simplified parent/child branches
        branch = knowledge_base.get_branch(focus_branch)
        if branch:
            render_multi_level_view(branch)
```

## Timeline Impact

Adding branch formation functionality would affect our implementation timeline as follows:

1. **Phase 1: Core Prototype** - No significant changes, but need to plan for branch-aware data structures

2. **Phase 2: Core Algorithms** - Add ~3-4 weeks for:
   - Implementing coordinate transformation functions
   - Developing branch detection algorithms
   - Creating the Branch class and branch management functions

3. **Phase 3: Integration and Testing** - Add ~2 weeks for:
   - Testing branch formation under various conditions
   - Ensuring consistent performance across branch boundaries
   - Validating coordinate transformations

4. **Phase 4: Refinement** - Add specific branch-related optimizations

Total additional development time: Approximately 5-6 weeks

## Adoption Strategy

To minimize impact on existing implementation work:

1. **Implement Core System First**: Complete the basic temporal-spatial database without branching

2. **Add Branch Formation as Extension**: Introduce branch capabilities as a module that extends the base system

3. **Incremental Integration**: Add branch detection and management first, then coordinate transformation, and finally branch-aware queries

4. **Feature Flag Approach**: Allow branching to be enabled/disabled during testing phases

This approach allows parallel development tracks and ensures the core functionality remains stable while branching features are being developed and refined.
