from dataclasses import dataclass
from ._vec import Vec2
from bidict import bidict

@dataclass
class GraphNode:
    id: int
    position: Vec2
    value: int

class Graph(object):
    def __init__(self, layout: list[list[int]]):
        self.layout = layout
        self.bimap = bidict()
        self.nodes: list[GraphNode] = [] 
        self._build_nodes()
        self.edges = self.get_connectivity()

    def _build_nodes(self):
        """Populates bimap and creates GraphNode instances."""
        ctr = 0
        for y, row in enumerate(self.layout):
            for x, val in enumerate(row):
                pos = Vec2(x, y)
                self.bimap[pos] = ctr
                
                # Create the node (even for -1, or you can filter them out)
                node = GraphNode(id=ctr, position=pos, value=val)
                self.nodes.append(node)
                
                ctr += 1

    def get_node_by_id(self, node_id: int) -> GraphNode:
        return self.nodes[node_id]

    def get_connectivity(self) -> list[list[int]]:
        """Generates list of connected cell IDs excluding -1 values."""
        connectivity = []
        rows = len(self.layout)
        cols = len(self.layout[0]) if rows > 0 else 0

        for y in range(rows):
            for x in range(cols):
                # Skip connectivity logic if the cell is a wall (-1)
                if self.layout[y][x] == -1:
                    continue

                current_id = self.bimap[Vec2(x, y)]

                # Check Right
                if x + 1 < cols and self.layout[y][x + 1] != -1:
                    connectivity.append([current_id, self.bimap[Vec2(x+1, y)]])

                # Check Down
                if y + 1 < rows and self.layout[y + 1][x] != -1:
                    connectivity.append([current_id, self.bimap[Vec2(x, y+1)]])

        return connectivity
    

if __name__ == "__main__":
    layout = [
        [0, 0, 0, 0, 0, -1],
        [1, 1, 1, 1, 1, 2],
        [0, 0, 1, 0, 0, -1],
        [0, 0, 1, 0, 0, -1],
        [1, 1, 1, 1, 1, 2],
        [0, 0, 0, 0, 0, -1],
    ]

    graph = Graph(layout)
    print(graph.nodes)