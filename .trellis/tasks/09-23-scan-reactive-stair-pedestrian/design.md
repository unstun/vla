# Design: separate support and observed people

## Behavior gap

The current local patch changes an inflated SCAN hit to free when nearby raw
occupied-column heights resemble a step. That has no source distinction, can
clear a pedestrian hit, and leaves wide tread interiors occupied. It has not
been compiled or run. SCAN currently replans from live occupancy and checks
the executing spline every 50 ms.

## Seam and contract

Use a local terrain-support layer and a separate current-person layer. Terrain
is assessed from an elevation/support input, not inferred from the raw
obstacle voxels during every collision query. The pinned PCT wrapper retains
`elev_g` and its node publishes selected ground cells with traversability cost
on `/pct_tomogram` (`pct_runtime/python/pct_planner/planner_node.py`). This is a
candidate terrain input, not yet a verified SCAN stair-support feed. No
current-person track publisher has been identified in this execution path.
The collision decision checks
person occupancy first, then nonterrain static obstacles, then support. A
terrain allowance never overrides a current person or an unknown/out-of-map
result. Current tracks include `id`, frame, observation timestamp, center,
and footprint radius/extent. Track staleness blocks a previously occupied
corridor until a fresh clearing observation or a safe stop; no extrapolation.

The first planner behavior is reactive stop/yield and replan against the
current map. A time-indexed search and predicted pedestrian path are excluded.
The existing SCAN A*, spline optimizer, and 50 ms safety check must agree on
the same obstacle result. Stairside passing requires a measured supported
full-body corridor; if absent, stop/yield. Isaac flat stance hold is not
evidence that holding on stairs is safe.

## Source and rollout

`scan_04` is the immutable accepted baseline. Produce a new named copy with a
hash-gated overlay. Read-only `git ls-remote` on 2026-09-23 pinned ETH
`leggedrobotics/traversability_estimation` HEAD at
`14d24c059e1c43466aadf328280adf6394d78039`; its `StepFilter.cpp` is a
reference, not imported source. An adaptation must be named as such. Build and simulator outputs return under
this local task/experiment path. Remote directories are execution copies.

For `scan_04` source identity, use the successful build's `source_sha256.json`.
Its `planner_manager.cpp` hash `6eec7d6f...` intentionally differs from
`overlay_manifest.json`'s pre-terminal-fix `0c51df63...`;
`terminal_accel_fix_manifest.json` records the exact before/after chain.
The candidate materializer must check this chain rather than weaken the gate.

## Claim boundary

Local tests prove only the pure decision and patcher contract. A Foxy build
proves compilation. Isaac proves at most bounded simulation integration for
the actual input source and scene. No real-robot claim follows.
