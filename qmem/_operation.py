from abc import ABC, abstractmethod
from enum import Enum

from tqec.computation.block_graph import CubeKind, ZXCube
from tqec.utils.position import Position3D


from qmem._patch import TqecMemoryPatch, PatchType
from qmem.utility import Vec2, generate_cube_kinds, Cube, Pipe



class OperationType(Enum):
    INIT = "INIT"
    STORE = "STORE"
    LOAD = "LOAD"
    YOKE_ROW = "YOKE_ROW"
    YOKE_COL = "YOKE_COL"

class Operation(ABC):
    """
    Operation is consisted of a list of patches. 
    """

    def __init__(self):
        super().__init__()
        self.positions = []
        self.pipes = []

    @abstractmethod
    def run(self):
        """
        Run the operation and update the patches accordingly
        """

    
    @abstractmethod
    def to_tqec_pipes(self) -> list[tuple[Position3D, CubeKind]]:
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

    def to_tqec_pipes(self):
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


    def run(self):
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

        end_times = []        

        pipes = []
        cycle = self.from_patch.next_available_cycle(self.cycle)
        _cycle = cycle

        if self.from_patch.patch_type == PatchType.OUTLET: 
            self.from_patch.add_a_cube(cycle)
            positions.append(Position3D(self.from_patch.pos.x, self.from_patch.pos.y, cycle))
            cycle += 1
        else:
            pipes.append( Pipe(Position3D(self.from_patch.pos.x, self.from_patch.pos.y, cycle-1), Position3D(self.from_patch.pos.x, self.from_patch.pos.y, cycle)) )
        

        for i in range(len(self.patches) - 1):
            curr_patch = self.patches[i]
            next_patch = self.patches[i + 1]      
            while(next_patch.next_available_cycle(cycle) != cycle):
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

        # return the list of pipes
       
        for i in range(len(positions) - 1):
            pipes.append( Pipe(positions[i], positions[i + 1]) ) 

        self.positions = positions
        self.pipes = pipes  


        for patch in self.patches:
            end_times.append((patch.pos, patch.current_occupied_cycle))

        return self.positions
    
    def to_tqec_pipes(self):
        if not self.pipes or len(self.pipes) == 0:
            self.run()

        return self.pipes

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
    def __init__(self, idling_patch: TqecMemoryPatch, cycle):
        super().__init__()
        self.idling_patch = idling_patch
        self.cycle = cycle

    def __repr__(self):
        return f"IdleOp@{self.cycle}" 


    def run(self):
        cycle = self.idling_patch.next_available_cycle(self.cycle)
        
        if cycle > self.cycle:
            print(f"Warning: IdleOperation requested at cycle {self.cycle} but patch is busy. Assigned at cycle {cycle} instead.")
            return

        self.idling_patch.add_a_cube(cycle)
        ck = self.idling_patch.get_cube_kind(cycle)  # ensure the cube kind is set
        self.idling_patch.set_cube_kind(cycle, ck)
        self.positions = [Position3D(self.idling_patch.pos.x, self.idling_patch.pos.y, cycle)]
        self.pipes = [Pipe(Position3D(self.idling_patch.pos.x, self.idling_patch.pos.y, cycle-1), Position3D(self.idling_patch.pos.x, self.idling_patch.pos.y, cycle))]
        return self.positions

    def to_tqec_pipes(self, joint:bool = False) -> tuple[list[Position3D], list]:
        """
        Convert the idle operation to tqec cubes and pipes.

        Returns:
            A tuple of empty list of cubes and list of pipes.
        """
        if not self.pipes or len(self.pipes) == 0:
            self.run()

        return self.pipes

class YokeOperationType(Enum):
    YOKE_ROW = "YOKE_ROW"
    YOKE_COL = "YOKE_COL" 

class YokeOperation(Operation):
    """
    A yoke operation that connects a set of patches and 
    """

    def __init__(self, target_patches: list[TqecMemoryPatch], access_hallway_patches: list[TqecMemoryPatch], cycle: int, op_type: YokeOperationType):
        super().__init__()

        self.patches = target_patches
        self.access_hallway_patches = access_hallway_patches
        self.cycle = cycle
        self.op_type = op_type

        next_available_cycles = [patch.next_available_cycle(cycle) for patch in self.patches + self.access_hallway_patches]
        max_next_available_cycle = max(next_available_cycles + [cycle])

        self.cycle = max(self.cycle, max_next_available_cycle)
        print(f"YokeOperation initialized at cycle {cycle}, but next available cycle for patches is {max_next_available_cycle}. Assigned at cycle {self.cycle} instead.")

    def run(self):
        cycle = self.cycle
        # align all cube kinds at the cycle
        # take the majority cube kind among the patches
         

        cube_kinds = [patch.get_cube_kind(cycle - 1) for patch in self.patches]
        majority_kind = max(set(cube_kinds), key=cube_kinds.count)
        print(f"Aligning cube kinds for YokeOperation at cycle {cycle}. Majority kind: {majority_kind}")

        kind = list(majority_kind.as_tuple())

        for patch in self.patches:
            patch.add_a_cube(cycle, ZXCube(x=kind[0], y=kind[1], z=kind[2]))
            self.positions.append(Position3D(patch.pos.x, patch.pos.y, cycle))
            self.pipes.append(Pipe(Position3D(patch.pos.x, patch.pos.y, cycle-1), Position3D(patch.pos.x, patch.pos.y, cycle))) 
         


        kind[1] = kind[1].flipped()  # flip the y basis for the access hallway patches 
        for patch in self.access_hallway_patches:
            patch.add_a_cube(cycle, ZXCube(x=kind[0], y=kind[1], z=kind[2]))
            self.positions.append(Position3D(patch.pos.x, patch.pos.y, cycle))
            # self.pipes.append(Pipe(Position3D(patch.pos.x, patch.pos.y, cycle-1), Position3D(patch.pos.x, patch.pos.y, cycle)))

        if self.op_type == YokeOperationType.YOKE_ROW:
            row_df = self.patches[0].pos.y - self.access_hallway_patches[0].pos.y
            for patch in self.patches:
                self.pipes.append(Pipe(Position3D(patch.pos.x, patch.pos.y, cycle), Position3D(patch.pos.x, patch.pos.y - row_df, cycle)))
        elif self.op_type == YokeOperationType.YOKE_COL:
            col_df = self.patches[0].pos.x - self.access_hallway_patches[0].pos.x
            for patch in self.patches:
                self.pipes.append(Pipe(Position3D(patch.pos.x, patch.pos.y, cycle), Position3D(patch.pos.x - col_df, patch.pos.y, cycle)))

        for i in range(len(self.access_hallway_patches) - 1):
            curr_patch = self.access_hallway_patches[i]
            next_patch = self.access_hallway_patches[i + 1]
            self.pipes.append(Pipe(Position3D(curr_patch.pos.x, curr_patch.pos.y, cycle), Position3D(next_patch.pos.x, next_patch.pos.y, cycle)))

        for patch in self.patches:
            patch.add_a_cube(cycle + 1, ZXCube(x=kind[0], y=kind[1].flipped(), z=kind[2]))
            self.positions.append(Position3D(patch.pos.x, patch.pos.y, cycle + 1))
            self.pipes.append(Pipe(Position3D(patch.pos.x, patch.pos.y, cycle), Position3D(patch.pos.x, patch.pos.y, cycle + 1)))
        
        return self.positions



    def to_tqec_pipes(self):
        return self.pipes
            