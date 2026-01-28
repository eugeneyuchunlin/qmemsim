from abc import ABC, abstractmethod
from qmem.utility import Vec2


class PathGenerator(ABC):

    def __init__(self, memory_layout: list[list[int]]):
        self.memory_layout = memory_layout
        self.rows = len(memory_layout)
        self.cols = len(memory_layout[0]) if self.rows > 0 else 0

    @abstractmethod
    def path(self, start: Vec2, goal: Vec2 | list[Vec2]) -> list[Vec2]:
        """
        Generate a path from start to goal.
        Args:
            start: The starting position as a Vec2.
            goal: The goal position(s) as a Vec2 or list of Vec2.
        Returns:
            A list of Vec2 representing the path from start to a goal. 
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
class BFSPathGenerator(PathGenerator):


    def __init__(self, map: list[list[int]]):
        """
        Initialize the BFS with a given map.
        The map is a 2D grid where 0 represents walkable cells and 1
        represents obstacles.
        Args:
            map: A 2D list representing the grid map.
        """

        self.map = map
        self.rows = len(map)
        self.cols = len(map[0]) if self.rows > 0 else 0
    
    def path(self, start: Vec2, goal: Vec2 | list[Vec2]) -> list[Vec2]:
        """
        Perform BFS search from start to goal.
        Args:
            start: The starting position as a Vec2.
            goal: The goal position(s) as a Vec2 or list of Vec2.
        Returns:
            A list of Vec2 representing the path from start to goal.
        """
        goals = []
        if isinstance(goal, Vec2):
            goals.append(goal) 
        elif isinstance(goal, list):
            goals = goal

        #check start and goal validity
        map = self.map.copy()
        for goal in goals:
            if self.map[goal.y][goal.x] < 0:
                raise ValueError(f"Goal at {goal} is not accessible.")
            else:
                map[goal.y][goal.x] = 1  # Mark goal as walkable in the following search algorithm            
        
        if map[start.y][start.x] < 0: # Start is a wall
            raise ValueError("Start is not walkable.")
        map[start.y][start.x] = 1  # Mark start as walkable in the following search algorithm
        

        queue = [start]
        visited = set([start])
        parent = { start: None }        
        directions = [Vec2(0, 1), Vec2(1, 0), Vec2(0, -1), Vec2(-1, 0)]

        while queue:
            current = queue.pop(0)

            if current in goals:
                # Reconstruct path
                path = []
                while current is not None:
                    path.append(current)
                    current = parent[current]
                return path[::-1]  # Return reversed path

            for direction in directions:
                neighbor = current + direction

                if (0 <= neighbor.x < self.cols and
                    0 <= neighbor.y < self.rows and
                    map[neighbor.y][neighbor.x]  > 0 and
                    neighbor not in visited):

                    visited.add(neighbor)
                    parent[neighbor] = current
                    queue.append(neighbor)
        return []  # No path found  