from pyparsing import Union
import tqec
from tqec.utils.position import Position3D
from tqec.utils.enums import Basis
from tqec.computation.block_graph import CubeKind, ZXCube
import webbrowser
import os
from dataclasses import dataclass


@dataclass
class Cube:
    kind: CubeKind
    pos: Position3D

@dataclass
class Pipe:
    from_pos: Position3D
    to_pos: Position3D


def view_block_graph(block_graph: tqec.BlockGraph, filename="block_graph.html", **args):
    """View a BlockGraph as an HTML file in the default web browser.

    This function generates an HTML representation of the provided BlockGraph
    and opens it in the user's default web browser for visualization.

    Args:
        block_graph (BlockGraph): The BlockGraph to be visualized.
        filename (str, optional): The name of the HTML file to be created.
            Defaults to "block_graph.html".
        **args: Additional keyword arguments to pass to the `view_as_html` method
            of the BlockGraph.
    """
    # Save to a local file
    block_graph.view_as_html(write_html_filepath=filename, **args)

    # Open it automatically in your default browser
    webbrowser.open('file://' + os.path.realpath(filename))

from enum import Enum
from tqec.computation.block_graph import CubeKind
from tqec.utils.position import Position3D

def zx_flip(_type: Union[str, Basis]) -> Union[str, Basis]:
    if isinstance(_type, str):
        try:
            basis_obj = Basis(_type)
        except ValueError:
            raise ValueError(f"Invalid basis string: {_type}")
    elif isinstance(_type, Basis):
        basis_obj = _type
    else:
        raise TypeError(f"Expected str or Basis, got {type(_type)}")

    flipped_basis = basis_obj.flipped()
    return str(flipped_basis) if isinstance(_type, str) else flipped_basis

class Dynamic(Enum):
    X = "X"
    Y = "Y"
    Z = "Z"
    U = "U"  # placeholder, undetermined

class PositionToDynamicMapper:
    type_to_dynamic = {
        Dynamic.X: 0,
        Dynamic.Y: 1,
        Dynamic.Z: 2
    }

def excluder(axis1: Dynamic, axis2: Dynamic) -> list[Dynamic]:
    all_axes = {Dynamic.X, Dynamic.Y, Dynamic.Z}
    return list(all_axes - {axis1, axis2})


def cube_dynamic(prev_pos: Position3D, current_pos: Position3D) -> Dynamic:
    deltas = {
        Dynamic.X: abs(current_pos.x - prev_pos.x),
        Dynamic.Y: abs(current_pos.y - prev_pos.y),
        Dynamic.Z: abs(current_pos.z - prev_pos.z)
    }

    active_axes = [axis for axis, diff in deltas.items() if diff > 1e-9]

    if len(active_axes) == 0:
        raise ValueError("No movement detected: The cube is stationary.")
    
    if len(active_axes) > 1:
        raise ValueError(f"Diagonal movement detected across axes: {active_axes}")

    return active_axes[0]


def generate_cube_kinds(positions: list[Position3D], initial_kind: str=str("XZX")):
    size = len(positions)
    cube_kinds = [list(initial_kind)]
    for i in range(1, size):
        prev_pos = positions[i - 1]
        curr_pos = positions[i]
        next_pos = positions[i + 1] if i + 1 < size else None

        movement_axis1 = cube_dynamic(prev_pos, curr_pos)
        if next_pos:
            movement_axis2 = cube_dynamic(curr_pos, next_pos)
        else:
            movement_axis2 = movement_axis1  
         
        # types of the surface except for the movement axis must be the same
        prev_kind = cube_kinds[-1].copy()
        curr_kind = cube_kinds[-1].copy()
        curr_kind[PositionToDynamicMapper.type_to_dynamic[movement_axis1]] = Dynamic.U  # undetermine

        # print(curr_kind, movement_axis1, movement_axis2)


        if movement_axis1 == movement_axis2:
            # no change in movement axis
            curr_kind[PositionToDynamicMapper.type_to_dynamic[movement_axis1]] = prev_kind[PositionToDynamicMapper.type_to_dynamic[movement_axis1]]
        else:
            excluded_axis = excluder(movement_axis1, movement_axis2)[0]
            # print("Excluded axis:", excluded_axis)
             
            curr_kind[PositionToDynamicMapper.type_to_dynamic[movement_axis1]] = zx_flip(curr_kind[PositionToDynamicMapper.type_to_dynamic[excluded_axis]])

        cube_kinds.append(curr_kind)

    return cube_kinds


def construct_3D_diagram(all_cubes: list[Cube], pipes_batches: list[list[Pipe]]) -> tqec.BlockGraph:
    bg = tqec.BlockGraph()
    for cube in all_cubes:
        bg.add_cube(cube.pos, cube.kind)

    for pipes in pipes_batches:
        for pipe in pipes:
            bg.add_pipe(pipe.from_pos, pipe.to_pos)

    return bg