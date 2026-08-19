"""
agent.py
--------
A* search agent for the AI Express Hackathon
Track 1: Warehouse Logistics Agent (Unit 2 - Informed Search).

Core algorithmic formulation
    State space   : every free (non-obstacle) grid cell (x, y) on the
                    warehouse floor.
    Initial state : forklift's current cell (pickup point at the start).
    Goal test     : state == goal (the loading bay).
    Actions       : Up / Down / Left / Right (unit cost each).
    Path cost     : g(n) = number of moves taken so far (uniform step cost = 1).
    Heuristic     : h(n) = Manhattan distance to goal
                     h(n) = |x - goal_x| + |y - goal_y|
                     (admissible & consistent for 4-connected grids -> A*
                     is guaranteed optimal). This is exactly the heuristic
                     specified by the Track 1 brief.
    Evaluation    : f(n) = g(n) + h(n)

Complexity (theoretical)
    Time  : O(b^d) worst case, bounded by O(V log V) with a binary-heap
            priority queue over V = width*height reachable cells.
    Space : O(V) for the open/closed sets.

This module exposes `astar_search`, implemented as a *generator* so the
Pygame visualizer can render each node expansion live (real-time
decision-log requirement) instead of only showing the final path.
"""

from __future__ import annotations
import heapq
import itertools
import time
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

Cell = Tuple[int, int]


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass
class SearchEvent:
    """One yielded step of the A* generator, consumed by the visualizer/logger."""
    kind: str  # "expand" | "done" | "failed"
    node: Optional[Cell] = None
    g: float = 0.0
    h: float = 0.0
    f: float = 0.0
    nodes_expanded: int = 0
    frontier_size: int = 0
    path: Optional[List[Cell]] = None
    cost: Optional[float] = None
    elapsed: Optional[float] = None


def astar_search(grid, start: Cell, goal: Cell, log: bool = True) -> Iterator[SearchEvent]:
    """
    Generator-based A* search. Yields a SearchEvent each time a node is
    popped/expanded from the open set, and a final "done"/"failed" event.
    """
    start_time = time.perf_counter()
    counter = itertools.count()  # tie-breaker for heap stability

    open_heap: List[Tuple[float, int, Cell]] = []
    g_score: Dict[Cell, float] = {start: 0.0}
    came_from: Dict[Cell, Cell] = {}
    closed: set = set()

    h0 = manhattan(start, goal)
    heapq.heappush(open_heap, (h0, next(counter), start))

    nodes_expanded = 0

    if log:
        print(f"[A*] Starting search: start={start} goal={goal} h(start)={h0}")

    while open_heap:
        f, _, current = heapq.heappop(open_heap)

        if current in closed:
            continue
        closed.add(current)
        nodes_expanded += 1

        g = g_score[current]
        h = manhattan(current, goal)

        if log:
            print(
                f"[A*] expand #{nodes_expanded:03d} node={current} "
                f"g={g:.0f} h={h} f={g + h:.0f} frontier={len(open_heap)}"
            )

        yield SearchEvent(
            kind="expand",
            node=current,
            g=g,
            h=h,
            f=g + h,
            nodes_expanded=nodes_expanded,
            frontier_size=len(open_heap),
        )

        if current == goal:
            path = _reconstruct_path(came_from, start, current)
            elapsed = time.perf_counter() - start_time
            if log:
                print(
                    f"[A*] GOAL REACHED. path_cost={g_score[current]:.0f} "
                    f"nodes_expanded={nodes_expanded} time={elapsed*1000:.2f}ms"
                )
                print(f"[A*] path={path}")
            yield SearchEvent(
                kind="done",
                node=current,
                path=path,
                cost=g_score[current],
                nodes_expanded=nodes_expanded,
                elapsed=elapsed,
            )
            return

        for neighbor in grid.neighbors(current):
            tentative_g = g + 1  # uniform step cost
            if tentative_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current
                priority = tentative_g + manhattan(neighbor, goal)
                heapq.heappush(open_heap, (priority, next(counter), neighbor))

    elapsed = time.perf_counter() - start_time
    if log:
        print(f"[A*] FAILED: no path found. nodes_expanded={nodes_expanded} time={elapsed*1000:.2f}ms")
    yield SearchEvent(kind="failed", nodes_expanded=nodes_expanded, elapsed=elapsed)


def _reconstruct_path(came_from: Dict[Cell, Cell], start: Cell, goal: Cell) -> List[Cell]:
    path = [goal]
    while path[-1] != start:
        path.append(came_from[path[-1]])
    path.reverse()
    return path


def run_search_to_completion(grid, start: Cell, goal: Cell, log: bool = True) -> SearchEvent:
    """Convenience wrapper: drains the generator and returns the final event."""
    final_event = None
    for event in astar_search(grid, start, goal, log=log):
        final_event = event
    return final_event
