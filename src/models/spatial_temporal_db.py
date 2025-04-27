from typing import Dict
from dataclasses import dataclass

@dataclass
class Node:
    id: str
    type: str
    content: dict
    temporal_coordinate: float
    spatial_coordinates: list

class SpatialTemporalDB:
    def __init__(self):
        self.nodes: Dict[str, Node] = {} 

    def delete_node(self, node_id: str) -> bool:
        """Remove a node from the database.

        Args:
            node_id: The ID of the node to delete.

        Returns:
            True if the node was found and deleted, False otherwise.
        """
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False 