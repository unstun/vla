# Design: Livox MID-360 CSV on Building stand_probe

Survey (status `surveyed`):
`.pipeline/survey/2026-09-21_isaac_mid360_livox_upstream_survey.md`.

## 1. Boundaries

- **Keep** the Building patched `run_pct_scan_building.py` path.
  `v12._configure_environment` already builds `PatternBaseCfg` and the
  `mid360_scan_frame` mount when helper_args request `livox_mid360`.
  Building still overwrites `mesh_prim_paths` with the Building mesh +
  optional `/World/unmapped_box` string.
- **Port, do not invent.** Forward existing fallback flags. Call
  `v12._set_mid360_scan_window` at both LiDAR update sites. Do not add
  RTX, Gazebo rings, or a new CSV parser.
- **Fifth materializer group** `livox_mid360` after `unmapped_box`.
  Four-group patched SHA `f0f10206…` stays the identity of
  `include_livox_mid360=False`.
- **Launcher:** `qualify_stand_runner.py` copies pinned URDF+meshes+CSV
  into `inputs/` only for livox packages.
- **Not touched:** 09-20 frozen AC1/AC2, SCAN, PCT, Pi, sibling repos.

## 2. Pins

| Item | SHA-256 / commit | Path in VLA |
|---|---|---|
| Livox CSV | `aa1fc08b…` @ `1cce107` | `isaac_runner/assets/livox_mid360/mid360.csv` (local-only) |
| Canonical URDF | `d0a1be09…` | `isaac_runner/assets/lite3_sensor_rig/urdf/lite3_pro_sensor_rig_real_with_interface.urdf` |
| Isaac-safe URDF | `803d5527…` | `…_isaac.urdf` |
| Meshes | hashed in `assets/LOCAL_ONLY_BYTES.sha256` | `…/urdf/meshes/` |
| Fallback helpers | same bytes as packaged bridge `run_isaac_v12_fallback.py` | already in BRIDGE_REF |

Source of the URDF copy: sibling `machine-dog`
`go2_rl_robotlab_lite3_v17a85z/resources/lite3_sensor_rig/` (read-only).

## 3. Data flow

1. qualify `--lidar-pattern-mode livox_mid360` verifies pins, copies
   `inputs/sensor_rig/` and `inputs/livox_mid360/mid360.csv`.
2. Runner argv adds CSV, both URDFs, `--lidar-max-range 40.0`.
3. Building helper_args include those flags. `v12._parser().parse_args`
   then `load_mid360_pattern` into `helper_args.mid360_pattern_table`.
4. `v12._configure_environment` sets spawn asset, lidar prim
   `mid360_scan_frame`, `PatternBaseCfg`, 40 m.
5. Building replaces `mesh_prim_paths` with Building + optional box.
6. Each scan: `_set_mid360_scan_window(lidar, table, scan_index, torch)`.

Uniform default omits CSV/URDF copies and keeps 12 m / TORSO offset.

## 4. Claim boundary

`Livox MID-360 source-backed geometric snapshot` from
`mid360_pattern.py`. Not intensity, noise, motion smear, LIO, or a
physical bag compare.
