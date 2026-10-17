# Enable Livox MID-360 CSV stand_probe on Building with v17 sensor-rig

Stage: experiment + analysis. Parent: `09-16-emos-harnessvln-reimplementation`.
Sibling of `09-20-isaac-lidar-unmapped-box-hits` (frozen AC1/AC2 unchanged).

## Goal

Turn on the already-ported Livox CSV geometric snapshot
(`livox_mid360` + Isaac Lab `PatternBaseCfg`) on the Building
`stand_probe`, using the pinned v17 sensor-rig URDF, so Dr Sun can see
the cloud versus the uniform 16-beam stand that ran on 2026-09-21.

## User value

The frozen box-hit cloud is a stock 16×2° `LidarPatternCfg` on the
original V12 URDF. That is not the physical MID-360. Enabling the
surveyed Livox table on the surveyed sensor-rig is the smallest honest
next look; it does not claim a hardware match.

## Background

- Survey (`surveyed`):
  `.pipeline/survey/2026-09-21_isaac_mid360_livox_upstream_survey.md`.
  Rank 1: Livox-SDK `livox_laser_simulation` `1cce107` MIT `mid360.csv`.
  Rank 2: already-ported `mid360_pattern.py` +
  `run_isaac_v12_fallback.py` `_set_mid360_scan_window`.
- Dr Sun, 2026-09-21: do not invent a matcher; enable the CSV path.
  The v17 URDF has the sensor rig; implement it to see how it turns out.
- Frozen 09-20 AC1 (spawn-mode floor hits in the AABB) is not amended
  here. Denser rays do not remove the Building slab from the box
  footprint.

## Decisions

- D1. Reuse `qualify_stand_runner.py` `--case stand_probe`. No SCAN, PCT
  motion publisher, or Pi.
- D2. One 8 s gpu5070ti episode after local tests: `--unmapped-box
  lidar` so the red cuboid stays visible, `--lidar-pattern-mode
  livox_mid360`.
- D3. Spawn asset is the pinned Isaac-safe v17 sensor-rig URDF
  (`803d5527…`); canonical pair (`d0a1be09…`) is recorded. Copy bytes
  into VLA; do not edit `machine-dog`.
- D4. Pattern file is Livox `mid360.csv` SHA-256 `aa1fc08b…` at commit
  `1cce107`. 20 000 rays / 0.1 s, 0.1–40 m. Fail closed without CSV,
  hashes, 10 Hz, or 40 m.
- D5. Default `--lidar-pattern-mode uniform` keeps the four-group
  identity (`patched_sha256` `f0f10206…`) except for dead CLI. The fifth
  group is opt-in.

## Constraints

- Do not invent RTX `emitterStateArrays`, Gazebo `gpu_lidar` rings, or
  a new firing table.
- Do not switch the Building runner to `course=single_box`.
- Do not edit `machine-dog` or `machine-dog-nav`.
- Do not silently amend 09-20 frozen AC1.
- Claim: source-backed geometric snapshot, not a physical MID-360.

## Acceptance Criteria

- [ ] AC0. Local pins: Isaac-safe URDF `803d5527…`, canonical
      `d0a1be09…`, CSV `aa1fc08b…`. Materializer `--check` freezes
      four-group `f0f10206…`. Tests refuse RTX/Gazebo invention and
      refuse livox without CSV+rig+40 m.
- [ ] AC1. Default uniform `stand_probe` packages still pass
      `--unmapped-box off` and do not require the CSV.
- [ ] AC2. One executed `livox_mid360` stand_probe on gpu5070ti returns
      artifacts. `sensor_metrics.jsonl` / cloud size is the Livox window
      (20 000 rays/scan class), not the uniform ~2880. Video + hashes
      recorded. Claim remains geometric snapshot.

## Notes

SCAN scoring, contact taxonomy, stairs, and Pi stay out of this child.
