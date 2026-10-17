# SCAN global step traversability in collision query

Stage: planning then experiment (local tests only). Parent:
`09-16-emos-harnessvln-reimplementation`.

Dr Sun (2026-09-22) rejected stair-segment labels as the obstacle rule
(no generalization). He authorized a **global** ETH-style step rule inside
SCAN’s collision query: the planner asks whether a height jump is within
V12’s step capability and has a support patch, not whether PCT labelled a
staircase.

## Goal

Local, testable collision rule: occupied cells that look like a climbable
step are free; tall boxes and thin walls stay occupied. Do not import ETH’s
ROS 1 node. Do not retune frozen occupancy keys. Do not edit `scan_04`.

## Confirmed facts

- SCAN A*, B-spline, and the 50 ms safety check all call
  `GridMap::getInflateOccupancy` (`scan_04` `grid_map.h`,
  `scan_replan_fsm.cpp`).
- Occupancy is binary log-odds. There is no stair class.
- ETH `StepFilter` (BSD, `leggedrobotics/traversability_estimation`) scores
  a height jump against `critical_value`. Defaults (0.12 m windows 0.04 m)
  are ANYmal elevation-map numbers, not ours. Status: `surveyed` only.
- V12 terrain cfg uses step height 0.05–0.257 m. Building stairs: ~0.136 m
  risers, ~0.74 m treads. Unmapped box: 0.4 × 0.4 × 0.8 m.
- Pinned source `planner.yaml` SHA-256
  `42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e`.
  Frozen keys: `ground_height`, `vis_height`, `cloud_is_world`.
- Accepted SCAN build is `scan_04`. A later Foxy rebuild / Isaac walk needs
  a new authorization.

## Requirements

- R1. Global rule (no PCT stair labels). Thresholds are V12 capability, not
  a stair name.
- R2. Height jump ≥ 0.26 m stays occupied (0.8 m box). Jump in
  [0.04, 0.26) m is a step only if the high patch’s smaller plan extent is
  at least 0.15 m (Building 0.74 m and standard ~0.30 m treads pass; 0.05 m
  walls fail).
- R3. Flat local height is not a step: keep occupancy (do not clear
  inflation on flat ground).
- R4. Algorithm lives in this repository as a ROS-free module plus a SCAN
  patcher. ETH is not cloned. `scan_04` bytes stay unchanged. New parameters
  use C++ defaults so source `planner.yaml` is not edited.
- R5. This task is local tests. No Foxy image build, no gpu5070ti, no Isaac,
  no real robot.

## Acceptance Criteria

- [x] AC0. `python3 -m unittest p2b_execution/test_step_traversability.py`
      passes the four geometry cases: 0.8 m box occupied; Building stair
      free; standard stair (0.16 m / 0.30 m) free; 0.15 m × 0.05 m wall
      occupied. Also: flat window is not a step.
- [x] AC1. `python3 -m unittest p2b_execution/test_apply_scan_step_traversability.py`
      shows the patcher refuses a wrong `grid_map.h` hash, inserts the
      header and `getInflateOccupancy` call, does not rewrite
      `ground_height` / `vis_height` / `cloud_is_world`, and leaves
      `scan_04` and pinned `planner.yaml` hashes unchanged.
- [x] AC2. RESULT records `surveyed` ETH, `not imported`, and that SCAN
      Foxy/Isaac is **not** `integrated` or `validated`.

## Out of scope

- Importing `leggedrobotics/traversability_estimation` or
  `elevation_mapping`.
- Editing `scan_04`, frozen occupancy keys, or sibling repos.
- Soft B-spline cost, heading lock, speed cap, Pi, real robot.
- Foxy `build_scan.py` and Isaac episodes.

## Decisions

- D1 (Dr Sun, 2026-09-22). Global collision rule, not route-labelled stair
  mode.
- D2. Capability ceiling 0.26 m; min tread depth 0.15 m; window 0.30 m.
- D3. Local tests only until a later run budget is approved.
