from dataclasses import dataclass
from typing import Iterable, Iterator, Optional
from tqec.utils.position import Position2D, Vec2D

class Vec2(Position2D):
    """
    A class representing a 2-dimensional vector or coordinate.
    """
    x: Optional[float] = None
    y: Optional[float] = None


    @classmethod
    def row(cls, y: int) -> 'Vec2':
        return cls(x=None, y=y)

    
    @classmethod
    def column(cls, x: int) -> 'Vec2':
        return cls(x=x, y=None)
    
    def is_row(self) -> bool:
        return self.x is None and self.y is not None

    def is_col(self) -> bool:
        return self.x is not None and self.y is None


    def expand(self, values: Iterable[int]) -> Iterator['Vec2']:
        """
        Generates a sequence of points.
        - If this is a row (x=None), it yields Vec2(val, y) for each val in values.
        - If this is a col (y=None), it yields Vec2(x, val) for each val in values.
        """
        if self.is_row():
            for val in values:
                yield Vec2(x=val, y=self.y)
        elif self.is_col():
            for val in values:
                yield Vec2(x=self.x, y=val)
        else:
            yield self

    def __iter__(self):
        yield self.x
        yield self.y

    def __add__(self, other):
        if isinstance(other, Vec2D) or isinstance(other, Position2D) or isinstance(other, Vec2): # Works with both Vec2D and Vec2
            new_x = None if (self.x is None or other.x is None) else self.x + other.x
            new_y = None if (self.y is None or other.y is None) else self.y + other.y
            return Vec2(new_x, new_y)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Vec2D) or isinstance(other, Position2D) or isinstance(other, Vec2): # Works with both Vec2D and Vec2
            new_x = None if (self.x is None or other.x is None) else self.x - other.x
            new_y = None if (self.y is None or other.y is None) else self.y - other.y
            return Vec2(new_x, new_y)
        return NotImplemented


if __name__ == "__main__":
    coord = Vec2.row(5)
    for i in coord.expand([1, 2, 3]):
        print(i)
    print(coord)
    print(coord.to_3d())
    print(coord.is_row())