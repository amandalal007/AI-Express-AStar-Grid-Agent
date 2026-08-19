"""
main.py
-------
Entry point for the AI Express Hackathon submission.

Track 1: Warehouse Logistics Agent (Unit 2 - Informed Search)
    Scenario: an autonomous forklift picks up a package and delivers it to
    a designated loading bay in a grid warehouse with static shelf
    obstacles, using A* search with a Manhattan-distance heuristic.

Run:
    python main.py                  # fixed warehouse layout, pygame window
    python main.py --layout random --seed 7
    python main.py --no-replan      # disable the dynamic shelf-blockage demo
    python main.py --headless       # run the algorithm only, no window
                                     # (useful for CI / automated testing)

Controls (visual mode):
    When a run finishes (goal reached, or no route found), the window
    waits for you:
        R  -> run it again, from scratch, with a NEW randomly-chosen
              loading bay (same shelf layout) so it isn't an identical
              replay
        Q / Esc / close the window -> quit

What it demonstrates (maps to the marking rubric):
    - Live Agent Movement (video): the pygame window animates the
      forklift's real search (node expansion) and its final path traversal
      to the loading bay -- Track 1's core deliverable requirement.
    - Algorithmic Correctness: a full A* implementation with the admissible
      Manhattan heuristic specified by Track 1, plus a bonus live
      *replanning* pass triggered by a shelf/pallet toppling into the
      forklift's path (credited under "... or Dynamic Replanning" in the
      Algorithmic Correctness rubric row).
    - Performance metrics are printed to the console at the end (time
      taken, path cost, nodes expanded) -- exactly what Track 1 asks the
      agent to log -- for use in the video's final 15s and in the
      Technical Summary Sheet's complexity-analysis section.
"""

from __future__ import annotations
import argparse
import random
import sys
import time

from environment import Grid
from agent import astar_search, manhattan

# --- Animation pacing -------------------------------------------------- #
# Tuned to be easy to follow on a live screen recording. Lower FPS = slower.
SEARCH_FPS = 12       # how fast node-expansion ("thinking") frames play
TRAVERSAL_FPS = 2     # grid cells the forklift crosses per second (0.5s/cell)
BEAT_PAUSE = 1.2      # seconds to hold on key story beats (blockage appears, etc.)
END_SCREEN_FPS = 30   # just the redo/quit prompt polling rate


def build_grid(layout: str, seed: int | None) -> Grid:
    if layout == "random":
        return Grid.random_layout(seed=seed)
    return Grid.default_layout()


def randomize_goal(grid: Grid, rng: random.Random, min_distance: int = 6) -> None:
    """
    Move the loading bay to a new, reachable, randomly-chosen cell, so each
    redo delivers to a different spot instead of repeating the exact same
    run. Falls back gracefully if the warehouse is too small/cramped to
    satisfy `min_distance`.
    """
    reachable = grid.reachable_free_cells(grid.start) - {grid.start}
    if not reachable:
        return  # nothing else reachable; leave the goal where it is

    far_enough = [c for c in reachable if manhattan(grid.start, c) >= min_distance]
    candidates = far_enough or list(reachable)

    # Prefer not to repeat the exact same loading bay twice in a row.
    fresh = [c for c in candidates if c != grid.goal]
    pool = fresh or candidates

    grid.goal = rng.choice(pool)


def run_headless(grid: Grid) -> None:
    """Search-only run with no visualization; prints the same console log
    a human would see, and a final metrics summary. Useful for quick
    correctness checks / automated tests."""
    print(f"[WAREHOUSE] Forklift pickup point={grid.pickup_point}  loading bay={grid.loading_bay}")
    final = None
    for event in astar_search(grid, grid.start, grid.goal, log=True):
        final = event
    if final and final.kind == "done":
        print("\n=== PERFORMANCE METRICS ===")
        print(f"Path cost      : {final.cost:.0f}")
        print(f"Nodes expanded : {final.nodes_expanded}")
        print(f"Time taken     : {final.elapsed * 1000:.2f} ms")
    else:
        print("No path found.")


