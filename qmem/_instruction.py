from dataclasses import dataclass
from enum import Enum
from ._operation import OperationType
from .utility import Vec2

@dataclass
class Instruction:
    operation: OperationType
    q_id: int | list[int] = None
    pos: Vec2 = None
