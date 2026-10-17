# Design: RViz Lite3 URDF plus SCAN occupancy

## 1. Boundaries

- **Keep** 09-21 livox `stand_probe` (CSV, sensor-rig URDF, unmapped
  box lidar, GPU RViz observer, bridge `--ipc=host`).
- **Add** two existing Foxy nodes, do not invent a detector:
  1. `robot_state_publisher` + live `rviz_replay_node` (`TORSO` TF)
     from `native_rviz_review.launch.py`.
  2. `scan_04` `scan_planner_node` with `baseline_config/planner.yaml`
     and `cloud:=/quad_0/cloud` (two-goal remap).
- **Not started:** `closed_loop_controller`, PCT, goal A/B, Pi.
- **Not amended:** 09-20 frozen AC1, 09-21 Livox claim.

## 2. Process layout (gpu5070ti)

| Process | Image / workspace | Role |
|---|---|---|
| Isaac runner | conda isaaclab | livox stand_probe |
| Foxy bridge | `e4aa7154…`, `--network=host --ipc=host` | `/quad_0/*` |
| SCAN occupancy | same Foxy image, `scan_04` install, `--ipc=host` | `/grid_map/occupancy` |
| Review helpers | same Foxy image, packaged URDF+meshes | `robot_state_publisher`, live `rviz_replay_node` |
| GPU RViz | `980cec47…` NVIDIA observer | display + NVENC |

Helpers may share one Foxy container if launch is simpler; they must
not share the GPU RViz container (that image is the 09-16 renderer).

## 3. Data flow

1. Bridge publishes joints, body pose, lidar pose, `cloud` / `cloud_raw`.
2. `rviz_replay_node` live: `world` → `TORSO` from `/quad_0/body_pose`.
3. `robot_state_publisher`: URDF on `/robot_description`, joints
   `/quad_0/joint_states`, mesh `file://` prefix as in
   `native_rviz_review.launch.py`.
4. `scan_planner_node`: occupancy from `/quad_0/cloud` (sensor frame,
   `grid_map.cloud_is_world: false`).
5. RViz Fixed Frame `world`: RobotModel, live `/quad_0/cloud_raw`,
   `/grid_map/occupancy`. Drop the spawn-truth AABB as the obstacle
   display (keep AABB jsonl optional, not the story).

## 4. Compatibility

- `planner.yaml` `ground_height: 0.0` is the two-goal pin. Building
  slab is z≈1.56 m. Occupancy may include floor voxels (same geometry
  issue as 09-20 AC1). Report it; do not retune SCAN.
- Livox ~20 k points / 0.1 s into SCAN is denser than the 09-16
  ~2880-point cloud. Fail closed if the planner dies; do not subsample
  in a new node.

## 5. Rollback

Omit the SCAN container and RobotModel display; the 09-21 livox RViz
cloud path remains. Four-group patched SHA unchanged.
