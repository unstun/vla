# Implement: Isaac LiDAR hits on one unmapped box

Paths are relative to `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/`
unless absolute.

Pattern sources (do not invent replacements):

- Isaac Lab v2.3.2 `37ddf626`: sibling extra prim + string
  `mesh_prim_paths` entry.
- Fallback `run_isaac_v12_fallback.py` @ `848b4aec` SHA-256 `6104fe68…`:
  Cuboid spawn L1938–1948, string append L2130–2131, AABB pad L4723–4734.

## A. Local code (no remote calls)

- [x] A1 `isaac_runner/unmapped_box.py`: box pose from stand spawn + 2.5 m
      yaw, world AABB with 0.01 m pad, robot-overlap check, sensor-frame →
      world, AABB counts. No Isaac/ROS import. Tests cover D3 numbers,
      overlap fail-closed, and a known pose/point.
- [x] A2 `isaac_runner/materialize_runner_patch.py`: new `unmapped_box`
      anchors for CLI `--unmapped-box {off,spawn,lidar}` (default `off`),
      `AssetBaseCfg` Cuboid at `/World/unmapped_box`, extra **string**
      target only in `lidar`, overlap check, and identity fields. Frozen
      source hash `1490dc85…` unchanged. `off` text must match the current
      patched runner except for dead CLI default. Regenerate
      `runner_external_episode.patch` and `source_hashes.json`. Extend
      `test_materialize_runner_patch.py`. Do not emit `RaycastTargetCfg`
      for the box. Do not spawn under `/World/ground`.
- [x] A3 `isaac_runner/qualify_stand_runner.py`: pass `--unmapped-box`
      into runner argv and `run_request.json`; refuse `--execute` on
      mismatch. Tests for both modes.
- [x] A4 `isaac_runner/analyze_unmapped_box_hits.py` plus
      `unmapped_box_thresholds.json` (hash recorded here before any C run).
      Tests from synthetic `clouds.jsonl`.
      Frozen SHA-256:
      `727d84805067aa4f07191add3d59196bbd9ba1965307a0dcaa8582ba12b44c97`.
- [x] A5 Local check: unittest discover on `isaac_runner`, materializer
      `--check`. Stop for Dr Sun if A2 changes the `off` path hash
      unexpectedly.

```bash
python3 -m unittest discover -s .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner -p 'test_*.py'
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py --check
```

## C. gpu5070ti (PRD D2)

- [x] C1 Prepare two 8 s `stand_probe` packages (`spawn`, then `lidar`),
      `--stance-hold auto`. Host idle check before each `--execute`.
- [x] C2 Run negative control, return hashes, `analyze_unmapped_box_hits.py`
      must pass AC1 and fail AC2.
      **As frozen: AC1 failed** (median 5 floor-slab hits). AC2 correctly
      failed on the spawn package. See RESULT.md.
- [x] C3 Run positive control, return hashes, analyzer must pass AC2.
      Passed: median 30, min 30.
- [x] C4 AC0/AC3: RESULT cites the survey pins; tomogram SHA-256 vs
      `native_nominal_scope.json`. Write AC4 claim boundary.
      RESULT:
      `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/unmapped_box_lidar_hits/RESULT.md`.
      AC1 remains failed as frozen pending a Dr Sun decision on a
      ground-relative floor cut.
