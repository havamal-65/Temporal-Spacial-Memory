# Security and Access Control Model

This document outlines the security and access control model for the temporal-spatial knowledge database, addressing the unique challenges posed by its coordinate-based structure and branch formation mechanisms.

## Security Challenges

The temporal-spatial database presents unique security challenges:

1. **Multi-dimensional Access Control**: Traditional row/column level permissions are insufficient for a coordinate-based system
2. **Temporal Sensitivity**: Some information may only be accessible for specific time periods
3. **Branch-based Isolation**: Different branches may have different access requirements
4. **Relational Context**: Access to a node may not imply access to all connected nodes
5. **Historical Immutability**: Ensuring past knowledge states cannot be inappropriately modified

## Coordinate-Based Access Control Model

### 1. Dimensional Access Boundaries

Access can be limited by defining boundaries in the coordinate space:

```python
class AccessBoundary:
    def __init__(self, time_range=None, relevance_range=None, angle_range=None):
        self.time_range = time_range  # (min_time, max_time) or None for unlimited
        self.relevance_range = relevance_range  # (min_r, max_r) or None for unlimited
        self.angle_range = angle_range  # (min_θ, max_θ) or None for unlimited
        
    def contains_node(self, node):
        """Check if a node falls within this boundary"""
        t, r, θ = node.position
        
        if self.time_range and not (self.time_range[0] <= t <= self.time_range[1]):
            return False
            
        if self.relevance_range and not (self.relevance_range[0] <= r <= self.relevance_range[1]):
            return False
            
        if self.angle_range:
            # Handle circular angle range (may wrap around 2π)
            if self.angle_range[0] <= self.angle_range[1]:
                if not (self.angle_range[0] <= θ <= self.angle_range[1]):
                    return False
            else:
                if not (θ >= self.angle_range[0] or θ <= self.angle_range[1]):
                    return False
                    
        return True
```

### 2. Branch-Based Permissions

Access control can be applied at the branch level:

```python
class BranchPermission:
    def __init__(self, branch_id, permission_type, user_id=None, role_id=None):
        self.branch_id = branch_id
        self.permission_type = permission_type  # read, write, admin, etc.
        self.user_id = user_id
        self.role_id = role_id
        
    def grants_access(self, user, requested_permission):
        """Check if this permission grants the requested access to the user"""
        if self.user_id and self.user_id != user.id:
            return False
            
        if self.role_id and self.role_id not in user.roles:
            return False
            
        return self.permission_type_allows(requested_permission)
```

### 3. Node-Level Permissions

For fine-grained control, individual nodes can have specific permissions:

```python
class NodePermission:
    def __init__(self, node_id, permission_type, user_id=None, role_id=None, 
                 propagate_to_connections=False):
        self.node_id = node_id
        self.permission_type = permission_type
        self.user_id = user_id
        self.role_id = role_id
        self.propagate_to_connections = propagate_to_connections
```

## Permission Resolution Algorithm

When a user attempts to access a node, the system checks permissions in this order:

1. **Node-specific permissions** take precedence
2. **Branch-level permissions** apply if no node-specific permissions exist
3. **Coordinate boundary permissions** apply if no branch or node permissions match
4. **Default deny** if no permissions explicitly grant access

```python
def check_access(user, node, permission_type):
    """Check if user has the specified permission for the node"""
    
    # 1. Check node-specific permissions
    node_permission = find_node_permission(node.id, user, permission_type)
    if node_permission is not None:
        return node_permission.grants_access(user, permission_type)
    
    # 2. Check branch-level permissions
    branch_permission = find_branch_permission(node.branch_id, user, permission_type)
    if branch_permission is not None:
        return branch_permission.grants_access(user, permission_type)
    
    # 3. Check coordinate boundary permissions
    for boundary in user.accessible_boundaries:
        if boundary.contains_node(node):
            # Check if the boundary grants the requested permission
            if boundary.permission_type_allows(permission_type):
                return True
    
    # 4. Default deny
    return False
```

