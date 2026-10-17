# Implement: Livox MID-360 CSV on Building stand_probe

Paths relative to `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/`
unless absolute.

## A. Local

- [x] A1 Pin assets: copy v17 sensor-rig URDFs (hash-gated) and meshes;
      download Livox `mid360.csv` @ `1cce107`; path-specific gitignore +
      `isaac_runner/assets/LOCAL_ONLY_BYTES.sha256` + PROVENANCE.
- [x] A2 Fifth materializer group `livox_mid360`: CLI default uniform;
      helper_args forward; `_set_mid360_scan_window` at both update
      sites; fail closed without CSV/rig/40 m/0.1 s. Freeze four-group
      SHA `f0f10206…`. No RTX/Gazebo strings. Regenerate patch +
      `source_hashes.json`.
- [x] A3 `qualify_stand_runner.py`: `--lidar-pattern-mode`; copy assets
      only for livox; argv 40 m + URDF + CSV; refuse execute mismatch.
- [x] A4 Tests: four-group identity, uniform packages need no CSV,
      livox refuse-closed, pins match fallback, no invented lidar.
- [x] A5 unittest + materializer `--check`.

```bash
python3 -m unittest \
  .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_materialize_runner_patch.py \
  .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_qualify_stand_runner.py
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py --check
```

## C. gpu5070ti

- [x] C1 Host idle. Prepare 8 s `stand_probe`, `--unmapped-box lidar`,
      `--lidar-pattern-mode livox_mid360`, `--stance-hold auto`.
- [x] C2 `--execute`, collect video/cloud/hashes.
- [x] C3 Record RESULT.md: ray count vs uniform ~2880; claim remains
      geometric snapshot. Do not amend 09-20 AC1.
- [x] C4 GPU RViz live `/quad_0/cloud_raw` on gpu5070ti using the
      2026-09-16 observer. Bridge `--ipc=host` required (same as the
      09-16 GPU probe). Obstacle overlay = frozen AABB hits, not SCAN.

Rollback: `--lidar-pattern-mode uniform` (default). Four-group bytes
unchanged when the fifth group is not applied.
