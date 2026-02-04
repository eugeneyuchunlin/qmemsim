from dataclasses import dataclass
from enum import Enum
from ._operation import OperationType

@dataclass
class Instruction:
    operation: OperationType
    q_id: int | list[int]
