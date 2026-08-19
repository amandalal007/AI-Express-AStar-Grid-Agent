# Warehouse Logistics Agent — AI Express Hackathon

**Track:** Track 1 — Warehouse Logistics Agent (Unit 2, Informed Search)
**Scope:** Units 1–4 (AI Foundations, Problem-Solving Agents, Logical Agents, First-Order Logic)

**Scenario:** an autonomous forklift must pick up a package and deliver it to a
designated loading bay in a grid warehouse with static shelf obstacles.

An autonomous agent (the forklift) plans and navigates a 2D grid warehouse using
**A\* search** with the Manhattan-distance heuristic specified by the track brief
(`h(n) = |x1-x2| + |y1-y2|`), renders its movement live in **Pygame**, logs every
decision (node expansion) to the console in real time, and — as a bonus that
also covers the "Dynamic Replanning" credit path in the Algorithmic Correctness
rubric row — **replans on the fly** when a shelf/pallet topples into its route.

> Why Track 1: of the four tracks (Warehouse/A*, Mars Rover/Propositional
> Logic, Legal Drone/FOL, Ambulance/Dynamic Replanning), this one has the
> clearest, lowest-risk deliverable for a 90-minute window — a single
> well-defined algorithm (A*) with an exact heuristic given in the brief —
> and this codebase already implements it end-to-end, tested. It also
> incorporates the Track 4 dynamic-replanning idea as a bonus, without
> the added complexity of a full logic/inference engine (Tracks 2 & 3).

## 1. What this agent does

1. Loads a warehouse floor plan (fixed shelf layout by default, or a randomly generated one).
2. Runs A* from the pickup point to the loading bay, visually lighting up each
   node as it's expanded, while printing `g`, `h`, `f`, and nodes-expanded
   to the console.
3. Animates the forklift moving step-by-step along the optimal path found.
4. Partway through the run, a **shelf/pallet topples into an aisle** on the
   forklift's planned route (simulating a dynamic/partially observable
   warehouse). The agent detects this, **re-runs A\*** from its current
   position to the loading bay avoiding the new blockage, and resumes
   delivery — all shown live.
5. Prints final performance metrics: path cost, total nodes expanded,
   number of replans, and total time taken — exactly what Track 1's
   deliverable requirement asks the agent to log.

## 2. PEAS framework

| | |
|---|---|
| **Performance measure** | Deliver the package to the loading bay with minimum path cost; minimise nodes expanded and replanning time |
| **Environment** | 2D discrete grid warehouse floor, static shelf obstacles known upfront + one dynamic blockage (toppled shelf/pallet) introduced mid-run |
| **Actuators** | Move Up / Down / Left / Right by one cell |
| **Sensors** | Full visibility of static shelf obstacles; the new blockage is only "sensed" once it appears on the forklift's route |

## 3. Core algorithmic formulation

- **State space:** every free grid cell `(x, y)`
- **Initial state:** the agent's current cell
- **Goal test:** `state == goal`
- **Path cost:** `g(n)` = number of moves so far (uniform step cost = 1)
- **Heuristic:** `h(n) = |x - goal_x| + |y - goal_y|` (Manhattan distance — admissible & consistent for 4-connected grids, so A* returns the optimal path)
- **Evaluation function:** `f(n) = g(n) + h(n)`

## 4. Complexity

- **Time:** O(b^d) worst case; with a binary-heap priority queue, effectively O(V log V) over V = width × height reachable cells
- **Space:** O(V) for open/closed sets
- Observed values (nodes expanded, path cost, elapsed time) are printed to
  the console at the end of each run — copy these into the Technical
  Summary Sheet's complexity-analysis section.

## 5. Setup & run instructions

```bash
# 1. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run with the visual pygame window (fixed layout, replanning demo on)
python main.py

# Other useful runs:
python main.py --layout random --seed 7   # randomly generated maze
python main.py --no-replan                # skip the dynamic obstacle demo
python main.py --headless                 # console-only, no window (quick correctness check)
```

Close the pygame window (or press the window's close button) to exit early;
otherwise it auto-closes ~4 seconds after the goal is reached.

## 6. Recording the demo video (60–90s)

Suggested flow matching the video guidelines:


## 7. Project structure

```
astar_grid_agent/
├── environment.py   # Grid world: obstacles, neighbors, dynamic obstacle injection
├── agent.py         # A* search (generator-based, for live visualization + logging)
├── visualizer.py     # Pygame rendering of grid, search, path, agent, HUD
├── main.py           # Orchestrates search -> traversal -> replanning -> metrics
├── requirements.txt
└── README.md
```

## 8. Team

- Member 1: Akash Ganesh 2441604
- Member 2: Aleena Elsa Benoy 2441605
- Member 3: Aman 2441606
- Group ID: Team 02
- Course Code: BCA301-5

