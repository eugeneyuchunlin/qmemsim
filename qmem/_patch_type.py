from enum import Enum
from tqec.computation.block_graph import CubeKind, ZXCube

class PatchType(Enum):
    DATA = "D"
    ACCESS_HALLWAY = "A"
    YOKE = "Y"
    OUTLET = "O"
    WALL = "W"

    def to_cube_kind(self) -> CubeKind:
        match self:
            case PatchType.DATA:
                return ZXCube.from_str("ZXX")
            case PatchType.ACCESS_HALLWAY:
                return ZXCube.from_str("XZX") # Fixed cubekind will cause an issue when enabling preemption in the access hallway. FIXME
            case PatchType.YOKE:
                return ZXCube.from_str("ZXX")
            case PatchType.OUTLET:
                return ZXCube.from_str("XZX")