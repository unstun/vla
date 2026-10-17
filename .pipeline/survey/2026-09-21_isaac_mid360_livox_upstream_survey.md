---
origin: ai+web
reviewed: false
date: 2026-09-21
stage: planning
status: surveyed
related_task: .trellis/tasks/09-20-isaac-lidar-unmapped-box-hits
claim_boundary: "Surveyed only. Nothing cloned, imported, or run. The unmapped-box stand_probe still used uniform LidarPatternCfg. Enabling livox_mid360 is not authorized by this note."
---

# Isaac LiDAR vs physical MID-360: open-source patterns

**Question (Dr Sun, 2026-09-21).** Do not invent a closed-door MID-360
matcher. How do open-source stacks simulate Livox MID-360, and what of
that is already in this repo?

**Status: `surveyed`.** Notes:
`2026-09-21_isaac_mid360_livox_sources/`.

## Criteria

1. Reuse a published MID-360 firing table or a documented Isaac/Gazebo hook.
2. License copyable (MIT/BSD/Apache) or already pinned here.
3. Fits the Building runner (`MultiMeshRayCaster`), or is explicitly a
   different stack (RTX / Gazebo / real driver).
4. Does **not** claim a physical MID-360 without a recorded comparison.

## Ranking

| Rank | Source | Reuse | Do not reuse |
|---|---|---|---|
| 1 | Livox-SDK `livox_laser_simulation` `1cce107` MIT, `scan_mode/mid360.csv` (16.8 MB at pin) | Ordered azimuth/zenith CSV; this is the table `mid360_pattern.py` already names | Gazebo plugin C++; optional gaussian noise as “the real sensor”; xacro VFOV −7.22…+55.22 as datasheet |
| 2 | Already-ported Lite3 adapter: `PatternBaseCfg` + `_set_mid360_scan_window` in pinned `run_isaac_v12_fallback.py` | Isaac Lab’s public custom-pattern hook; 20 000 rays / 0.1 s, 0.1–40 m when that mode is on | Treating opt-in `livox_mid360` as validated hardware; using it without the CSV + sensor-rig URDF |
| 3 | Isaac Lab v2.3.2 `PatternBaseCfg` / `LidarPatternCfg` BSD-3-Clause | Custom `func` for CSV windows; Bpearl shows Lab’s own vendor-angle pattern | Stock `LidarPatternCfg` 16×2° as “MID-360” (this is the current stand_probe) |
| 4 | Isaac Sim RTX `emitterStateArrays` (discussion [#685](https://github.com/isaac-sim/IsaacSim/discussions/685); docs) | Later RTX fidelity, from a **recorded** cycle | New renderer in this child; forum 283074 OS1 **40-beam rotary** snippet |
| — | Gazebo `gpu_lidar` rings (e.g. LXRobotics 720×40) | — | Spinning dense lidar sold as MID-360 |
| — | `livox_ros_driver2` / EMOS `/livox/lidar` | Real-robot topic contract for a later bag compare | Not a simulator |

## What the current box-hit cloud actually is

`stand_20260921T072340Z_unmapped_lidar`: `--lidar-pattern-mode` default
**uniform**, 16 channels, 2° azimuth, VFOV −7°…+52°, max 12 m, TORSO
offset, original V12 URDF. `sensor_metrics.jsonl`: **2880** rays, ~2860
finite hits. Bridge README: not real MID-360 or LIO.

That uniform FOV copy is the same *class* of shortcut as the NVIDIA
forum rotary-40 example and Gazebo `gpu_lidar` rings. It is not the
Livox CSV.

## What already exists here (do not rewrite)

`references/upstream/2026-09-11_lite3_sim_bridge/source/lite3_sim_bridge/mid360_pattern.py`
loads the Livox CSV (header `Time/s,Azimuth/deg,Zenith/deg`), converts
with the plugin yaw / `zenith-90` pitch rule, slices 20 000 rays per
0.1 s, and refuses intensity, multi-return, weather, electronic noise,
and intra-scan motion. Runtime mode `livox_mid360` requires the CSV
path, sensor-rig URDF, 10 Hz, 0.1 m min, **40 m** max. The CSV file is
**not** in this tree; stand_probe did **not** turn the mode on.

## Recommendation (no implementation in this note)

Do **not** write a new LiDAR. If the next goal is closer MID-360
**geometry** in Isaac, turn on the already-ported Livox CSV + Isaac
`PatternBaseCfg` path (rank 1+2). Keep the claim
“source-backed geometric snapshot”. AABB slab hits on AC1 would still
happen: denser rays do not remove the floor from the box footprint.

Do **not** move this runner to RTX to “match hardware.” Do **not** copy
Gazebo `gpu_lidar` rings. A physical bag vs sim compare is a separate
authorized task (`livox_ros_driver2`).

## Labels

`surveyed` only. CSV not imported. `livox_mid360` not reproduced on
these stand_probe runs. Not `validated` against a Lite3 MID-360.

SCAN, PCT, Pi, and the frozen AC1 floor-cut decision are out of this
note.
---
