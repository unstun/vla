---
origin: ai_with_source_check
reviewed: false
date: 2026-09-21
task: .trellis/tasks/09-21-isaac-rviz-urdf-scan-occupancy
machine: gpu5070ti (Isaac Lab on the RTX 5070 Ti); analysis local
claim_boundary: "GPU RViz occupancy visualization on a standing Livox snapshot: Lite3 URDF mesh, live /quad_0/cloud_raw, scan_04 /grid_map/occupancy. Not navigation success, not a physical MID-360, and does not amend 09-20 AC1."
---

# RViz Lite3 URDF plus scan_04 occupancy (livox stand)

Sibling of `09-21-isaac-livox-mid360-stand-probe`. That child still
forbids SCAN. This child starts `scan_planner_node` only (no
`closed_loop_controller`, no PCT, no Pi).

## Verdict

| Criterion | Status | Evidence |
|---|---|---|
| AC0 local hooks, meshes, scan_04 identity, no new detector | pass | `python3 test_run_rviz_probe.py` 7/7. Packaged canonical URDF + `inputs/sensor_rig/meshes/`. `inputs/scan_04_identity.json` pin. Helper argv is `scan_planner_node` + `cloud:=/quad_0/cloud`. |
| AC1 GPU video: Lite3 mesh + occupancy Status Ok, nonempty voxels | pass as visualization | `stand_20260921T105823Z_livox_rviz_gpu`. NVIDIA 5070 Ti. RViz: Lite3 URDF Status Ok, Live Point Cloud Ok, Raw SCAN Occupancy Ok. Occupancy receipts 1122, 910 nonempty, median **3231** voxels. |
| AC2 occupancy receipts; box footprint counts; no AC1 amendment | receipts pass; box AABB occupancy **0** | Frozen box AABB on occupancy xyz: 0 / 991 samples. Live `/quad_0/cloud_raw` AABB still median **232** hits. 09-20 AC1 not amended. |

Occupancy visualization is not navigation success.

## Run (accepted)

20 s livox `stand_probe`, `--unmapped-box lidar`, `--stance-hold auto`,
GPU RViz + `scan_04` occupancy + URDF. Host idle before `--execute`
(184 MiB GPU, no compute apps, ports 46240/46241 free).
`robot_state_publisher` present in Foxy image `e4aa7154…`. Returned
hashes 48/48.

| Field | Value |
|---|---|
| Run | `livox_mid360_stand_probe/runs/stand_20260921T105823Z_livox_rviz_gpu` |
| Isaac | `EXTERNAL_EPISODE_FINISHED`, 17.06 s, travel_xy 0.074 m |
| Renderer | NVIDIA GeForce RTX 5070 Ti (`nvidia_renderer_verified`) |
| Encoder | `h264_nvenc`, 1228×826, 43.0 s, 430 frames, 10.0 MiB, SHA `475a132f…` |
| Cloud receipts | 171, 19 656–19 972 pts, SHA `f17a1d73…` |
| Cloud AABB hits | min 209, median 232, max 263 |
| Occupancy receipts | 1122, SHA `bc78d00b…`; nonempty 910; points min/med/max 0 / 3231 / 3315 |
| Occupancy AABB hits | **0 / 991** (`detected=false`) |
| SCAN | `scan_planner_node` only, `cloud:=/quad_0/cloud`, `planner.yaml` `ground_height: 0.0` SHA `42a265a3…` |
| scan_04 | `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_04` |

Review copy:
`livox_mid360_stand_probe/review_frames/rviz_urdf_scan_occupancy.mp4`
(stills `occupancy_t8s.png`, `occupancy_t20s.png`, `occupancy_t35s.png`).

The stills show the Lite3 mesh (not only the odometry arrow), the live
Livox cloud of the Building, and green `/grid_map/occupancy` with
Status Ok. SCAN stayed in FSM `INIT` / `wait for goal` (planner-only,
no goals).

## Diagnostic first execute

`stand_20260921T105341Z_livox_rviz_gpu` passed Isaac and started SCAN,
but RViz could not open `file:///robot/meshes/*.STL` (meshes were
mounted only in the SCAN helper) and `occupancy_audit.py` exited
because `unmapped_box_setup.json` did not exist yet. Collect also
dropped once (SSH/rsync). Fixes: mount `inputs/sensor_rig` at `/robot`
in the GPU RViz container; load the AABB setup when the file appears.
That package is not the AC1 video.

## What this is / is not

- **Is:** standing Livox snapshot with measured-joint URDF TF and
  scan_04 occupancy published from `/quad_0/cloud`.
- **Is not:** two-goal scoring, PCT, Pi `navigate_to`, a physical
  MID-360, or a claim that SCAN occupied the unmapped box.

`planner.yaml` `ground_height: 0.0` is the two-goal pin. Building slab
z≈1.56 m. Occupancy voxels (~3300) did not fall in the frozen box AABB
while the raw cloud still does. Same geometry family as 09-20 AC1.
Reported; SCAN was not retuned.
