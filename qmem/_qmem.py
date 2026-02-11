
from typing import Optional, Type
from copy import deepcopy
from requests import patch
import tqec

from ._operation import Operation, LoadOperation, StoreOperation, OperationType, IdleOperation, YokeOperation, YokeOperationType
from .yoke import YokedSurfaceCode
from .utility import Vec2, view_block_graph, construct_3D_diagram, Cube, Pipe
from ._patch import TqecMemoryPatch
from ._patch_type import PatchType
from ._controller import Controller, SimpleController
from ._path_generator import PathGenerator, BFSPathGenerator
from ._instruction import Instruction
from .exception import MemoryLayoutError




class QMemory(YokedSurfaceCode):
    """
    QMemory is a class that handles the operations of memory. 
    The interface of the QMemory is simple, which only needs to handle:
        - load: load the qubit from the memory out of the memory
        - store: store the qubit into the memory. 
                 The qubit can be stored into a specific location. 
                 If no location is specified, the qubit will be stored into the nearest available location.
        - move: move the qubit from one location to another location. This is for the qubit with no connectivity to the access hallway.
        - refresh: refresh the qubit in the memory, i.e., reset the memory cell to the |0> state.
        - rotate: rotate the qubit in the memory, i.e., apply a Pauli rotation to the qubit in the memory.
    """

    # _CYCLE = 1
    def __init__(self,
                 memory_layout: list[list[int]],
                 path_finding_algorithm: Type[PathGenerator] = BFSPathGenerator,
                 controller: Type[Controller] = SimpleController,
                 maximum_cycles: int = 1000,
                 qubit_diameter: int = 3
                ):
        """
        Initialize the QMemory with the given memory layout dimension and access hallway layout.
        Args:
            memory_layout_dimension (tuple[int]): The dimensions of the memory layout. It's referred to as (rows, columns) for 2D memory.
            access_hallway_layout (list[Vec2]): The list of coordinates representing the access hallway layout. 
            

        Caveats:
            - The coordinates in the access hallway layout is in the form of (x, y), where x is the column index and y is the row index.
              This contradicts to the usual (row, column) format. It would be easier to deal with this by unpacking the position 
              received from Vec2.get_position() as (x, y) or (col, row) directly.
        """
        self.maximum_cycles = maximum_cycles
        self.memory_layout = deepcopy(memory_layout)
        self.memory_layout_dimension = (len(memory_layout), len(memory_layout[0]) if len(memory_layout) > 0 else 0)
        self.access_hallway_layout = []

        self.memory_storage = deepcopy(memory_layout)
        self.outlet_points = []

        for y, row in enumerate(memory_layout):
            for x, cell in enumerate(row):

                if cell == 0:
                    self.memory_storage[y][x] = TqecMemoryPatch(
                        pos=Vec2(x, y), 
                        patch_type=PatchType.DATA, 
                        maximum_cycles=maximum_cycles
                    )
                elif cell == 1:
                    self.memory_storage[y][x] = TqecMemoryPatch(
                        pos=Vec2(x, y), 
                        patch_type=PatchType.ACCESS_HALLWAY,
                        maximum_cycles=maximum_cycles
                    )
                    self.access_hallway_layout.append(Vec2(x, y))
                elif cell == 2:
                    self.memory_storage[y][x] = TqecMemoryPatch(
                        pos=Vec2(x, y), 
                        patch_type=PatchType.OUTLET,
                        maximum_cycles=maximum_cycles
                    )
                    self.outlet_points.append(Vec2(x, y))
                elif cell == -1:
                    self.memory_storage[y][x] = TqecMemoryPatch(
                        pos=Vec2(x, y), 
                        patch_type=PatchType.WALL,
                        maximum_cycles=maximum_cycles
                    )
                else: 
                    raise ValueError("Memory layout can only contain 0, 1, 2, and -1.")

        self.width = self.memory_layout_dimension[1]
        self.height = self.memory_layout_dimension[0]
        self.path_generator = path_finding_algorithm(map=self.memory_layout)
        self.controller = controller(memory_layout=self.memory_layout)
        self.tqec_patches : list[TqecMemoryPatch] = [patch for layer in self.memory_storage for patch in layer] 
        self.data_patches = [patch for patch in self.tqec_patches if patch.patch_type == PatchType.DATA]
        self.access_hallway_patches = [patch for patch in self.tqec_patches if patch.patch_type == PatchType.ACCESS_HALLWAY]
        self.outlet_patches = [patch for patch in self.tqec_patches if patch.patch_type == PatchType.OUTLET]
        self.wall_patches = [patch for patch in self.tqec_patches if patch.patch_type == PatchType.WALL]



    def generate_path(self, coord_from: Vec2, coord_to: Vec2 | list[Vec2]) -> list[int, list[TqecMemoryPatch], TqecMemoryPatch]:
        """
        Find the path from the given access hallway coordinate to the nearest outlet point using BFS.
        Args:
            coord_from (Vec2): The starting coordinate.
            coord_to (Vec2): The ending coordinate.
        Returns:
            list[TqecMemoryPatch]: The list of patches along the path from the access hallway to the outlet point.
            TqecMemoryPatch: The coordinate of the outlet point
        Raise:
            ValueError: If the given coordinate is not an access hallway or no path is found to any outlet point.
        """
        
        paths = self.path_generator.path(start=coord_from, goal=coord_to)
        if not paths:
            raise ValueError("No path found from the access hallway to any outlet point.")
        
        from_patch = self.memory_storage[paths[0].y][paths[0].x]
        access_hallway_positions = paths[1:-1] # exclude the outlet point
        access_hallway_patches = [self.memory_storage[p.y][p.x] for p in access_hallway_positions]
        to_patch = self.memory_storage[paths[-1].y][paths[-1].x]
        return from_patch, access_hallway_patches, to_patch

    def get_patches_at(self, positions: list[Vec2]) -> list[TqecMemoryPatch]:
        """
        Get the list of patches at the given positions.
        Args:
            positions (list[Vec2]): The list of coordinates to get the patches from.
        Returns:
            list[TqecMemoryPatch]: The list of patches at the given positions.
        """

        patches = []
        for pos in positions:
            patch = self.memory_storage[pos.y][pos.x]
            patches.append(patch)
        return patches

    def _move(self, coord_from: Vec2, coord_to: Vec2):
        """
        Move the qubit from coord_from to coord_to.
        Args:
            coord_from (Vec2): The coordinate to move the qubit from.
            coord_to (Vec2): The coordinate to move the qubit to.
        Returns:
            dict: A dictionary containing the qubit patch and the access hallway patches involved in the move operation. 
        """
        from_patch, access_hallway_patches, to_patch = self.generate_path(coord_from=coord_from, coord_to=coord_to) 
        return {
            "from_patch": from_patch,
            "access_hallway_patches": access_hallway_patches,
            "to_patch": to_patch,
        }


    def load(self, q_id, cyl) -> LoadOperation:
        """
        Load the qubit at the given coordinate out of the memory.
        The load operation involves growing the patch to the access hallway and then shrinking it out.
        The affected access hallway patches are just the ones connecting to the target patch
        and the rest of the access hallway patches along the way to the exit point.
        Args:
            q_id: The identifier of the qubit to be loaded.
            cyl: The cycle at which the load operation is performed.
        Returns:
            list[TqecMemoryPatch, list[TqecMemoryPatch], TqecMemoryPatch]: A list containing the qubit patch and the access hallway patches involved in the load operation.
        """
        
        coord = self.controller.get_mapping_coord(q_id)
        self.controller.unmap(q_id)
        from_patch, access_hallway_patches, to_patch = self.generate_path(coord_from=coord, coord_to=self.outlet_points) 

        return LoadOperation(
            target_patch=from_patch,
            access_hallway_patches=access_hallway_patches,
            outlet_patch=to_patch,
            cycle=cyl
        )
    

    def store(self, q_id, cyl) -> StoreOperation:
        """
        Store the qubit at the given coordinate into the memory.
        The store operation involves growing the patch from the access hallway to the target patch and then shrinking
        it into the target patch.
        The affected access hallway patches are just the ones connecting to the target patch
        and the rest of the access hallway patches along the way from the outlet point.

        (It's actually the same as load operation but in reverse order.)
        Args:
            q_id: The identifier of the qubit to be stored.
            cyl: The cycle at which the store operation is performed.
        Returns:
            list[TqecMemoryPatch, list[TqecMemoryPatch], TqecMemoryPatch]: A list containing the qubit patch and the access hallway patches involved in the store  
        """

        coord_to = self.controller.map(q_id, cyl)
        # print("Store to ", coord_to)
        # It was supposed to be from_patch, access_hallway, and to_patch, but since find the path in a reverse way so that we swap the orer of from and to.
        target_coord, access_hallway_patches, outlet_patch = self.generate_path(coord_from=coord_to, coord_to=self.outlet_points)
        access_hallway_patches.reverse()

        return StoreOperation(
            target_patch=target_coord,
            access_hallway_patches=access_hallway_patches,
            outlet_patch=outlet_patch,
            cycle=cyl
        )
    
    def idle(self, q_id, cyl) -> IdleOperation:
        coord = self.controller.get_mapping_coord(q_id)
        patch = self.memory_storage[coord.y][coord.x]
        return IdleOperation(
            idling_patch=patch,
            cycle=cyl)

    
    def __yoke(self, line: Vec2, cyl) -> Optional[YokeOperation]:
        """
        Unified method to handle both row and column yoke operations.
        """
        is_row = line.is_row()
        is_col = line.is_col()
        assert is_row or is_col, "Input must be either a row (x=None) or column (y=None)."
        
        limit = self.width if is_row else self.height

        all_points = line.expand(range(limit))
        occupied_patches = [
            patch for patch in self.get_patches_at(all_points) 
            if self.controller.mapping.get(patch.pos) is not None
        ]

        if not occupied_patches:
            return None

        pos = occupied_patches[0].pos
        access_line = None

        checks = [ (0, 1), (0, -1) ] if is_row else [ (1, 0), (-1, 0) ]
        
        for dx, dy in checks:
            nx, ny = pos.x + dx, pos.y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.memory_storage[ny][nx].patch_type == PatchType.ACCESS_HALLWAY:
                    access_line = Vec2.row(ny) if is_row else Vec2.col(nx)
                    break

        if not access_line:
            label = "row" if is_row else "column"
            raise MemoryLayoutError(f"No access hallway found for the occupied patch in the {label}.")

        return YokeOperation(
            target_patches=occupied_patches,
            access_hallway_patches=self.get_patches_at(list(access_line.expand(range(limit)))),
            cycle=cyl,
            op_type=YokeOperationType.YOKE_ROW if is_row else YokeOperationType.YOKE_COL
        )

    def yoke_row(self, row: Vec2, cyl):
        return self.__yoke(row, cyl)

    def yoke_col(self, col: Vec2, cyl):
        return self.__yoke(col, cyl)


    def _closest_access_hallway(self, coord: Vec2, points: list[Vec2]) -> list[int, Vec2]:
        """
        Calculate the Manhattan distance from the given coordinate to the nearest point in the list.
        Args:
            coord (Vec2): The coordinate to calculate the distance from.
            points (list[Vec2]): The list of coordinates to calculate the distance to.
        Returns:
            int: The Manhattan distance to the nearest point.
            Vec2: The coordinate of the nearest point.
        """
        min_distance = float('inf')
        closest_access_hallway = None
        for p in points:
            distance = sum(abs(a - b) for a, b in zip(coord, p))
            if distance < min_distance:
                min_distance = distance
                closest_access_hallway = p
        return closest_access_hallway

        
    def view_memory(self):
        for layer in self.memory_storage:
            for col in layer:
                print(f"[{col}]", end=" ")
            print()


    def run(self, instructions: dict[int, list[Instruction]]) -> list[list[Cube], list[list[Pipe]]]:


        all_pipes = []
        for cyl in instructions:
            ops = instructions[cyl]
            qids = self.controller.get_in_memory_qids() 
            print(f"Cycle {cyl} starting. In-memory q_ids: {qids}")
            for op in ops:
                if op.operation == OperationType.LOAD:
                    memory_operation = self.load(op.q_id, cyl)
                elif op.operation == OperationType.STORE:
                    memory_operation = self.store(op.q_id, cyl)
                elif op.operation == OperationType.YOKE_ROW or op.operation == OperationType.YOKE_COL:
                    memory_operation = self.__yoke(op.pos, cyl)
                    
                    cycle = memory_operation.cycle
                    if cycle > cyl:
                        patches = memory_operation.patches
                        for i in range(len(patches)):
                            patch = patches[i]
                            patch_id = self.controller.get_mapping_qid(patch.pos)
                            if patch_id is not None:
                                _cyl = cyl
                                while _cyl < cycle:
                                    idle_operation = self.idle(patch_id, _cyl)
                                    res = idle_operation.run()
                                    _cyl += 1
                                    if not res:
                                        continue
                                    pipes = idle_operation.to_tqec_pipes()
                                    all_pipes.append(pipes)

                cubes = memory_operation.run()
                pipes = memory_operation.to_tqec_pipes() 
                all_pipes.append(pipes)


            qids = self.controller.get_in_memory_qids() 
            for qid in qids:
                idle_operation = self.idle(qid, cyl)
                res = idle_operation.run()
                if not res:
                    continue
                pipes = idle_operation.to_tqec_pipes()
                all_pipes.append(pipes)
            print(f"Cycle {cyl} completed. In-memory q_ids: {qids}")

        all_cubes = []
        for patch in self.tqec_patches:
            cubes = patch.get_cubes()
            all_cubes.extend(cubes) 
        
        return all_cubes, all_pipes