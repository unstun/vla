# PCT global route, SCAN local avoid the unmapped box

Stage: planning. Parent: `09-16-emos-harnessvln-reimplementation`.
Dr Sun (2026-09-21) approved a walk: PCT plans globally, SCAN plans
locally, and the dog must go around `/World/unmapped_box`.

## Goal

One Isaac episode on gpu5070ti. The dog starts at the Building stand pose,
Livox Mid-360 sees the unmapped box, PCT plans to the existing goal behind
that box, and SCAN’s local trajectory plus V12 motion go around it.

## Confirmed facts

- Stand `stand_20260921T151214Z_livox_rviz_gpu` ran `scan_planner_node` only.
  The goal equalled the spawn. The dog did not walk.
- The box face is already in the SCAN grid. Hits near `x ≈ 0.687` publish at
  voxel center `x = 0.675` (`indexToPos` in `scan_04` `grid_map.h`). SCAN
  collision uses `getInflateOccupancy` (`scan_replan_fsm.cpp`
  `checkCollisionCallback`).
- P2B mode ignores legacy `/pct_path`. The global route enters on
  `/p2b/route`. Motion is `/planning/bspline` → `closed_loop_controller` →
  `/quad_0/cmd_vel` → V12. That chain is the two-goal pilot in
  `isaac_runner/run_two_goal_pilot.py`.
- `p2b_execution/inputs/pilot.json` spawn
  `(-1.6088105720747303, -4.542777504301488, 1.5608844757080078)`, yaw
  `0.057418473165896385`. The box is 2.5 m along that yaw
  (`unmapped_box.py`, 0.4 × 0.4 × 0.8 m). `goal-b` is
  `(2.3894024585958937, -4.45715232978101, 1.5608844757080078)`, about 1.5 m
  past the box center on the same corridor. `goal-a` at `x = 0.389` is still
  in front of the near face.
- The patched runner already accepts `--unmapped-box lidar` and
  `--lidar-pattern-mode livox_mid360`. The two-goal launcher does not pass
  them, and its driver also cancels and visits `goal-a`.
- Pinned `planner.yaml` SHA
  `42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e`.
  The two-goal package adds `p2b_mode: true` in the run copy only.

## Requirements

- R1. Reuse the two-goal PCT worker, `POST /goal`, `scan_planner_node`, and
  `closed_loop_controller`. Do not edit the two-goal cancel driver or
  `pilot.json`.
- R2. One goal: `goal-b` from `pilot.json`. Spawn and box pose stay the
  D3 stand. Sensor is Livox Mid-360. Box mode is `lidar`.
- R3. SCAN workspace is the accepted `scan_04` build. Source `planner.yaml`
  is not edited. A run copy may add `p2b_mode: true` and nothing else.
- R4. Record whether the PCT route’s xy crosses the frozen box footprint,
  whether any body sample’s expanded torso AABB intersects the box AABB
  (`robot_aabb_world` in `unmapped_box.py`), and the final xy error to
  `goal-b`.

## Acceptance Criteria

- [x] AC0. Local tests show one `POST /goal` to `goal-b`, no `/cancel`, runner
      argv contains `--unmapped-box lidar` and
      `--lidar-pattern-mode livox_mid360`, and the source `planner.yaml`
      hash is unchanged. `python3 -m unittest isaac_runner/test_run_unmapped_box_avoid.py` 6/6.
- [x] AC1. One gpu5070ti episode, sim cap 45 s, wall cap 1200 s. RESULT names
      the run and states pass or fail. Run `avoid_20260921T1635Z`, status pass.
- [x] AC2. Pass: the PCT route xy crosses the box footprint; the URDF torso
      (no 0.25 m pad) does not intersect the box; final body xy is within
      0.25 m of `goal-b`. Dr Sun rejected the padded-torso rule after watching
      `third_person_master.mp4`. The 0.25 m pad still overlaps on 65/450
      samples and is recorded, not used as the verdict.

## Out of scope

- Retuning `ground_height`, `vis_height`, or `cloud_is_world`.
- The two-goal cancel / `goal-a` protocol.
- Pi, a new detector, editing `machine-dog-nav`, or a real robot.
- Amending 09-20 AC1. One episode is not a navigation validation claim.

## Decisions

- Walk, not a path-only picture. Approved by Dr Sun on 2026-09-21.
- Goal is the existing `goal-b`, not a new coordinate.
- Same Livox rig and `lidar` box as the stand that saw the face voxels.
