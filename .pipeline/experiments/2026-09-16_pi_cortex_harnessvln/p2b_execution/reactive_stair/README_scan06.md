# scan_06 reactive stair and current-person source candidate

Status: **local source candidate, Foxy-built but without live inputs**. `scan_06` is a
hash-gated copy of the built `scan_04` source with an adapter overlay. It is
separate from the inactive `scan_05` experiment. The accepted `scan_04`, frozen
`planner.yaml`, and existing step prototype are unchanged.

## Input contract

`GridMap` subscribes to `/pct_tomogram` as a reliable transient-local
`sensor_msgs/PointCloud2`. The existing PCT publisher emits selected ground
cells with float32 `x/y/z/intensity`, where `z` includes a default **+0.03 m
visual offset**. The adapter requires the configured world frame, subtracts
that offset, retains multiple elevations per XY cell, and uses an explicit
0.10 m PCT resolution. The published selected cells are positive support;
missing cells remain unknown. The adapter records a content fingerprint and
source timestamp, then treats the tomogram as one static map version with a
bounded default validity of 86400 s. This is a candidate source contract, not
proof that the PCT support mask covers every test stair tread.

`GridMap` subscribes to `/tracked_person_snapshot` with the new
`scan_planner_msgs/TrackedPersonSnapshot` type. Each complete snapshot contains
its source ID, frame, timestamp, and the entire current person set. Each
`TrackedPerson` has identity, own observation time, current 3D center, and
radius. A valid fresh empty snapshot explicitly clears prior tracks. No
velocity or trajectory field exists. Missing, invalid, or stale snapshots
block every collision query. The source is **external**; no sensor-derived
tracker is bundled. A future synthetic test publisher must be labelled
synthetic or simulator-oracle in its `source_id` and result.

The existing LiDAR raycasting path remains intact, so terrain points still
provide free-space clearing rays. On each accepted cloud, endpoint voxels are
positively classified as terrain only when they lie within 0.05 m of a
selected PCT ground elevation. Every other endpoint is nonterrain. A
nonterrain return at the same voxel takes precedence, and historical
nonterrain evidence persists until the raw occupancy update clears it. Old
occupied voxels without a currently classified terrain endpoint remain
obstacles. Empty, wrong-frame, future, or stale LiDAR input blocks planning.

The one shared `GridMap::getInflateOccupancy` path calls the conservative
decision for both SCAN body centers. A*, spline optimization, and the 50 ms
trajectory safety check already call this method. At each query, current
person footprints are checked first. For an inflated raw hit, every occupied
source voxel contributing to SCAN's existing inflation must have a positive
current terrain classification; one unclassified source keeps it occupied.
Unknown and out-of-map results block. The body height is checked against the
selected ground elevation. This is reactive occupancy only; it contains no
pedestrian trajectory prediction or time-indexed search.

The ROS callback remains unverified. The Foxy build passed with source identity
checks in `builds/scan_06/build_result.json`. The one-shot PCT map and
live LiDAR/tracks use different age limits. Their clocks and actual publish
rates need measurement before an Isaac run. An absent track publisher makes
the planner stop, as intended. The source adapter's endpoint classification
may conservatively block tread cells that lack a fresh terrain LiDAR return.

## Upstream attribution

ETH `StepFilter` is **surveyed only** at commit
[`14d24c059e1c43466aadf328280adf6394d78039`](https://github.com/leggedrobotics/traversability_estimation/blob/14d24c059e1c43466aadf328280adf6394d78039/traversability_estimation_filters/src/StepFilter.cpp).
The repository's recorded license is BSD-style (see the local survey). No ETH
source or two-pass score is imported into this candidate. The PCT selected
ground cells supply support here; any later ETH-style scoring needs a separate
height-map contract and local V12 thresholds before it can be called an
adaptation.

## Local checks and remaining gate

`materialize_scan_06.py` verifies the 67-file `scan_04` built-source hash
manifest and the terminal-acceleration provenance chain before creating a new
`builds/scan_06`. Its manifest lists every changed or added path and its
SHA-256. Run from `p2b_execution`:

```sh
python3 reactive_stair/test_materialize_scan_06.py -v
g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -I builds/scan_06/src/plan_env/include \
  reactive_stair/test_scan06_contract.cpp -o /private/tmp/test_scan06_contract
/private/tmp/test_scan06_contract
```

The local C++ test exercises the ROS-free decision and endpoint classifier,
including full tread interiors, multiple elevations, box/wall return rejection,
current person updates, stale and complete-empty snapshots, and precedence.
The Python test checks materialization, hash refusal, and shared hook
structure. **Neither test compiles the ROS adapter or proves simulator
integration.** The remaining gate is a bounded episode with a labelled
current-track source and separately scored outcomes. Later `scan_07` adds the
ETH-style two-pass score; `scan_09` includes the tracker and PCT density fix.
