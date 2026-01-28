from abc import ABC, abstractmethod
from ._patch import TqecMemoryPatch
from qmem.utility import Vec2

class Controller(ABC):

    def __init__(self, memory_layout: list[list[int]], ):
        self.memory_layout = memory_layout
        self.coord_to_qid = {}
        self.qid_to_coord = {}

        for y, row in enumerate(memory_layout):
            for x, cell in enumerate(row):
                if cell == 0:  # Assuming 0 represents a valid memory cell
                    self.coord_to_qid[(x, y)] = None  # Initialize with no qubit assigned


    @abstractmethod
    def map(self, q_id):
        """
        Map a qubit identified by q_id to a memory cell.
        Args:
            q_id: The identifier of the qubit to be mapped.
        Returns:
            A tuple (x, y) representing the coordinates of the mapped memory cell.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    

    def unmap(self, q_id):
        """
        Unmap a qubit identified by q_id from its memory cell.
        Args:
            q_id: The identifier of the qubit to be unmapped.
        Returns:
            None
        """
        coord = self.get_mapping_coord(q_id)
        self.coord_to_qid[(coord.x, coord.y)] = None
        self.qid_to_coord[q_id] = None

    
    def get_mapping_coord(self, q_id) -> Vec2:
        """
        Get the memory cell coordinates for a given qubit identifier.
        Args:
            q_id: The identifier of the qubit.
        Returns:
            A tuple (x, y) representing the coordinates of the mapped memory cell.
        """
        coord = self.qid_to_coord[q_id]
        if coord is None:
            raise ValueError(f"q_id: {q_id} is not in the mapping")
        return Vec2(*self.qid_to_coord[q_id])

    def get_mapping_qid(self, coord: Vec2) -> int:
        """
        Get the qubit identifier mapped to a given memory cell coordinates.
        Args:
            coord: A Vec2 representing the coordinates of the memory cell.
        Returns:
            The identifier of the qubit mapped to the given memory cell.
        """
        if self.coord_to_qid[(coord.x, coord.y)] is None:
            raise ValueError(f"coord: {coord} is not mapped to any q_id")
        return self.coord_to_qid[(coord.x, coord.y)]

    



class SimpleController(Controller):

    def map(self, q_id) -> Vec2:
        # find a free memory cell and assign the qubit to it

        for coord in self.coord_to_qid:
            # print("coord: ", coord, self.coord_to_qid[coord])
            if self.coord_to_qid[coord] is None:
                self.coord_to_qid[coord] = q_id
                self.qid_to_coord[q_id] = coord
                return Vec2(*coord)
                
        raise ValueError("No available memory cells to map the qubit.")