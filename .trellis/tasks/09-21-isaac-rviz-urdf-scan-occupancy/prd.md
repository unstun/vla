# RViz Lite3 URDF plus SCAN occupancy on livox stand

Stage: experiment + analysis. Parent: `09-16-emos-harnessvln-reimplementation`.
Sibling of `09-21-isaac-livox-mid360-stand-probe` (Livox CSV + GPU RViz
cloud; that child stays `in_progress` and does not start SCAN).

## Goal

Show the standing Lite3 as a URDF mesh in GPU RViz and show the unmapped
box as SCAN occupancy voxels (`/grid_map/occupancy`), from live Livox
`/quad_0/cloud`, while the robot stands. Not two-goal navigation, not
Pi, not a physical MID-360.

## User value

The last GPU RViz clip (`stand_20260921T100017Z_livox_rviz_gpu`) has
the live cloud and a spawn-truth AABB cube. Isaac already spawned the
v17 sensor-rig dog; RViz did not. Dr Sun (2026-09-21) asked for the
Lite3 model in the scene and for the box to be recognized as an
obstacle. He selected URDF + SCAN occupancy (not an invented clusterer).

## Confirmed facts

- Isaac already uses the pinned Isaac-safe v17 sensor-rig URDF
  (`803d5527…`). Meshes are packaged under
  `inputs/sensor_rig/` on livox stands.
- Foxy bridge already publishes `/quad_0/joint_states`,
  `/quad_0/body_pose`, `/quad_0/lidar_pose`, `/quad_0/cloud`,
  `/quad_0/cloud_raw`. Stand RViz now needs `--ipc=host` on the bridge
  (09-16 GPU probe and the second livox RViz run).
- Existing reuse for the dog mesh:
  `bridge/launch/native_rviz_review.launch.py` runs
  `robot_state_publisher` on the URDF with
  `joint_states` remapped to `/quad_0/joint_states`.
  `foxy_native_scan_review.rviz` already has
  `Lite3 URDF (measured joints)` on `/robot_description` and
  `Raw SCAN Occupancy` on `/grid_map/occupancy`.
- Existing reuse for occupancy: `scan_04` workspace
  `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_04`,
  `baseline_config/planner.yaml`, two-goal backend starts
  `ros2 run scan_planner scan_planner_node` with
  `cloud:=/quad_0/cloud`. Occupancy is a grid_map of that cloud, not
  the spawn AABB.
- 09-21 PRD D1 still forbids SCAN inside that child. This sibling
  starts SCAN for occupancy visualization only.

## Requirements

- GPU RViz records the live scene with: (1) Lite3 URDF mesh driven by
  measured joints, (2) live `/quad_0/cloud_raw`, (3) SCAN
  `/grid_map/occupancy` voxels.
- Livox `stand_probe`, `--unmapped-box lidar`, `--lidar-pattern-mode
  livox_mid360`, same pinned CSV/URDF as 09-21.
- SCAN input cloud is `/quad_0/cloud` (the two-goal remap). No PCT,
  no goal A/B, no Pi.
- Claim: occupancy visualization on a standing Livox snapshot. Not
  navigation success.

## Acceptance Criteria

- [ ] AC0. Local: observer hooks still unique; URDF meshes copied into
      the RViz package; `scan_04` identity recorded; tests refuse a
      new detector.
- [ ] AC1. GPU RViz video on gpu5070ti shows the Lite3 mesh (not only
      an odometry arrow) and `/grid_map/occupancy` Status Ok with
      nonempty voxels while the dog stands.
- [ ] AC2. Occupancy receipts or voxel counts are recorded. Box
      footprint has occupancy in front of the robot (report counts;
      do not invent a new box classifier). Frozen 09-20 AC1 is not
      amended.

## Out of scope

- Two-goal scoring, PCT route, Pi `navigate_to`.
- Invented Euclidean clustering or a new LiDAR.
- 09-20 frozen AC1 amendment, stairs, contact taxonomy.
- Physical MID-360 match.

## Open questions

- None. SCAN process set: `scan_planner_node` only (Dr Sun 2026-09-21).