## Temporal Access Control

The system supports time-based access control through several mechanisms:

### 1. Time-Limited Views

Users can be granted access to specific time slices of the knowledge base:

```python
def create_time_limited_view(user, start_time, end_time):
    """Create a view of the knowledge base limited to a time range"""
    boundary = AccessBoundary(time_range=(start_time, end_time))
    user.accessible_boundaries.append(boundary)
```

### 2. Historical Immutability

Ensuring past states cannot be modified:

```python
def can_modify_node(user, node):
    """Check if a user can modify a node"""
    # Admin users may have special temporal modification privileges
    if user.has_role('temporal_admin'):
        return True
        
    # Normal users can only modify nodes within a recency window
    recency_window = get_recency_window()
    current_time = get_current_time()
    
    if node.timestamp < (current_time - recency_window):
        return False
        
    # Check write permissions
    return check_access(user, node, 'write')
```

## Branch Security Model

The branch mechanism provides natural security isolation:

### 1. Branch Creation Control

Restrict who can create new branches:

```python
def can_create_branch(user, from_branch_id):
    """Check if a user can create a new branch"""
    if not user.has_permission('create_branch'):
        return False
        
    # Check if user has access to the source branch
    source_branch = get_branch(from_branch_id)
    return check_access(user, source_branch, 'branch_from')
```

### 2. Branch Inheritance

Child branches can inherit access controls from parent branches:

```python
def create_branch_with_permissions(parent_branch, center_node, name, user):
    """Create a new branch with inherited permissions"""
    new_branch = create_branch(parent_branch, center_node, name)
    
    # Copy parent branch permissions to new branch
    for permission in parent_branch.permissions:
        new_permission = permission.clone()
        new_permission.branch_id = new_branch.id
        new_branch.permissions.append(new_permission)
    
    # Add creator as admin of the new branch
    admin_permission = BranchPermission(
        branch_id=new_branch.id,
        permission_type='admin',
        user_id=user.id
    )
    new_branch.permissions.append(admin_permission)
    
    return new_branch
```

### 3. Branch Isolation

Each branch can maintain separate access control policies:

```python
def isolate_branch_permissions(branch_id, maintain_admin_access=True):
    """Isolate a branch from inheriting parent permissions"""
    branch = get_branch(branch_id)
    
    # Store original admins if we want to maintain their access
    admins = []
    if maintain_admin_access:
        admins = [p.user_id for p in branch.permissions 
                 if p.permission_type == 'admin' and p.user_id is not None]
    
    # Remove inherited permissions
    branch.inherit_parent_permissions = False
    
    # Re-add admin permissions if needed
    if maintain_admin_access:
        for admin_id in admins:
            admin_permission = BranchPermission(
                branch_id=branch.id,
                permission_type='admin',
                user_id=admin_id
            )
            branch.permissions.append(admin_permission)
```

## Cross-Cutting Security Concerns

### 1. Encryption

The system supports encryption at multiple levels:

- **Node Content Encryption**: Individual node content can be encrypted with different keys
- **Connection Encryption**: Relationship data can be separately encrypted
- **Coordinate Encryption**: Position coordinates can be encrypted to prevent unauthorized structure analysis

### 2. Audit Trails

Comprehensive audit logging tracks access and modifications:

```python
def log_access(user, node, action_type, timestamp=None):
    """Log an access to the audit trail"""
    if timestamp is None:
        timestamp = get_current_time()
        
    audit_entry = AuditEntry(
        user_id=user.id,
        node_id=node.id,
        branch_id=node.branch_id,
        action_type=action_type,
        timestamp=timestamp,
        node_position=node.position,
        user_ip=get_user_ip(user)
    )
    
    audit_log.append(audit_entry)
```

### 3. Differential Privacy

