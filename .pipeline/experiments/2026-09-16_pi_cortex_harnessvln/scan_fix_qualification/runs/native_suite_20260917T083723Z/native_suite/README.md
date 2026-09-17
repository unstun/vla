# Native SCAN A/B suite executable

`scan_fix_native_suite` is a copy of the diagnosis package
`scan_replan_diagnosis/native_repro/scan_replan_native_repro` (source file SHA-256 `9feceb1c…`),
renamed so that the two cannot be confused. Every original option and output line is unchanged.
It calls the real `scan_planner::SCANPlannerManager::reboundReplan`, compiled from the
`planner_manager.cpp` passed as `-DSCAN_MANAGER_CPP=`, against the scan_03 headers and installed
static libraries. CMake embeds that path and its SHA-256 in the binary (`SUITE_IDENTITY`).

## Added options

| Option | Behavior |
| --- | --- |
| `--occupied-boxes FILE` | JSON list, or object with `boxes`, of `{"id", "min": [x,y,z], "max": [x,y,z]}`. Every voxel whose centre lies inside a box is marked with `GridMap::setOccupied`, which updates inflation. A voxel outside the map is an error. Prints `MAP_BOX` per box and `MAP_CONDITION boxes=N occupied_voxels=K ...`. Without the option, the original `MAP_CONDITION dynamics_only_empty_grid_no_clouds=true` line is printed. |
| `--follow-up-offsets L` | Strictly increasing simulated seconds since the first plan. At each one, the newest accepted trajectory is sampled and replanned in the same manager, with the FSM `planFromCurrentTraj` chain: previous trajectory (`poly_init=false`), then polynomial, then random polynomial. The sequence stops at the first step with no accepted attempt. |
| `--dump-samples BOOL` | For accepted calls, print `SUITE_PATH` with XYZ every 0.05 s and the endpoint. |
| `--print-samples BOOL` | `false` suppresses the legacy per-sample `SAMPLE` lines; `SUMMARY` is still printed. |

Exit codes: 0 when every requested call or step is accepted, 2 when the planner rejects one, and
64 on a setup error.

## Follow-up timing: exact simulated clock

`reboundReplan` reads `node_->now()` in its previous-trajectory branch (`planner_manager.cpp:177`) and
stores it with each plan (`:308`). The parameter file sets `use_sim_time: true`, so rclcpp enables
the ROS time override on the node clock at creation. The executable never spins the node, so
no `/clock` message or timer callback can move the clock. When follow-ups are requested, the
executable sets the time directly with `rcl_set_ros_time_override(node->get_clock()->get_clock_handle(), ns)`:
first to 100 s, then to 100 s plus each offset. It checks that `node->now()` returns the value it
set, and refuses to run if the override is disabled. The measured offset
(`now - local_data_.start_time_`) is printed in every `SUITE_CALL_BEGIN`. Wall-clock timing was not
needed.

## Per-call records

Every call prints `SUITE_CALL_BEGIN` (call index, attempt, flags, clock, start state, target) and
`SUITE_CALL_END`. For accepted calls, `SUITE_CALL_END` also carries:

- `max_acc`: the norm of the second derivative at 1001 uniform samples of the returned spline. This is
  the diagnosis `diagnosticSpline` method.
- `endpoint_xy_m`, `endpoint_z_m`: the distance from the spline end at its full duration to this call's target.
- `collision_samples`: the `checkCollisionCallback` loop from t = 0 in 0.01 s steps, using
  `getInflateOccupancy(pos, yaw of the next segment)`. Any nonzero result is counted, so outside-map
  cells (-1) count too; `inflated_occupied_samples` and `out_of_map_samples` split the two.
- `duration`, `traj_id` and the distance from the spline start to the requested start.

`stdout` is line-buffered, so the planner's stderr warnings (for example `Dynamic feasibility failed:
acceleration ...`) fall between the matching BEGIN and END records. `analyze_suite.py` classifies
rejections from those lines.

## APIs used beyond the diagnosis executable

| API | Declaration checked |
| --- | --- |
| `GridMap::setOccupied(Vector3d)` | `scan_03/src/plan_env/include/plan_env/grid_map.h:169`, inline body `:339-346`, which calls `applyOccupancyUpdate` (`grid_map.cpp:288-300`) and then `updateInflation` |
| `GridMap::getOccupancy(Vector3d)` | `grid_map.h:170`, `:362-369` |
| `GridMap::getInflateOccupancy(Vector3d, double)` | `grid_map.h:172`, `:371-389` (1 inflated, 0 free, -1 outside the map) |
| `GridMap::indexToPos`, `isInMap(Vector3d)`, `getResolution` | `grid_map.h:162,165,194`, `:398-409,427-429,465` |
| `GridMap::getRegion(Vector3d&, Vector3d&)` | `grid_map.h:193`, `grid_map.cpp:1146-1149` (`getVoxelNum` is declared but not defined, so it is not used) |
| `SCANPlannerManager::grid_map_`, `local_data_`, `pp_` | public, `plan_manage/include/plan_manage/planner_manager.h:39-42` |
| `LocalTrajData::{start_time_, duration_, traj_id_, position_traj_, velocity_traj_, acceleration_traj_}` | `plan_container.hpp:67-77` |
| `UniformBspline::{evaluateDeBoorT, getDerivative, getTimeSum}` | `bspline_opt/include/bspline_opt/uniform_bspline.h:52,53,71` |
| `rclcpp::Node::get_clock`, `Clock::get_clock_handle`, `rclcpp::Time::nanoseconds`, `Duration::seconds` | rclcpp (Foxy); the same calls appear in Foxy `time_source.cpp` and in `planner_manager.cpp:177` |
| `rcl_is_enabled_ros_time_override`, `rcl_set_ros_time_override` | `rcl/time.h` (present since Ardent) |

Local check, 2026-09-17, on Dr Sun's Mac in the existing `machine-dog-nav-pct-scan-humble` conda
environment (ROS 2 Humble, arm64, clang), not in the Foxy image: the package was built against
scratch copies of the scan_03 libraries and run for all 1,668 fixture runs. On that platform, the
original build reproduced the recorded `acceleration at t=3.500 is 1.567 > 1.500` rejection, and the
candidate matched the diagnosis `max_acc` 0.590244562. This is a harness check only. The first Foxy
compile and all acceptance evidence come from suite step B.
