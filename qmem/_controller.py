from abc import ABC, abstractmethod
from bidict import bidict
from qmem.utility import Vec2 # Assuming Vec2 is imported

class Controller(ABC):
    def __init__(self, memory_layout: list[list[int]], maximum_cycles: int = 100):
        self.memory_layout = memory_layout
        self.maximum_cycles = maximum_cycles

        self._3D_map = {}
        
        # Key: Vec2 coordinate, Value: q_id integer
        self.mapping = bidict()

        # Pre-populate self._3D_map
        for i in range(self.maximum_cycles):
            self._3D_map[i] = [
                [None for _ in range(len(memory_layout[0]))] 
                for _ in range(len(memory_layout))
            ]

    @abstractmethod
    def map(self, q_id, cycle):
        raise NotImplementedError("Subclasses must implement this method.")

    def unmap(self, q_id):
        """Removes the qubit from the bidict mapping."""
        if q_id in self.mapping.inverse:
            # .inverse allows looking up by value (q_id) to delete the pair
            del self.mapping.inverse[q_id]

    def get_mapping_coord(self, q_id) -> Vec2:
        """Get coordinate from q_id."""
        if q_id not in self.mapping.inverse:
            return None
        return self.mapping.inverse[q_id]

    def get_mapping_qid(self, coord: Vec2) -> int:
        """Get q_id from Vec2 coordinate."""
        if coord not in self.mapping:
            return None
        return self.mapping[coord]

    def get_in_memory_qids(self) -> list[int]:
        """Returns all q_ids currently in the bidict."""
        return list(self.mapping.values())

class SimpleController(Controller):
    def map(self, q_id, cycle) -> Vec2:
        # Iterate through the layout to find a valid cell (val == 0)
        for y, row in enumerate(self.memory_layout):
            for x, cell_type in enumerate(row):
                if cell_type == 0:
                    coord = Vec2(x, y)
                    # Check if this specific coordinate is already taken in the bidict
                    if coord not in self.mapping:
                        self.mapping[coord] = q_id
                        return coord
                        
        raise ValueError("No available memory cells to map the qubit.")