For sensitive knowledge bases, differential privacy can be applied to query results:

```python
def apply_differential_privacy(query_result, privacy_budget, sensitivity):
    """Apply differential privacy noise to query results"""
    epsilon = privacy_budget / sensitivity
    
    # Apply Laplace mechanism
    noise = generate_laplace_noise(0, 1/epsilon)
    
    # Apply noise differently based on result type
    if isinstance(query_result, int):
        return query_result + int(round(noise))
    elif isinstance(query_result, float):
        return query_result + noise
    elif isinstance(query_result, list):
        return [apply_differential_privacy(item, privacy_budget/len(query_result), sensitivity) 
                for item in query_result]
    else:
        return query_result  # No noise for non-numeric types
```

## Integration with External Systems

### 1. Authentication Integration

The system can integrate with external identity providers:

```python
class ExternalAuthProvider:
    def authenticate(self, credentials):
        """Authenticate user with external system"""
        
    def get_user_roles(self, user_id):
        """Retrieve roles from external system"""
        
    def validate_token(self, token):
        """Validate a security token"""
```

### 2. Permission Synchronization

Synchronize with external permission systems:

```python
def sync_permissions_from_external(external_system, mapping_config):
    """Sync permissions from an external system"""
    external_permissions = external_system.get_permissions()
    
    for ext_perm in external_permissions:
        # Map external permission to internal
        internal_perm = map_permission(ext_perm, mapping_config)
        
        # Apply to appropriate entity (node, branch, etc.)
        apply_permission(internal_perm)
```

## Implementation Considerations

### 1. Permission Caching

For performance, cache permission decisions:

```python
class PermissionCache:
    def __init__(self, max_size=10000, ttl=300):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        
    def get(self, user_id, node_id, permission_type):
        """Get cached permission decision"""
        key = f"{user_id}:{node_id}:{permission_type}"
        entry = self.cache.get(key)
        
        if entry and (time.time() - entry['timestamp']) < self.ttl:
            return entry['result']
            
        return None
        
    def set(self, user_id, node_id, permission_type, result):
        """Cache a permission decision"""
        key = f"{user_id}:{node_id}:{permission_type}"
        
        # Evict if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
            
        self.cache[key] = {
            'result': result,
            'timestamp': time.time()
        }
        
    def _evict_oldest(self):
        """Evict oldest cache entry"""
        oldest_key = min(self.cache, key=lambda k: self.cache[k]['timestamp'])
        del self.cache[oldest_key]
```

### 2. Performance Optimization

Optimize permission checks for common operations:

```python
def bulk_check_access(user, nodes, permission_type):
    """Efficiently check permissions for multiple nodes"""
    # Group nodes by branch to reduce permission lookups
    nodes_by_branch = {}
    for node in nodes:
        if node.branch_id not in nodes_by_branch:
            nodes_by_branch[node.branch_id] = []
        nodes_by_branch[node.branch_id].append(node)
    
    results = {}
    
    # Check branch permissions first (most efficient)
    for branch_id, branch_nodes in nodes_by_branch.items():
        branch_permission = find_branch_permission(branch_id, user, permission_type)
        if branch_permission and branch_permission.grants_access(user, permission_type):
            # All nodes in this branch are accessible
            for node in branch_nodes:
                results[node.id] = True
            continue
        
        # Need to check individual nodes
        for node in branch_nodes:
            results[node.id] = check_access(user, node, permission_type)
    
    return results
```

## Conclusion

The security and access control model for the temporal-spatial knowledge database leverages the unique coordinate-based structure to provide flexible, fine-grained protection. By combining dimensional boundaries, branch-level isolation, and node-specific permissions, the system can enforce complex security policies while maintaining performance.

This approach ensures that sensitive information is properly protected, even as the knowledge structure grows, branches, and evolves over time. The model supports both simple use cases with minimal configuration and complex enterprise scenarios requiring sophisticated access controls.
