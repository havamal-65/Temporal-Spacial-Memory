import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation

# --- Node Data Generation ---
np.random.seed(42)
num_nodes = 20
times = np.sort(np.random.randint(0, 10, size=num_nodes))
distances = np.random.uniform(0.5, 2.0, size=num_nodes)
angles = np.random.uniform(0, 2 * np.pi, size=num_nodes)
max_time = times.max()

# --- Edge Data Generation (Simple Sequential Example) ---
# Connect node i to node i+1 if they appear at the same or next time step
edges = []
for i in range(num_nodes - 1):
    # Example logic: connect sequentially appearing nodes
    if times[i+1] <= times[i] + 1: # Connect if time difference is 0 or 1
         # Check distance/angle proximity (optional, simple example connects all sequential)
         edges.append((i, i + 1))

# --- Coordinate Conversion ---
def get_cartesian_3d(time, distance, angle):
    x = time
    y = distance * np.cos(angle)
    z = distance * np.sin(angle)
    return x, y, z

# --- Plot Setup ---
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')
ax.set_xlim(0, max_time + 1)
ax.set_ylim(-2.5, 2.5)
ax.set_zlim(-2.5, 2.5)
ax.set_xlabel("Time (X)")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.set_title("Temporal-Spatial Mesh (GraphRAG-like View)")

# --- Artists Initialization ---
# Nodes (scatter plot)
node_coords_all = np.array([get_cartesian_3d(t, d, a) for t, d, a in zip(times, distances, angles)]).T
scat = ax.scatter([], [], [], s=80, c='blue', alpha=0.7, label="Nodes")

# Edges (line plots)
lines = []
for _ in edges:
    # Initialize each line with empty data, store the artist
    line, = ax.plot([], [], [], 'r-', alpha=0.5, lw=1) # Red lines for edges
    lines.append(line)

# Add a placeholder for the legend entry for edges
ax.plot([], [], [], 'r-', alpha=0.5, lw=1, label="Edges (Relationships)")
ax.legend()

# --- Animation Functions ---
def init():
    # Initialize nodes
    scat._offsets3d = ([], [], [])
    # Initialize edges
    for line in lines:
        line.set_data_3d([], [], [])
    return [scat] + lines # Return all artists

def animate(frame):
    # 1. Update Nodes
    node_mask = times <= frame
    visible_node_indices = np.where(node_mask)[0]
    if len(visible_node_indices) > 0:
         # Update scatter plot with coordinates of visible nodes
        scat._offsets3d = (node_coords_all[0, node_mask],
                           node_coords_all[1, node_mask],
                           node_coords_all[2, node_mask])
    else:
        scat._offsets3d = ([], [], []) # Ensure it's empty if no nodes visible

    # 2. Update Edges
    visible_edge_count = 0
    for i, (start_idx, end_idx) in enumerate(edges):
        # Check if *both* nodes connected by the edge are visible
        if node_mask[start_idx] and node_mask[end_idx]:
            # Get coordinates for the start and end nodes
            x_coords = [node_coords_all[0, start_idx], node_coords_all[0, end_idx]]
            y_coords = [node_coords_all[1, start_idx], node_coords_all[1, end_idx]]
            z_coords = [node_coords_all[2, start_idx], node_coords_all[2, end_idx]]
            # Update the line plot for this edge
            lines[i].set_data_3d(x_coords, y_coords, z_coords)
            visible_edge_count += 1
        else:
            # Hide the edge if one or both nodes are not visible
             lines[i].set_data_3d([], [], [])


    ax.set_title(f"Temporal-Spatial Mesh: Time = {frame} (Nodes: {len(visible_node_indices)}, Edges: {visible_edge_count})")
    return [scat] + lines # Return all artists

# --- Create and Show Animation ---
ani = animation.FuncAnimation(
    fig, animate, frames=range(max_time + 2), # Extend frames slightly
    init_func=init, blit=False, interval=400, repeat=True
)

plt.show() 