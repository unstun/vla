# Implement: occupancy AABB miss diagnosis

Paths relative to `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/`
unless absolute.

## A. Local

- [x] A1 Extend `livox_mid360_stand_probe/rviz_observer/occupancy_audit.py`:
      xyz min/max/median; `aabb_xy_hits`; `aabb_z_hits`. Reuse
      `aabb_hit_marker`.
- [x] A2 Tests in `test_run_rviz_probe.py`: fixture extents; xy vs z
      split; helper still planner-only.

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/livox_mid360_stand_probe/test_run_rviz_probe.py
```

## C. gpu5070ti

- [x] C1 Host idle. Livox stand, `--unmapped-box lidar`, SCAN
      planner-only, unchanged `planner.yaml`.
- [x] C2 `--execute`, collect occupancy receipts with extents.
- [x] C3 RESULT: miss class + numbers. No SCAN retune. No 09-20 AC1
      amendment.

Rollback: occupancy_audit without extent fields.
