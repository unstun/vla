---
origin: primary_source_inspection_with_ai_synthesis
reviewed: false
date: 2026-10-08
stage: experiment_and_analysis
status: surveyed
runtime_execution: not_run
---

# Mapping backlog and safe navigation: eight GitHub repositories

This is a source survey requested by Dr Sun, not an implementation approval or
a navigation qualification. Repository metadata, fixed-commit source files,
and local v78/v82 evidence were read. No upstream repository was cloned, no
navigation code was changed, and no simulation or remote compute was run.
Recommendations below are hypotheses to test, not demonstrated fixes.

## Main finding

The inspected implementations combine several mechanisms: bounded or
latest-observation input, separate mapping/control rates, local/incremental map
work, continued execution of an already committed trajectory, and sometimes
GPU mapping. They do not establish that a background thread can process an
arbitrarily growing stream while preserving every observation.

Our v82 has a materially stricter processing contract: distinct scans are not
dropped, and the planner rejects map evidence older than 250 ms. Its duplicate
reducer removed **zero** frames in both real runs. Therefore its queue is not
equivalent to ROG-Map's latest-cloud slot or nvblox's bounded/discarding queues.

An especially relevant difference exists in our own upstream: the pinned
PCT-SCAN-ROS2 LiDAR callback prepares the current point buffer and sets a dirty
flag; a separate 50 ms timer performs raycasting/fusion. The inspected local
v50 callback additionally invokes `updateOccupancyCallback()` immediately.
Later v81/v82 worker code still applies every paired cloud through that local
callback. Restoring the upstream scheduling model would change which
observations get fused under overload. It is a useful comparison arm, not an
already safe drop-in repair.

## Pins and scope

These commits were resolved from the GitHub API and then used for raw source
reads. Branch names alone are not the evidence identity. Metadata dates are
commit dates, not a guarantee of maintained deployment support.

