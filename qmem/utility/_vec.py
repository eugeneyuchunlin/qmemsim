from dataclasses import dataclass

@dataclass(frozen=True)
class Vec2:
    """
    A class representing a 2-dimensional vector or coordinate.
    """
    x: float = 0
    y: float = 0

    def __iter__(self):
        yield self.x
        yield self.y

    def __add__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x + other.x, self.y + other.y)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x - other.x, self.y - other.y)
        return NotImplemented


if __name__ == "__main__":
    coord = Vec2(1, 2)
    print(coord)