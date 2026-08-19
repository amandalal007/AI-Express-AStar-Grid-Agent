"""
environment.py
---------------
Defines the Grid environment for the AI Express Hackathon
Track 1: Warehouse Logistics Agent (Unit 2 - Informed Search).

Scenario: an autonomous forklift must pick up a package and deliver it to a
designated loading bay in a grid warehouse, navigating around static shelf
obstacles. A shelf/pallet can also topple into an aisle mid-run, forcing the
forklift to replan (bonus: Dynamic Replanning, credited under the
"Algorithmic Correctness" rubric item alongside A*).

PEAS summary for this environment:
    Performance measure : Deliver the package to the loading bay with
                           minimum path cost (steps); minimise nodes
                           expanded / replanning time.
    Environment          : 2D discrete grid warehouse floor, partially
                           dynamic (a shelf/pallet can topple into an aisle
                           at runtime, forcing the forklift to replan).
    Actuators            : Move Up / Down / Left / Right by one grid cell.
    Sensors              : Full observability of static shelf obstacles at
                            start; the forklift "senses" a new aisle
                            blockage only once it appears on its planned
                            route (simulated dynamic environment).
"""

from __future__ import annotations
import random
from collections import deque
from typing import Iterable, List, Set, Tuple

Cell = Tuple[int, int]


class Grid:
    """A simple 2D grid world with static + dynamically-added obstacles."""

    # 4-connected movement: Up, Down, Left, Right
    MOVES: List[Cell] = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    def __init__(
        self,
        width: int,
        height: int,
        obstacles: Iterable[Cell] = (),
        start: Cell = (0, 0),
        goal: Cell = None,
    ):
        self.width = width
        self.height = height
        self.obstacles: Set[Cell] = set(obstacles)
        self.start = start
        self.goal = goal if goal is not None else (width - 1, height - 1)

        assert self.in_bounds(self.start), "Start cell out of bounds"
        assert self.in_bounds(self.goal), "Goal cell out of bounds"
        assert self.start not in self.obstacles, "Start cell cannot be an obstacle"
        assert self.goal not in self.obstacles, "Goal cell cannot be an obstacle"

    # ------------------------------------------------------------------ #
    # Warehouse-scenario aliases (Track 1 naming: pickup point -> loading bay)
    # ------------------------------------------------------------------ #
    @property
    def pickup_point(self) -> Cell:
        return self.start

    @property
    def loading_bay(self) -> Cell:
        return self.goal

    # ------------------------------------------------------------------ #
    # Core environment queries
    # ------------------------------------------------------------------ #
    def in_bounds(self, cell: Cell) -> bool:
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def is_free(self, cell: Cell) -> bool:
        return cell not in self.obstacles

    def is_valid(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and self.is_free(cell)

    def neighbors(self, cell: Cell) -> List[Cell]:
        """Return valid (in-bounds, non-obstacle) neighbor cells of `cell`."""
        x, y = cell
        result = []
        for dx, dy in self.MOVES:
            nxt = (x + dx, y + dy)
            if self.is_valid(nxt):
                result.append(nxt)
        return result

    def reachable_free_cells(self, source: Cell) -> Set[Cell]:
        """BFS flood-fill: every free cell reachable from `source`
        (`source` itself included). Used to pick a random-but-solvable
        loading bay on each redo."""
        visited = {source}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            for nxt in self.neighbors(current):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return visited

    # ------------------------------------------------------------------ #
    # Dynamic environment support (for replanning demo)
    # ------------------------------------------------------------------ #
    def add_obstacle(self, cell: Cell) -> bool:
        """Add a new obstacle at runtime. Returns False if cell is start/goal."""
        if cell in (self.start, self.goal):
            return False
        self.obstacles.add(cell)
        return True

    def pick_dynamic_obstacle(self, path: List[Cell], agent_index: int) -> Cell | None:
        """
        Pick a cell further ahead on the forklift's current path to convert
        into a surprise obstacle (e.g. a toppled pallet blocking the aisle),
        simulating a dynamic/partially observable warehouse. Used to trigger
        live replanning during the demo.
        """
        ahead = path[agent_index + 2:]  # leave a couple of safety cells
        candidates = [c for c in ahead if c not in (self.start, self.goal)]
        if not candidates:
            return None
        return candidates[len(candidates) // 2]

    # ------------------------------------------------------------------ #
    # Factory helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def default_layout(cls) -> "Grid":
        """
        A fixed, reproducible warehouse floor plan: the forklift starts at
        the pickup point (top-left) and must deliver to the loading bay
        (bottom-right), navigating around rows of storage shelves.
        Good for demos/screen recording.
        """
        width, height = 16, 10
        start = (0, 0)
        goal = (width - 1, height - 1)
        walls = set()

        # Vertical shelf-row segments with single-cell aisle gaps.
        for y in range(0, 8):
            walls.add((4, y))
        walls.discard((4, 6))  # gap

        for y in range(2, height):
            walls.add((9, y))
        walls.discard((9, 8))  # gap

        for y in range(0, 6):
            walls.add((12, y))
        walls.discard((12, 4))  # gap

        walls.discard(start)
        walls.discard(goal)
        return cls(width, height, obstacles=walls, start=start, goal=goal)

    @classmethod
    def random_layout(cls, width=16, height=10, obstacle_ratio=0.22, seed=None, max_attempts=200) -> "Grid":
        """
        Random warehouse floor plan. Regenerates the shelf layout (up to
        `max_attempts` times) until it verifies a path actually exists
        between the pickup point and the loading bay -- a randomly placed
        obstacle set can otherwise seal off the goal entirely, which would
        fail mid-demo.
        """
        rng = random.Random(seed)
        start = (0, 0)
        goal = (width - 1, height - 1)
        candidate_cells = [
            (x, y) for x in range(width) for y in range(height) if (x, y) not in (start, goal)
        ]
        n_obstacles = int(width * height * obstacle_ratio)

        for _ in range(max_attempts):
            shuffled = list(candidate_cells)
            rng.shuffle(shuffled)
            walls = set(shuffled[:n_obstacles])
            if cls._is_solvable(width, height, walls, start, goal):
                return cls(width, height, obstacles=walls, start=start, goal=goal)

        # Fallback (astronomically unlikely to be reached): no obstacles,
        # which is always solvable.
        return cls(width, height, obstacles=set(), start=start, goal=goal)

    @staticmethod
    def _is_solvable(width: int, height: int, walls: Set[Cell], start: Cell, goal: Cell) -> bool:
        """BFS reachability check used by random_layout() to guarantee a
        generated maze always has a path from start to goal."""
        visited = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            if (x, y) == goal:
                return True
            for dx, dy in Grid.MOVES:
                nxt = (x + dx, y + dy)
                if (
                    0 <= nxt[0] < width
                    and 0 <= nxt[1] < height
                    and nxt not in walls
                    and nxt not in visited
                ):
                    visited.add(nxt)
                    queue.append(nxt)
        return False