| Repository | Branch / inspected commit | Declared license evidence | Relevant environment / boundary |
|---|---|---|---|
| [Nav2](https://github.com/ros-navigation/navigation2) | main / `e48c3296a9e49ee88e7e22b7a1c584a26f8620a3` | Repository API: mixed/unclassified; inspected observation buffer carries BSD conditions; check each component before copying | ROS 2; wheeled/planar navigation architecture, not Lite3 stair support |
| [ROG-Map](https://github.com/hku-mars/ROG-Map) | main / `df59c21304579a13fb3875100f8ce9523ba379a0` | Root GPL-3.0; inspected file headers mention LGPL v3 or later; reconcile at acquisition | ROS 1 Noetic, C++/Eigen/PCL; 3-D occupancy, no Lite3 terrain contract |
| [SUPER](https://github.com/hku-mars/SUPER) | master / `2ad3419c127a617c6d7df6925e81a14175a9c096` | GitHub API has no root classification; inspected planner and ROG headers declare LGPL v3 or later | ROS 1/ROS 2 aerial navigation; backup trajectory ideas only, not legged braking |
| [Elevation Mapping CuPy](https://github.com/leggedrobotics/elevation_mapping_cupy) | main / `20a8a26b67a995b43eb44c23568854d1fed82a52` | MIT root license | ROS 1, Python/CuPy/CUDA, local elevation/traversability; representation differs from our full 3-D map |
| [Isaac ROS nvblox](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox) | main / `79654d29c9f862db6b24c1116ab23a360f3294d5` | Apache-2.0 root license | ROS 2 and NVIDIA GPU; depth/LiDAR reconstruction, different occupancy/ESDF contracts |
| [EGO-Planner](https://github.com/ZJU-FAST-Lab/ego-planner) | master / `bfda51284c8c1b476043255a8145ef925a3778a5` | GPL-3.0 | ROS 1 aerial planner; depth and point-cloud paths differ; README recommends EGO-Swarm for newer work |
| [SCAN-Planner](https://github.com/wuyi2121/SCAN-Planner) | main / `348e8a590a50a5a6bbab8d8c6dcfd171f009be26` | Apache-2.0 root license | Author ROS 1 source; distinct from the imported ROS 2 port |
| [PCT-SCAN-ROS2](https://github.com/yagami-light7/PCT-SCAN-ROS2) | main / `1cf45a1c12ca785ce533293302be09d51daf0ccb` | Mixed repository; API unclassified, component notices require inspection | Exact upstream denominator of our native import; ROS 2 port, not an accepted Lite3 system |

All eight repositories have the evidence label **surveyed** in this report.
Existing project imports/runs retain their separately recorded historical
labels; this survey does not upgrade them.

## Source findings

### 1. Nav2: separate rates, explicit freshness waiting, independent collision monitor

The pinned example config uses controller 20 Hz, local costmap update 5 Hz,
local map publication 2 Hz, and global costmap update 1 Hz. These are configured
rates, not measured performance. They show that control and map rebuilding are
not required to have equal rates.

- [Example rates](https://github.com/ros-navigation/navigation2/blob/e48c3296a9e49ee88e7e22b7a1c584a26f8620a3/nav2_bringup/params/nav2_params.yaml#L94-L101), [local map](https://github.com/ros-navigation/navigation2/blob/e48c3296a9e49ee88e7e22b7a1c584a26f8620a3/nav2_bringup/params/nav2_params.yaml#L242-L252).
- [Map update thread and loop](https://github.com/ros-navigation/navigation2/blob/e48c3296a9e49ee88e7e22b7a1c584a26f8620a3/nav2_costmap_2d/src/costmap_2d_ros.cpp#L302-L306).
- [Controller waiting for a current costmap](https://github.com/ros-navigation/navigation2/blob/e48c3296a9e49ee88e7e22b7a1c584a26f8620a3/nav2_controller/src/controller_server.cpp#L680-L694): this can time out. It is not permission to navigate indefinitely on old data.
- [Observation buffer](https://github.com/ros-navigation/navigation2/blob/e48c3296a9e49ee88e7e22b7a1c584a26f8620a3/nav2_costmap_2d/src/observation_buffer.cpp#L164-L203): zero retention keeps one observation; expected-update freshness uses the time of successful buffering. This is not the same quantity as our original cloud timestamp age.
- [Collision monitor](https://github.com/ros-navigation/navigation2/blob/e48c3296a9e49ee88e7e22b7a1c584a26f8620a3/nav2_collision_monitor/src/collision_monitor_node.cpp#L444-L468) consumes sensor sources and commands a stop for invalid sources when the source timeout is enabled. Its [README](https://github.com/ros-navigation/navigation2/blob/e48c3296a9e49ee88e7e22b7a1c584a26f8620a3/nav2_collision_monitor/README.md) describes bypassing costmaps and trajectory planners for emergency collision monitoring.

Transfer value: define mapping, trajectory production, trajectory execution,
and fresh-sensor emergency checks separately. A Lite3 implementation still
needs three-dimensional body clearance, floor/drop support, dynamic obstacles,
the sole command owner and existing stop arbitration. A 2-D collision monitor
alone cannot certify a stair trajectory. Do not copy the example's looser time
limits or replace source timestamps with receipt times.

### 2. ROG-Map: latest-cloud admission plus efficient map representation

[The ROS callbacks](https://github.com/hku-mars/ROG-Map/blob/df59c21304579a13fb3875100f8ce9523ba379a0/rog_map/src/rog_map/rog_map.cpp#L285-L330)
store one point cloud and its associated pose. A later arrival overwrites that
slot. `unfinished_frame_cnt > 1` produces a non-realtime warning; the update
callback copies the current slot, clears the count, and maps it. Subscriber
queues are also configured to one. A 1 ms timer is a polling interval, not
proof of 1,000 Hz map processing.

[Probability updates](https://github.com/hku-mars/ROG-Map/blob/df59c21304579a13fb3875100f8ce9523ba379a0/rog_map/src/rog_map/prob_map.cpp#L565-L647)
update derived grid counters only when the cell's classification changes.
[Inflation counters](https://github.com/hku-mars/ROG-Map/blob/df59c21304579a13fb3875100f8ce9523ba379a0/rog_map/src/rog_map/inf_map.cpp#L183-L207)
add/remove each obstacle's influence. [Modulo-based indexing](https://github.com/hku-mars/ROG-Map/blob/df59c21304579a13fb3875100f8ce9523ba379a0/rog_map/src/rog_map/sliding_map.cpp#L205-L230)
supports a sliding local map; the README also describes multi-resolution
occupancy/inflation maps.

Transfer value: compare bounded admission and per-operation representation.
However, our SCAN already has incremental inflation and circular indexing;
merely adding those names does not supply a new optimization. ROG-Map's
unknown/out-of-map query semantics, inflation geometry, pose association and
multi-resolution boundaries differ. Latest-only admission can lose a transient
observation; no such omission is authorized by this survey.

### 3. nvblox: GPU work, bounded queues and configured integration rates

- [Queue implementation](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox/blob/79654d29c9f862db6b24c1116ab23a360f3294d5/nvblox_ros/include/nvblox_ros/impl/nvblox_node_impl.hpp#L33-L99): ready items are removed under a queue lock and processed after releasing it; when admission exceeds the maximum, the oldest queued item is removed.
- [Default maximum queue length](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox/blob/79654d29c9f862db6b24c1116ab23a360f3294d5/nvblox_ros/include/nvblox_ros/node_params.hpp#L73-L85) is ten at this pin. The older ROS 1 fork's documentation showing thirty is not the source used here.
- [LiDAR integration admission](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox/blob/79654d29c9f862db6b24c1116ab23a360f3294d5/nvblox_ros/src/lib/nvblox_node.cpp#L1265-L1284) deliberately discards messages that arrive sooner than the configured integration interval. [Transform readiness](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox/blob/79654d29c9f862db6b24c1116ab23a360f3294d5/nvblox_ros/src/lib/nvblox_node.cpp#L723-L734) is checked using the message frame and timestamp.
- The [README](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox/blob/79654d29c9f862db6b24c1116ab23a360f3294d5/README.md#L7-L19) identifies GPU reconstruction and a Nav2 costmap output.

Transfer value: an explicit overload policy and separate processing rates are
first-class interfaces. A count-bounded queue alone is not a bound on source
age. GPU mapping is an alternative implementation requiring a new map contract
and hardware-qualified measurements; it is not a speed result for our Mac
amd64-emulated SCAN worker. MID-360 scan geometry also needs a verified adapter.

### 4. Elevation Mapping CuPy: local terrain representation and GPU kernels

[The point-cloud subscription](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/20a8a26b67a995b43eb44c23568854d1fed82a52/elevation_mapping_cupy/src/elevation_mapping_ros.cpp#L75-L90)
has queue length one. [The callback](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/20a8a26b67a995b43eb44c23568854d1fed82a52/elevation_mapping_cupy/src/elevation_mapping_ros.cpp#L340-L362)
looks up the sensor transform at the cloud timestamp before passing data into
the map. [CuPy point and cell kernels](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/20a8a26b67a995b43eb44c23568854d1fed82a52/elevation_mapping_cupy/script/elevation_mapping_cupy/elevation_mapping.py#L330-L374)
perform the mapping work. [Example configuration](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/20a8a26b67a995b43eb44c23568854d1fed82a52/elevation_mapping_cupy/config/core/core_param.yaml#L1-L27)
uses a local eight-metre map at four-centimetre resolution and separates pose
and variance update rates.

Transfer value: a particularly relevant terrain-processing reference for a
legged robot. Its elevation representation and filters do not reproduce our
three-dimensional body obstacles, multiple floor layers or historical support
contracts. A one-frame queue does not preserve every observation, and the
callback can wait for TF; GPU usage does not guarantee end-to-end deadlines.

### 5. SUPER: commit an executable trajectory and a backup before replacement

[The replan path](https://github.com/hku-mars/SUPER/blob/2ad3419c127a617c6d7df6925e81a14175a9c096/super_planner/src/super_core/super_planner.cpp#L165-L279)
constructs a new exploration trajectory and its backup before replacing the
committed command trajectory. A failed replan does not itself clear the
currently committed trajectory in [the FSM branch](https://github.com/hku-mars/SUPER/blob/2ad3419c127a617c6d7df6925e81a14175a9c096/super_planner/src/super_core/fsm.cpp#L45-L79).
[Command publication](https://github.com/hku-mars/SUPER/blob/2ad3419c127a617c6d7df6925e81a14175a9c096/super_planner/include/ros_interface/ros2/fsm_ros2.hpp#L323-L343)
has a separate 10 ms timer/callback group. At this pin, the replan timer is
actually attached to `exec_cbk_group_`, despite a separately allocated
`replan_cbk_group_`; do not claim all three timers have independent execution.

[Backup generation](https://github.com/hku-mars/SUPER/blob/2ad3419c127a617c6d7df6925e81a14175a9c096/super_planner/src/super_core/super_planner.cpp#L828-L903)
checks visible/free trajectory geometry and stopping distance. The inspected
code also rejects a replan exceeding 90% of `replan_forward_dt` after it
finishes. That is not a hard preemptive deadline and is not permission to
reintroduce our rejected v49 mechanism.

Transfer value: preserve a valid committed segment while calculating its
replacement, with a separately qualified safe-stop plan. The aerial stopping
model does not establish Lite3 stopping distance, stair support, or safe
continuation on stale observations. This addresses behavior during delay, not
the mapper's intrinsic throughput.

### 6. EGO-Planner: local, event-marked map updates; distinguish sensor paths

[The depth path](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/plan_env/src/grid_map.cpp#L653-L716)
stores a paired depth image/pose and marks it dirty. A 50 ms occupancy timer
projects/fuses only when new input is marked. The [point-cloud path](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/plan_env/src/grid_map.cpp#L730-L810)
instead directly marks inflated points in a local update range. These are not
equivalent sensor fusion procedures.

Transfer value: separate admission from processing, bound the local work, and
avoid assuming a timer's period is the achieved map frequency. It is a useful
ancestral reference; its README recommends EGO-Swarm for current adoption.
The direct point-cloud mode must not be substituted for our full ray-based
occupancy, clearing and stair support behavior.

### 7–8. SCAN author code and the imported ROS 2 port: inspect before redesigning

The author [ROS 1 initialization](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_env/src/grid_map.cpp#L126-L148)
has separate subscriptions and a 50 ms occupancy timer. The exact imported
ROS 2 port retains [that timer](https://github.com/yagami-light7/PCT-SCAN-ROS2/blob/1cf45a1c12ca785ce533293302be09d51daf0ccb/src/planner/plan_env/src/grid_map.cpp#L149-L166),
[dirty-gated fusion](https://github.com/yagami-light7/PCT-SCAN-ROS2/blob/1cf45a1c12ca785ce533293302be09d51daf0ccb/src/planner/plan_env/src/grid_map.cpp#L743-L772),
and a [LiDAR callback ending in dirty flags](https://github.com/yagami-light7/PCT-SCAN-ROS2/blob/1cf45a1c12ca785ce533293302be09d51daf0ccb/src/planner/plan_env/src/grid_map.cpp#L872-L938).
Multiple callbacks before a fusion tick overwrite the prepared point buffer;
the port does not promise that every observed scan is fused.

Its [occupancy update](https://github.com/yagami-light7/PCT-SCAN-ROS2/blob/1cf45a1c12ca785ce533293302be09d51daf0ccb/src/planner/plan_env/src/grid_map.cpp#L288-L299)
already changes inflation only when occupancy crosses the classification
threshold. Thus a generic recommendation to add incremental inflation would
ignore existing code.

Local evidence: `versions/v50/verification/materialized_native/src/plan_env/src/grid_map.cpp:1093–1096`
adds immediate fusion; `versions/v81/async_mapping_methods.inc:70–93` invokes
the writer's cloud callback for each paired cloud. The v82 reducer retains
distinct clouds and its recorded reduction count is zero. This establishes a
processing-contract difference; it does not establish the exact historical
commit introducing it, nor prove that restoring the upstream timer fixes
navigation. The prior v77 upstream trial already failed/stalled, so an entire
upstream rollback is not supported.

## What the local measurements actually require

The [v78 profile](../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-05_map_processing/REPORT.md)
has four million map voxels and 2,755 inflation neighbors per changed occupied
cell. Seven scans induce 926,950 cached voxel fusions and 25,175,190 inflation
neighbor visits, including sliding removals. The large work count occurs even
with incremental inflation. The 977 ms historical input scope contains seven
different scans, not twelve redundant rebuilds of the same cloud.

The [v82 report](../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-05_safe_mapping_repair/REPORT.md)
shows genuine queues up to six clouds, background batch maxima of 816/1,062 ms,
and additional snapshot copies. Mean/maximum batch time is not individual scan
time or planner solve time. Successful planning is 11.114/10.959 Hz, with
23.787/31.283 s pauses. These are Mac/amd64-emulated measurements, not GPU
execution figures and not a matched hardware comparison with any upstream.

## Recommended order, pending design review

1. **First comparison target: exact PCT-SCAN-ROS2 mapping admission versus our
   current per-frame path**, with identical recorded point clouds, paired poses,
   map settings and native host. Measure source-age distribution, pending work,
   completed revision age, map differences and obstacle/clearing retention.
   Preserve original results even when a candidate loses a critical observation.
   This isolates the changed contract before replacing a whole planner.
2. **Architecture reference: Nav2's separation of fresh-sensor emergency checks,
   map processing and command execution**, plus SUPER's committed-trajectory
   handover. For Lite3, explicitly retain floor/drop/body checks and original
   ownership/cancellation. Define safe continuation and controlled stopping
   when a new map is pending; do not merely turn off the 250 ms gate.
3. **Implementation reference: ROG-Map's admission and data structures.**
   Evaluate precise operation/layout differences, not features we already have.
   A latest-only or bounded-drop variant is a changed sensing contract. Before
   adopting it, test briefly visible obstacles, non-repetitive scan coverage,
   narrow objects, clears, dynamic objects and pose/cloud pairing. Keeping the
   every-distinct-frame contract instead requires demonstrably adequate service
   throughput under burst load.
4. **GPU alternatives: CuPy elevation mapping and nvblox.** Compare only after
   specifying representation and Lite3 support semantics. Reproduction on a
   native Linux/NVIDIA host needs separate execution authorization; this survey
   does not launch it or infer its speed.

The likely design direction is a measured workload/admission contract with
separate safety and trajectory execution, not another thread added to an
unchanged unbounded workload. No candidate is yet selected for code import.
v48 remains the local experimental reference; v82 remains frozen as failed.

## Original run entry points, not executed

Commands below are source/documentation leads, not tested instructions for our
current image. Resolve each pinned dependency set before reproduction.

| Repository | Upstream installation/demo entry |
|---|---|
| Nav2 | [Official quickstart](https://docs.nav2.org/rolling/getting_started/quickstart/quickstart/); `ros2 launch nav2_bringup tb3_simulation_launch.py headless:=False` after the matching ROS/Nav2 setup |
| ROG-Map | [Pinned README](https://github.com/hku-mars/ROG-Map/blob/df59c21304579a13fb3875100f8ce9523ba379a0/README.md); `catkin_make -DBUILD_TYPE=Release`; `roslaunch rog_map_example marsim_example.launch` after its MARSIM launch |
| SUPER | [Pinned README](https://github.com/hku-mars/SUPER/blob/2ad3419c127a617c6d7df6925e81a14175a9c096/README.md); ROS 2 `colcon build --symlink-install`; `ros2 launch mission_planner click_demo.launch.py` |
| Elevation Mapping CuPy | [Pinned README](https://github.com/leggedrobotics/elevation_mapping_cupy/blob/20a8a26b67a995b43eb44c23568854d1fed82a52/README.md); provided Docker setup, `catkin build elevation_mapping_cupy`; `roslaunch elevation_mapping_cupy turtlesim_simple_example.launch` with TurtleBot dependencies |
| nvblox | [Pinned README quickstart links](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox/blob/79654d29c9f862db6b24c1116ab23a360f3294d5/README.md); release-matched Isaac ROS/CUDA environment and assets required; [release 5.0 RealSense demo](https://nvidia-isaac-ros.github.io/v/release-5.0/concepts/scene_reconstruction/nvblox/tutorials/tutorial_realsense.html) uses `ros2 launch nvblox_examples_bringup realsense_example.launch.py` with mode-specific arguments |
| EGO-Planner | [Pinned README](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/README.md); `catkin_make`; `roslaunch ego_planner simple_run.launch` |
| SCAN / PCT-SCAN-ROS2 | Existing local pinned import and v71–v77 provenance are the starting point; source scheduling inspected here, fresh upstream installation/demo not executed or requalified |

No model weights or training datasets are required for the inspected scheduling
mechanisms themselves. Example bags, environments, learned traversability
filters and simulator assets have separate requirements. No runtime performance
claim from a README is adopted as a result on our robot or hardware.
