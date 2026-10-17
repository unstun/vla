---
origin: ai_with_source_check
reviewed: false
date: 2026-09-21
task: .trellis/tasks/09-21-isaac-livox-mid360-stand-probe
machine: gpu5070ti (Isaac Lab on the RTX 5070 Ti); analysis local
claim_boundary: "Livox MID-360 source-backed geometric snapshot on Building stand_probe. Not a physical MID-360, not SCAN, not navigation success, not harness validated."
---

# Livox CSV stand_probe on Building with v17 sensor-rig

Survey (`surveyed`):
`.pipeline/survey/2026-09-21_isaac_mid360_livox_upstream_survey.md`.
This run **enables** the already-ported adapter; it does not invent a
new LiDAR.

## Verdict

| Criterion | Status | Evidence |
|---|---|---|
| AC0 pins + four-group identity | pass | CSV `aa1fc08b…` @ Livox `1cce107`. Isaac-safe URDF `803d5527…`, canonical `d0a1be09…` copied from sibling v17a85z (read-only). Four-group patched SHA `f0f10206…` unchanged. Fifth-group executed runner `2b282dc3…`. Local unittest 78/78 + materializer `--check`. |
| AC1 default uniform still works | pass | `--lidar-pattern-mode uniform` packages do not copy CSV/URDF. Tests cover this. No new uniform Isaac episode in this child. |
| AC2 one livox stand_probe | pass as geometric snapshot | `stand_20260921T083849Z_livox_lidar`. `EXTERNAL_EPISODE_FINISHED`. Returned hashes 26/26. 20 000 rays/scan, ~19 700 finite hits. LiDAR prim `.../Robot/mid360_scan_frame`, offset `(0,0,0)`. Box AABB median **233** hits (uniform lidar episode was 30). |

09-20 frozen AC1 is **not** amended.

## Run

8 s `stand_probe`, `--unmapped-box lidar`, `--lidar-pattern-mode
livox_mid360`, `--stance-hold auto`. Host idle before `--execute`
(182 MiB GPU, no compute apps, ports 46240/46241 free).

| Field | Value |
|---|---|
| Run | `livox_mid360_stand_probe/runs/stand_20260921T083849Z_livox_lidar` |
| Clouds | `bd5c94c7…` (32 759 391 B) |
| Video | `f74b02ea…` (1 587 347 B, 1920×1080, 12.5 fps, 3.12 s / 39 frames) |
| Rays / scan | 20 000 (`points_per_scan`) |
| Raw points / scan | 19 662–19 972 |
| First-scan finite hits | 19 932 |
| Box AABB after 1 s settle | min 217, median 233, max 249 / 21 scans |
| Uniform 2026-09-21 lidar compare | ~2 880 rays, AABB median 30 |
| Sensor pose (scan 1) | `(-1.425, -4.532, 2.013)` m on `mid360_scan_frame` |
| Box centre | `(0.887, -4.399, 1.961)` m — same as the frozen pair |

Review copy:
`livox_mid360_stand_probe/review_frames/lidar_third_person_master.mp4`.
The RGB frame shows the sensor-rig (MID-360 housing + front camera
envelope) and the red cuboid. That is the v17 URDF, not the original
V12 body-only mesh.

## What this is / is not

- **Is:** Livox `mid360.csv` windows through Isaac Lab `PatternBaseCfg`
  and `_set_mid360_scan_window`, mounted on the pinned sensor-rig
  `mid360_scan_frame`. Building mesh + `/World/unmapped_box` string
  target unchanged.
- **Is not:** intensity, noise, motion smear, LIO, or a bag compare
  against the physical Lite3 MID-360. The remaining ~70 missed rays per
  scan are mostly out of range / sky, not a claim of hardware fidelity.

Denser rays do not remove the Building slab from the box AABB. A
ground-relative cut `z > local_ground + 0.02` m on this cloud is
report-only (median 228 of 233). Same geometry issue as 09-20 AC1.

## GPU RViz live cloud (2026-09-21)

Reused the 2026-09-16 Foxy RViz observer (`pointcloud_display/observer`,
NVIDIA OpenGL + `h264_nvenc`, topic `/quad_0/cloud_raw`) on a new
livox + `--unmapped-box lidar` stand_probe. SCAN occupancy was **not**
started. Obstacle overlay is the frozen `unmapped_box.py` AABB
(0.01 m pad) published as `/review/unmapped_box_hits`.

First capture `stand_20260921T095218Z_livox_rviz_gpu` rendered NVIDIA
RViz but delivered **zero** ROS samples: the stand Foxy bridge had
`--network=host` only. The 2026-09-16 GPU probe that actually received
`/quad_0/cloud_raw` also set `--ipc=host` on the bridge. FastDDS SHM
does not cross that gap. That empty 41.6 s / 180 KiB mp4 is diagnostic
only.

Second capture after adding `--ipc=host` to the stand bridge (same
observer, same image `980cec47…`):

| Field | Value |
|---|---|
| Run | `livox_mid360_stand_probe/runs/stand_20260921T100017Z_livox_rviz_gpu` |
| Renderer | NVIDIA GeForce RTX 5070 Ti (Ogre.log + `nvidia_renderer_verified`) |
| Encoder | `h264_nvenc`, 1228×826, 10 fps, 42.20 s, 9.7 MiB, SHA `0f99c882…` |
| Cloud receipts | 171 / 171 scans, 19 657–19 972 pts, `frame_id=lidar` |
| AABB hits | min 209, median 232, max 263; `detected=true` on every scan |
| Isaac | 20 s duration, finish at 16 s, `EXTERNAL_EPISODE_FINISHED` |

Review copy:
`livox_mid360_stand_probe/review_frames/rviz_live_wall_time.mp4`
(stills `rviz_t8s.png`, `rviz_t20s.png`). Live AxisColor cloud of the
Building plus the green cuboid labelled `AABB hits 230 / 19665`. That
is a live ROS visualization of the geometric snapshot, not SCAN
occupancy scoring and not a physical MID-360.

## Sibling: URDF + SCAN occupancy

`09-21-isaac-rviz-urdf-scan-occupancy` (this livox child still does
not start SCAN). Evidence:
`livox_mid360_stand_probe/RESULT_urdf_scan_occupancy.md`.
