# v29: known-footprint waiver at the queried point, up to the LiDAR origin

Stage: experiment + analysis. Parent: v28. One change to the grid query's
known-footprint waiver, in two expressions. Dr Sun chose "Test the queried
point, not the voxel centre" on 2026-09-28. After the required optimizer trace
showed that the point test alone is a regression, he chose "Point + LiDAR
column".

## Motivation

`v28_historical_full01` stopped for good at 12.691 s. Every later replan from
the lowered walking pose failed. `audits/2026-09-28_v28_start_thrash/RESULT.md`
traces this from saved inputs:

- The walking body is about 4.7 cm lower than the stand.
- The known-footprint waiver tests the trunk band at the voxel centre. For
  that reason the never-observed cells beside the trunk stay UnknownObstacle.
- Testing the queried point alone fixes the seed search but fails 4 of 6 saved
  walking heights, 3 of which v28 plans.
- The remaining blocks are never-observed cells inside the footprint between
  the trunk band (+0.07 m) and the Mid-360 scan origin (+0.10854 m in `TORSO`,
  pinned Isaac URDF `803d5527...`). The sensor is pitched 15 degrees
  nose-down, so it cannot observe that slice beside and behind itself.
- A diagnostic point + column build (top 0.1085 m) planned all seven saved
  states, with full gates and negative controls.

## Exact change

`materialize.py` copies `runtime/scan60_constraint_guard_v28` to
`runtime/scan61_sensor_column_v29` and changes only these two expressions:

1. `plan_env/scan_reactive_grid_methods.inc`: rotate the queried point, not
   its voxel centre, into the body frame. The now-unused centre lookup is
   removed.
2. `plan_env/known_lite3_trunk.h`, `knownNavigationFootprintInterior`: change
   the vertical test from `|z - 0.01| <= 0.06` to `-0.05 <= z <= 0.10854`.
   The function has one call site, and the torso-box function is untouched.

Every other v28 byte is unchanged. The planner YAML files are copied
unchanged.

## Preserved

- The two-circle footprint (radius and offset parameters) and the 0.1 s pose
  freshness.
- The Unknown-only rule: observed Occupied voxels and Unknown voxels under an
  inflated hit still block.
- Terrain support, body height, map boundary and stale-input verdicts; the
  optimizer, A*, seed shortcut and all manager gates; the controller, executor
  and emergency hold.

## Acceptance plan and expected signals

1. **Build** in the pinned image with the scan60 incremental cache. Source
   identity is checked before and after.
2. **Red/green waiver contract** (`waiver_contract/`). One contract source is
   compiled against v28 (red) and v29 (green). It replays the frozen stopped
   and control states. At 27 points inside each voxel near the body, two
   independent oracles give the expected result, one for each specification,
   and the contract compares them with the tree's `reactiveOccupancy`:
   - v28 must match the v28 oracle and differ from the v29 oracle.
   - v29 must match the v29 oracle and differ from the v28 oracle.
   - With the pose made 0.15 s stale, no Unknown point may be waived.
   - Results at non-Unknown voxels must be identical between the two trees.
3. **Saved start states.** The seven frozen states (0.3517-0.3987 m) use the
   unchanged regression `gen_probe`. All are expected to continue, with
   boundary PVA, the full-curve gate and the negatives, as the diagnostic
   counterfactual did.
4. **The complete v28 native regression suite on v29:**
   - all 11 continuation replays accepted with full gates and negatives;
   - repeats identical;
   - the 8 unmapped and 5 mapped fixture outputs compared with v28.

   Every difference is explained before freezing, not waived.
5. **Independent review:** a read-only review of the change, the contract and
   the evidence.
6. **Freeze, then one physical trial:** the historical full route with
   `v28_historical_full01`'s profile.

The v28 UBSAN seed replay targeted an optimizer crash that v29 does not touch.
It is not repeated.

## Claim boundary and residual risk

v29 changes what SCAN treats as free. A never-observed cell inside the robot's
current footprint, between 5 cm below the body reference and the LiDAR origin,
now counts as free, but only while the pose is fresh. The residual risk is an
obstacle in that slice that was never observed and does not touch the trunk.
One example is a low overhang above the rear of the body when the robot starts
underneath it. Another is a railing or shelf edge beside the trunk, about
0.30-0.46 m above the floor and inside the 0.35 m footprint circles.

Unknown cells are not inflated. A planned circle centre that stays inside the
current footprint can therefore be placed on such an unobserved object. The
trunk band below +0.07 m already carried this risk in v28; v29 extends it
3.85 cm upward. A few waived cells are inside the sensor's field and merely
not yet observed (`COMPONENT_RESULTS.md`). The waiver still does not clear
space around, ahead of or behind the footprint.

This paragraph was widened after the independent review and before freezing.
The acceptance steps above are unchanged.

v29 does not address:
- the wall-clock freshness chain (`odom_stale`) that ended the v28 run;
- the emergency-hold position feedback;
- the pending 13 cm protrusion choice.

Only a physical run can support a navigation claim. v3 remains the last
accepted condition until one passes.
