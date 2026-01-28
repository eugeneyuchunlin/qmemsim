from abc import ABC, abstractmethod
from enum import Enum

from tqec.computation.block_graph import CubeKind, ZXCube
from tqec.utils.position import Position3D


from qmem._patch import TqecMemoryPatch
from qmem.utility import Vec2, generate_cube_kinds



class OperationType(Enum):

    STORE = "STORE"
    LOAD = "LOAD"

class Operation(ABC):
    """
    Operation is consisted of a list of patches. 
    """
    
    @abstractmethod
    def to_tqec_cubes(self) -> list[tuple[Position3D, CubeKind]]:
        """
        Convert the operation to tqec cubes and pipes.

        Returns:
            A tuple of list of cubes and list of pipes.
        """

class InitializationOperation(Operation):
    """
    An initialization operation that initializes qubits in the memory.
    """
    def __init__(self, patches: list[TqecMemoryPatch], cycle: int = 0):
        self.patches = [patch for patch in patches if patch.patch_type == patch.patch_type.DATA]
        self.cycle = cycle

    def to_tqec_cubes(self):
        # nodes = additional_nodes + [
        #     (Position3D(patch.pos.x, patch.pos.y, self.cycle), patch.cube_kind) for patch in self.patches
        # ]
        # pipes: list[tuple[Position3D, CubeKind]] = []
        return

    def __repr__(self):
        return f"InitOp@{self.cycle}: {self.patches}"
    

class MoveOperation(Operation):
    """
    A move operation that moves qubits within the memory.
    """
    def __init__(self, from_patch: TqecMemoryPatch, access_hallway_patches: list[TqecMemoryPatch], to_patch: TqecMemoryPatch, cycle: int = 0):
        self.from_patch = from_patch
        self.access_hallway_patches = access_hallway_patches
        self.to_patch = to_patch

        self.patches = [from_patch] + access_hallway_patches + [to_patch]

        self.positions_patch_map = {patch.pos: patch for patch in self.patches}

        self.cycle = cycle

  

    def to_tqec_cubes(self):
        """
        Convert the move operation to tqec cubes and pipes.
        The function iterates through each patch in the move sequence, adding cubes for each cycle and pipes between them.
        If the next patch is not available at the current cycle, it waits until the patch is free.


        The pipes that the function handles are the pipes between each patch in the move sequence. For the pipes within each patch (i.e., vertical pipes), 
        they are handled by the TqecMemoryPatch class when adding a cycle.

        The function only cares the pipes generated to connect the patches in the move sequence. The vertical pipes and the cubes generated to joint the sequence are handled by each patch itself.

        Returns:
            pipes only
        """

        positions = []


        cycle = self.from_patch.next_available_cycle(self.cycle)
        _cycle = cycle
        self.from_patch.add_a_cube(cycle)
        positions.append(Position3D(self.from_patch.pos.x, self.from_patch.pos.y, cycle))
        cycle += 1

        for i in range(len(self.patches) - 1):
            curr_patch = self.patches[i]
            next_patch = self.patches[i + 1]      
            while(next_patch.is_free_at_cycle(cycle) is False):
                curr_patch.add_a_cube(cycle)
                positions.append(Position3D(curr_patch.pos.x, curr_patch.pos.y, cycle))

                cycle += 1
            curr_patch.add_a_cube(cycle)
            positions.append(Position3D(curr_patch.pos.x, curr_patch.pos.y, cycle))

        last_patch = self.patches[-1]
        last_patch.add_a_cube(cycle)
        positions.append(Position3D(last_patch.pos.x, last_patch.pos.y, cycle))

        cycle += 1
        last_patch.add_a_cube(cycle)
        positions.append(Position3D(last_patch.pos.x, last_patch.pos.y, cycle))

        bases = [basis.value for basis in self.from_patch.get_cube_kind(_cycle).as_tuple()]
        cube_kinds = generate_cube_kinds(positions, initial_kind=bases)

        for ck, pos in zip(cube_kinds, positions):
            patch = self.positions_patch_map[Vec2(pos.x, pos.y)]
            patch.set_cube_kind(pos.z, ZXCube.from_str("".join(ck)))

        

        return list(zip(positions, cube_kinds))

    def __repr__(self):
        return f"MoveOp@{self.cycle}: {self.patches}"
        
class LoadOperation(MoveOperation):
    """
    A load operation that loads qubits into the memory.
    """
    def __init__(self, 
                 target_patch: TqecMemoryPatch, 
                 access_hallway_patches: list[TqecMemoryPatch], 
                 outlet_patch: TqecMemoryPatch,
                 cycle: int = 0):
        
        super().__init__(target_patch, access_hallway_patches, outlet_patch, cycle)

    def __repr__(self):
        return f"LoadOp@{self.cycle}: {self.patches}"

class StoreOperation(MoveOperation):

    """
    A store operation that stores qubits from the memory.
    """
    def __init__(self, 
                 target_patch: TqecMemoryPatch, 
                 access_hallway_patches: list[TqecMemoryPatch], 
                 outlet_patch: TqecMemoryPatch, 
                 cycle: int = 0):
        
        super().__init__(outlet_patch, access_hallway_patches, target_patch, cycle)

    def __repr__(self):
        return f"StoreOp@{self.cycle}: {self.patches}"

class OperationManager:
    """
    OperationManager is a container that handles a series of operations which is a sequence of merge, split, joint measurements, etc...
    OperationManager also keeps track of the cycle number and ensures there is no conflict between operations at the same cycle.
    The conflict means two operations trying to operate on the same qubit patch at the same cycle.


    """
    _CYCLE = 0
    def __init__(self):
        self.container = {}

    def add_operation(self, operation: Operation):
                
        pass 


class IdleOperation(Operation):
    """
    An idle operation that does nothing.
    """
    def __repr__(self):
        return f"IdleOp@{self.cycle}" 


    def to_tqec_cubes_and_pipes(self, joint:bool = False) -> tuple[list[Position3D], list]:
        """
        Convert the idle operation to tqec cubes and pipes.

        Returns:
            A tuple of empty list of cubes and list of pipes.
        """
        return super().to_tqec_cubes_and_pipes(joint, False)