def run_episode(grid: Grid, viz, allow_replan: bool):
    """
    Runs one full plan -> traverse -> (optional) replan -> arrive episode on
    the given grid/visualizer. Returns a metrics dict on success, or None if
    no route could be found (initial or after a blockage).
    """
    overall_start = time.perf_counter()
    total_nodes_expanded = 0
    total_path_cost = 0.0
    replans = 0

    def animate_search(start, goal):
        """Runs the A* generator, drawing each expansion. Returns the final
        'done'/'failed' SearchEvent."""
        nonlocal total_nodes_expanded
        final_event = None
        for event in astar_search(grid, start, goal, log=True):
            viz.pump_events()
            if event.kind == "expand":
                viz.expanded_cells.add(event.node)
                viz.set_status([
                    f"PLANNING ROUTE (A*)  expanding node={event.node}",
                    f"g={event.g:.0f}  h={event.h:.0f}  f={event.f:.0f}  "
                    f"nodes_expanded={event.nodes_expanded}  frontier={event.frontier_size}",
                ])
                viz.draw()
                viz.tick(SEARCH_FPS)
            final_event = event
        # Accumulate across searches (initial plan + any replans) rather
        # than overwriting, so the final total reflects all A* work done.
        total_nodes_expanded += final_event.nodes_expanded
        return final_event

    # ---------------- Phase 1: initial search ----------------
    print(f"\n[WAREHOUSE] Forklift pickup point={grid.pickup_point}  loading bay={grid.loading_bay}")
    viz.set_status(["Forklift planning initial route to loading bay with A*..."])
    viz.draw()
    result = animate_search(grid.start, grid.goal)
    if result.kind != "done":
        viz.set_status(["No route found from pickup point to loading bay."])
        viz.draw()
        return None

    path = result.path
    total_path_cost = result.cost
    viz.path = path
    viz.expanded_cells.clear()

    # ---------------- Phase 2: traverse path (with optional replanning) ----
    agent_index = 0
    trigger_point = len(path) // 2 if allow_replan and len(path) > 4 else None

    viz.agent_pos = path[0]
    viz.set_status([
        f"Route found. cost={result.cost:.0f} nodes_expanded={result.nodes_expanded}",
        "Forklift en route to loading bay...",
    ])
    viz.draw()
    time.sleep(BEAT_PAUSE)

    while agent_index < len(path) - 1:
        viz.pump_events()

        # Trigger a dynamic shelf/pallet blockage roughly halfway through the run.
        if trigger_point is not None and agent_index == trigger_point:
            new_obstacle = grid.pick_dynamic_obstacle(path, agent_index)
            if new_obstacle:
                grid.add_obstacle(new_obstacle)
                replans += 1
                print(f"\n[WAREHOUSE] Shelf/pallet toppled into aisle at {new_obstacle}! Replanning...")
                viz.set_status([
                    f"!! Aisle blocked at {new_obstacle} -- forklift replanning with A* !!",
                ])
                viz.draw()
                time.sleep(BEAT_PAUSE)

                viz.expanded_cells.clear()
                current = path[agent_index]
                replan_result = animate_search(current, grid.goal)
                if replan_result.kind != "done":
                    viz.set_status(["Replanning failed: no route around the blockage."])
                    viz.draw()
                    return None

                # Splice the new sub-path onto our executed history.
                path = path[: agent_index] + replan_result.path
                total_path_cost = agent_index + replan_result.cost
                viz.path = path
                viz.expanded_cells.clear()
                trigger_point = None  # only replan once in this demo
                viz.set_status([
                    f"Replanned. new sub-cost={replan_result.cost:.0f} "
                    f"nodes_expanded={replan_result.nodes_expanded}",
                    "Resuming delivery...",
                ])
                viz.draw()
                time.sleep(BEAT_PAUSE)

        agent_index += 1
        viz.agent_pos = path[agent_index]
        viz.set_status([
            f"Delivering package... step {agent_index}/{len(path) - 1}",
            f"cumulative nodes_expanded={total_nodes_expanded}  replans={replans}",
        ])
        viz.draw()
        viz.tick(TRAVERSAL_FPS)

    elapsed = time.perf_counter() - overall_start
    print("\n=== PERFORMANCE METRICS ===")
    print(f"Path cost (executed) : {total_path_cost:.0f}")
    print(f"Nodes expanded (total): {total_nodes_expanded}")
    print(f"Replans triggered     : {replans}")
    print(f"Total time taken      : {elapsed:.2f} s")

    viz.set_status([
        "PACKAGE DELIVERED TO LOADING BAY.",
        f"cost={total_path_cost:.0f} nodes_expanded={total_nodes_expanded} time={elapsed:.2f}s",
    ])
    viz.draw()

    return {
        "path_cost": total_path_cost,
        "nodes_expanded": total_nodes_expanded,
        "replans": replans,
        "elapsed": elapsed,
    }


def wait_for_redo(viz, last_line: str) -> bool:
    """
    Shows a redo/quit prompt on the existing window and blocks until the
    user responds. Returns True to run again, False to quit.
    """
    import pygame  # deferred import: keeps --headless free of any SDL dependency

    viz.set_status([
        last_line,
        "Press R to run it again  |  Q / close window to quit",
    ])
    viz.draw()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return False
        viz.tick(END_SCREEN_FPS)


def run_visual(grid_factory, allow_replan: bool = True) -> None:
    # Local import so --headless mode never needs a display / SDL.
    from visualizer import GridVisualizer

    goal_rng = random.Random()  # unseeded on purpose: varies every redo

    grid = grid_factory()
    randomize_goal(grid, goal_rng)
    viz = GridVisualizer(grid)

    while True:
        summary = run_episode(grid, viz, allow_replan)
        if summary is None:
            last_line = "Run ended without reaching the loading bay."
        else:
            last_line = (
                f"DELIVERED -- cost={summary['path_cost']:.0f} "
                f"nodes_expanded={summary['nodes_expanded']} "
                f"replans={summary['replans']} time={summary['elapsed']:.2f}s"
            )

        again = wait_for_redo(viz, last_line)
        if not again:
            break

        # Fresh grid + a new loading bay + reset visualizer state, so this
        # redo isn't an identical replay of the previous one.
        grid = grid_factory()
        randomize_goal(grid, goal_rng)
        viz.grid = grid
        viz.expanded_cells = set()
        viz.path = []
        viz.agent_pos = grid.start

    viz.close()


def main():
    parser = argparse.ArgumentParser(
        description="Track 1: Warehouse Logistics Agent (A* Search) - AI Express Hackathon"
    )
    parser.add_argument("--layout", choices=["default", "random"], default="default",
                         help="warehouse floor plan: fixed shelf layout, or randomly generated")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-replan", action="store_true",
                         help="disable the dynamic shelf-blockage/replanning demo")
    parser.add_argument("--headless", action="store_true", help="run without opening a pygame window")
    args = parser.parse_args()

    if args.headless:
        run_headless(build_grid(args.layout, args.seed))
    else:
        grid_factory = lambda: build_grid(args.layout, args.seed)
        run_visual(grid_factory, allow_replan=not args.no_replan)


if __name__ == "__main__":
    sys.exit(main())