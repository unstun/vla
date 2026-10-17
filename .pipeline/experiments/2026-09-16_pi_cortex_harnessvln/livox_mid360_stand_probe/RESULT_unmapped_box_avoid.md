# Unmapped box avoidance walk

Label: one Isaac episode. Not a navigation validation claim.

| Item | Value |
| --- | --- |
| Run | `avoid_20260921T1635Z` |
| Local package | `/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/unmapped_box_avoid_runs/avoid_20260921T1635Z` |
| Status | pass |
| PCT route crosses box xy | True |
| URDF torso intersects box | False |
| Final xy within 0.25 m of goal-b | True |
| Final xy error m | 0.1294447737355482 |
| Source planner.yaml SHA-256 | `42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e` |
| Body samples | 450 |
| Expanded-torso overlaps | 65 |
| URDF torso overlaps, pad 0 | 0 |
| Body origin inside box xy | 0 |
| Closest body origin to box xy | 0.355 m, at `(1.191, -4.952)`, south of the box |

Dr Sun (2026-09-21) judged this episode a success from the video and the body track. Pass means the PCT route crosses the box footprint, the URDF torso never intersects the box, and the dog stops within 0.25 m of goal-b.

An earlier note called the episode a failure because `robot_aabb_world` adds 0.25 m around the torso, and that padded box overlapped on 65 of 450 samples. That pad is the spawn-clearance margin. It is not the collision test for this walk. The body origin stayed 0.355 m outside the box and passed on the south side. SCAN moved `WAIT_TARGET` → `EXEC_TRAJ`, replanned, then stopped after the goal. `planner.yaml` was not retuned. One episode is not a navigation validation claim.
