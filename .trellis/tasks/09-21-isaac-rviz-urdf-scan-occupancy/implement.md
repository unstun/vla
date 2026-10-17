# Implement: RViz Lite3 URDF plus SCAN occupancy

Paths relative to `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/`
unless absolute.

## A. Local

- [x] A1 Extend `livox_mid360_stand_probe/run_rviz_probe.py` (or a thin
      sibling wrapper) to: copy sensor-rig URDF+meshes for RViz; patch
      observer session to keep NVIDIA RViz; add a Foxy helper command
      that runs `native_rviz_review.launch.py` (or the two nodes it
      starts) plus `scan_planner_node` only. Bridge stays `--ipc=host`.
- [x] A2 RViz config: RobotModel `/robot_description`, live
      `/quad_0/cloud_raw`, `/grid_map/occupancy` from
      `foxy_native_scan_review.rviz`. No planned-path displays as the
      story. Unique run-specific `.rviz` filename unchanged.
- [x] A3 Tests: helper anchors unique; package includes URDF meshes;
      SCAN argv is `scan_planner_node` + `cloud:=/quad_0/cloud` and
      does not start `closed_loop_controller`; no new clusterer.

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/livox_mid360_stand_probe/test_run_rviz_probe.py
```

## C. gpu5070ti

- [x] C1 Host idle. 20 s livox `stand_probe`, `--unmapped-box lidar`,
      `--stance-hold auto`, GPU RViz + SCAN occupancy + URDF.
- [x] C2 `--execute`, collect `rviz_live_wall_time.mp4`, occupancy
      receipts or planner log, hashes. Copy review video.
- [x] C3 RESULT.md: mesh visible; occupancy Status Ok; box voxels in
      front of the dog; claim occupancy visualization not navigation.
      Do not amend 09-20 AC1.

Rollback: GPU RViz cloud-only path from 09-21 (`run_rviz_probe.py`
without SCAN/URDF helpers).
