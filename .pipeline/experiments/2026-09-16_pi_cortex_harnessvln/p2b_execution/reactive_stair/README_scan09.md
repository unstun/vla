# scan_09: current-track and ETH-style stair candidate

Status: **hash-gated Foxy build and synthetic ROS transport passed; no Isaac
pedestrian avoidance episode**.

`scan_09` copies the successfully built `scan_08` source and changes one ROS
terrain intake predicate. The pinned Humble PCT publisher emits finite
`PointCloud2` records with `is_dense=false`; `scan_08` rejected them before
decoding. The new predicate accepts the cloud when the world frame, float32
fields, and finite records pass validation. The accepted `scan_04`, frozen
`baseline_config/planner.yaml`, previous candidates, and sibling repos remain
unchanged. The overlay and exact hashes are recorded in
`builds/scan_09/pct_density_candidate_manifest.json`.

The planner retains `scan_07`'s precomputed ETH-style two-pass step score and
shared collision query. The separate `scan_reactive_tracker` package consumes
paired current LiDAR/pose observations and PCT selected ground, then publishes
complete current moving-cluster snapshots. It uses last observed centers for
ID association, with no velocity extrapolation or pedestrian trajectory
prediction. SCAN's existing safety check handles current occupancy changes.
The tracker is a shape/motion candidate, not validated human recognition.

The existing P2B pilot does not launch `/pct_tomogram`. Use the separate
`pct_sim_clock_publisher.py` candidate described in
`README_pct_sim_clock_sidecar.md` for a nonzero simulation-time terrain stamp.
It must be the sole publisher on that topic for a trial. No existing pilot
runner has yet been changed to launch the sidecar or tracker.

Evidence:

- Local materializer regression, tracker core/PointCloud2 tests, exact PCT
  point parity, and simulation-clock callback tests passed.
- `builds/scan_09/build_result.json`: seven Foxy packages built with source
  identity equal before and after. `install_identity.json` records the
  installed-file hashes.
- The CPU-only Humble sidecar ROS probe received 86,775 `world` terrain points
  at a nonzero synthetic simulation stamp with the pinned payload SHA-256.
- A CPU-only cross-container Humble/Foxy probe received the same terrain
  topic and published five complete tracker snapshots for a synthetic moving
  LiDAR cluster. The ID stayed `cluster-1`; each center matched the current
  observed position. Raw logs, exact commands, and source hashes are under
  `.pipeline/experiments/2026-09-23_scan_reactive_stair/`.

These probes did not run SCAN's collision query, produce a person-labelled
sensor result, measure the 50 ms loop, or move a robot in Isaac. A confirmed
track lost from view remains incomplete indefinitely until reacquired;
this avoids silently clearing an unseen person but can halt navigation. The
XY-only person footprint can also conservatively block another floor.
