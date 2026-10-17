# Design: global step rule in SCAN occupancy query

## Behavior gap

Today `getInflateOccupancy` returns 1 whenever the inflated occupancy buffer
is set. Stair risers, treads, thin walls, and boxes are the same class.

Needed: if the **raw** column heights in a 0.30 m window around the query
show a climbable step, that inflated hit is treated as free. Otherwise the
buffer value is unchanged.

## Where it lives

| Piece | Path | Why |
|---|---|---|
| Contract + tests | `p2b_execution/step_traversability.py` | ROS-free, local unittest |
| C++ translation | `p2b_execution/step_traversability.h` | Header-only, no ROS/Eigen |
| Patcher | `p2b_execution/apply_scan_step_traversability.py` | Same pattern as the terminal-accel fix; hash-gated |
| Call site | `GridMap::getInflateOccupancy` | The only occupancy API used by A*, optimizer, FSM |

Not: ETH nodes, PCT labels, `planner.yaml`, `scan_04`.

## Algorithm

Height map H(ix, iy) = max occupied z in that xy column (unknown skipped).

Samples: cells whose center is inside `window_radius_m` of the query.

1. Fewer than 2 samples → not a step.
2. `delta = h_max - h_min`.
3. `delta < min_step_height_m` (0.04) → not a step (flat / inflation on
   flat ground stays occupied).
4. `delta >= critical_height_m` (0.26) → not a step (box, wall, cliff).
5. High cells: `|z - h_max| <= height_band_m` (0.05).
6. `min_side` of the high-cell index AABB, in metres, must be
   `>= min_tread_depth_m` (0.15). Thin ridge fails; a 0.30 m tread in a
   0.30 m window still has min_side ≥ 0.15 at the nosing.

Defaults are compiled in. `planner.yaml` is not required to list them.

## Hook

```
occ = inflate_buffer(query)
if occ == 1 and occupancyHitIsTraversableStep(raw_heights, query):
    return 0
return occ
```

Out of map remains -1.

## Compatibility

- `scan_04` is the accepted baseline and is not modified. The patcher
  copies listed files into a working tree (tests use tempfile).
- Frozen occupancy keys keep their load lines and values.
- ETH is a comment citation, not a dependency.

## Claim boundary

Passing AC0–AC1 is a local classifier + patcher result. It is not
`integrated` SCAN and not a stair or box Isaac result.
