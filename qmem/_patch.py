import tqec
from qmem.yoke._patch import Patch
from qmem.utility import Vec2
from tqec.computation.block_graph import CubeKind, ZXCube
from tqec.utils.position import Position3D
from dataclasses import dataclass

from ._patch_type import PatchType

@dataclass
class Cube:
    kind: CubeKind
    pos: Position3D

class MemoryPatch(Patch):

    def __init__(self, pos: Vec2, patch_type: PatchType, maximum_cycles: int = 100):

        self.pos = pos
        self._cycle_layer = [None for i in range(maximum_cycles)] # Preallocate for 1000 cycles


    def __repr__(self):
        return f"{self.patch_type.value}({self.pos.x}, {self.pos.y})"
    

class TqecMemoryPatch(MemoryPatch):

    """
    A memory unit represents a single qubit memory cell in the QMemory.
    It stores the qubit patch and its cube kind information over time.  
    """
    def __init__(self, pos: Vec2, patch_type=PatchType, maximum_cycles: int = 100):
        super().__init__(pos, patch_type, maximum_cycles)
        self.pos = pos
        self.patch_type = patch_type
        self.current_occupied_cycle = -1

    def add_a_cube(self, cycle: int, cube_kind: CubeKind = None):
        """
        Add a cube at the specified cycle with the given cube kind.
        """
        if self._cycle_layer[cycle] is not None:
            raise ValueError(f"Cube at {self.pos} already exists at cycle {cycle}.")
        self._cycle_layer[cycle] = Cube(cube_kind, Position3D(self.pos.x, self.pos.y, cycle))
        self.current_occupied_cycle = max(self.current_occupied_cycle, cycle)

    def set_cube_kind(self, cycle: int, cube_kind: CubeKind):
        if self._cycle_layer[cycle] is None:
            raise ValueError(f"No cube exists at cycle {cycle} to set kind.")
        self._cycle_layer[cycle].kind = cube_kind

    def get_cube_kind(self, cycle: int) -> CubeKind:
        cyl = cycle
        if self._cycle_layer[cyl] is None:
            raise ValueError(f"No cube exists at cycle {cycle} to get kind.")

        cyl -= 1
        while cyl >= 0 and self._cycle_layer[cyl] is None:
            cyl -= 1 
        
        if self._cycle_layer[cyl] is not None:
            return self._cycle_layer[cyl].kind
        else:
            return ZXCube.from_str("XZX")  # default kind if no prior kind is found

    def is_free_at_cycle(self, cycle: int) -> bool:
        """
        Check if the memory unit is free at the given cycle.
        A memory unit is considered free at a cycle if it has no cube registered at that cycle.
        """
        return self._cycle_layer[cycle] is None
    
    def next_available_cycle(self, start_cycle: int) -> int:
        """
        Find the next available cycle starting from start_cycle.
        """
        cycle = max(start_cycle, self.current_occupied_cycle + 1)
        # while not self.is_free_at_cycle(cycle):
        #     cycle += 1
        return cycle
    

if __name__ == "__main__":
    patch = MemoryPatch(Vec2(1, 2))
    print(patch)