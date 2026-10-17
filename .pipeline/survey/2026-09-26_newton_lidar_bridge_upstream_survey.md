---
origin: ai_only
reviewed: false
date: 2026-09-26
status: surveyed
---

# Newton stair reproduction: sensor occlusion and bridge sources

## Question and selection criteria

Dr Sun asked that encountered reproduction problems first be investigated in
GitHub open-source implementations. The immediate measured failure is that
19,998 of 20,000 rays hit the MID360's own metal CAD housing within 0.1 m.
The archived scan origin and Newton world pose agree within 1 micrometre; moving
the sensor frame would change the archived condition. Keep the original Livox
directions, mount, external near occlusion, remaining robot geometry, original
Building mesh and official skinned human. Prefer existing CPU-capable Newton
APIs and narrow adaptation of a demonstrated upstream pattern.

Source files, exact URLs, commits, byte counts and SHA-256 are recorded in
`2026-09-26_newton_lidar_bridge_sources/manifest.json`. Downloaded excerpts are
read-only references. None of these newly surveyed repositories has been
executed as a complete upstream application.

## Source comparison

| Source / pin / license | Actual inspected behavior | Applicability |
| --- | --- | --- |
| [RobotecAI/RGLGazeboPlugin](https://github.com/RobotecAI/RGLGazeboPlugin/tree/d4bf3cf36fe4a363a56df1bec2ce3809720db563), main, `d4bf3cf36fe4a363a56df1bec2ce3809720db563`, Apache-2.0 (root LICENSE inspected; API says NOASSERTION) | `RGLServerPlugin/src/Scene.cc:50-69,102-104`: constructs `entitiesToIgnore` from the sensor link and omits those entities from the ray scene. README warns that fixed-joint merging can accidentally exclude the entire robot. | Selected pattern: exclude only the original sensor link's two visual meshes in the sensor BVH. Do not use the merged Newton body ID. Full plugin requires Gazebo Harmonic, Ubuntu and CUDA/OptiX; it cannot run natively on this Mac. Original demo: `gz sim test_world/rgl_playground.sdf` after its documented build. |
| [google-deepmind/mujoco](https://github.com/google-deepmind/mujoco/tree/a79d65c4e54d4be91f2a25dc4ecccc37d24b0e95), main, `a79d65c4e54d4be91f2a25dc4ecccc37d24b0e95`, Apache-2.0 | `src/engine/engine_ray.c:67-73`: `bodyexclude` removes that body's geometry. `src/engine/engine_sensor.c:559-560`: a site rangefinder passes its own body as the exclusion. The installed MuJoCo 3.12 header exposes the same public argument. | Supports sensor-owner exclusion as an established geometric convention. A wholesale body exclusion is unsuitable here because the URDF importer merges fixed sensor parts into TORSO. Use installed `mj_ray` in an analytic comparison, not for the concave Building physics. No complete MuJoCo upstream demo newly run. |
| [Livox-SDK/livox_laser_simulation](https://github.com/Livox-SDK/livox_laser_simulation/tree/1cce1073633a062b92e30243a4c2920e45551bb5), main, `1cce1073633a062b92e30243a4c2920e45551bb5`, MIT | `src/livox_points_plugin.cpp:193-196` starts rays at `minDist * axis + offset.Pos()`. `urdf/livox_mid360.xacro` uses a 0.1 m minimum and a separate sensor link. The MID360 demo still references a Mid40 visual mesh. | Keep our already pinned ray CSV. Do not copy this minimum-distance start: it would change how unrelated objects inside 0.1 m occlude the scene. Do not treat its demo mount/mesh as MID360 physical calibration. ROS1/Gazebo/ODE implementation, not native Newton or macOS. |
| [newton-physics/newton](https://github.com/newton-physics/newton/tree/c2ca70bec5998062b0b2d35869865cbe3a49feee), already imported 1.6.0, Apache-2.0 | `newton/_src/sim/model.py:1624-1711` publicly builds a BVH from shape flags; `newton/_src/geometry/raycast.py:916` exposes `intersect_ray`. No per-ray sensor-owner exclusion argument at this pin. | Reuse the public BVH and ray APIs. A separate shallow model view with private flags/BVH preserves the physical/render model. The adapter is local glue, not an upstream Newton LiDAR implementation. |
| [NVIDIA/warp](https://github.com/NVIDIA/warp/tree/f4c57f26f1e3936a89afd283e39fcabf6d548dc7), tag v1.17.0, `f4c57f26f1e3936a89afd283e39fcabf6d548dc7`, Apache-2.0 | `warp/examples/core/example_mesh.py` changes mesh points and calls `Mesh.refit()` before querying; `example_raycast.py` calls `mesh_query_ray`. | Retain this update-before-query pattern for actual current UsdSkel skin vertices. Original example: `python -m warp.examples.core.example_mesh --device cpu`; not newly executed here. Our fixed-root animation/identical-frame control is separate integration evidence. |
| [vybhav-ibr/newton_ros](https://github.com/vybhav-ibr/newton_ros/tree/94baf7bb19cc77946d00904227467d841b70c446), main, `94baf7bb19cc77946d00904227467d841b70c446`, no root license; package.xml says TODO | `newton_ros_bridge.py` imports rclpy into the simulator process. `sensors/lidar_impl.py` reprojects six depth images to a uniform angular grid. README declares Newton 1.0.0 testing and possible newer-version incompatibility. | Surveyed only. It does not directly solve native Mac Newton + Linux ROS separation or reproduce our exact Livox ray table. Do not copy unlicensed code or replace the qualified 1.6 environment. Original commands are colcon build and `python test_import.py`; not run. |

## Selected bounded adaptation

Use the Robotec/MuJoCo sensor-owner exclusion convention with Newton's public
BVH API. Resolve the sensor's **original URDF link**, before fixed-joint
collapse, and exact-match its two scaled CAD visual meshes. Preserve all
physical shapes, render visibility, body pose, other robot shapes, Building
geometry and human geometry. This is an explicitly declared geometric sensor
adaptation; it does not establish RTX material parity or physical MID360
calibration. Keep unfiltered mode as the diagnostic default, and request the
selected mode explicitly in qualified sensor runs.

Required controls before closed-loop use:

1. Analytic upstream MuJoCo `mj_ray(bodyexclude=...)` comparison against the
   Newton sensor view: background visible through own emitter, a distinct robot
   part visible, and an unrelated near obstacle still blocks the background.
2. Physical/render flags are bit-identical before and after creating the sensor
   view; only the two original sensor-link meshes differ in the view.
3. Original scene ray windows and mount remain unchanged. Retain other robot
   near hits, even though returns below 0.1 m are invalid measurements.
4. Official human fixed-root skin changes alter rays; identical animation
   repeats yield identical rays. No actor truth reaches the tracker.

The former optical-only hypothesis was disproved and remains archived. The
earlier two-mesh diagnostic pass alone is not the acceptance evidence above.

## Bridge boundary

The archived project already contains a versioned TCP transport and original
ROS node. Reuse is preferable to inventing a new HTTP sensor protocol. However,
its watchdogs compare source and receiver monotonic timestamps as if they share
one OS. macOS and Docker's Linux VM have different monotonic clock origins.
The continuation below records the selected and tested cross-OS adaptation.
Do not disable or relax original watchdogs to force progress. The newton_ros candidate
does not resolve this boundary because it runs rclpy in the simulator process.

Follow-up source: [mavlink/mavros, ros2,
`a5979a5299775d9dd9ce1d57f9cfa1542c5259b9`](https://github.com/mavlink/mavros/tree/a5979a5299775d9dd9ce1d57f9cfa1542c5259b9).
`mavros/src/plugins/sys_time.cpp:372-384,425-489,507-559` uses request/response
timestamps, round-trip rejection, a double exponential filter, convergence and
clock-jump handling. `LICENSE.md` permits BSD/GPLv3/LGPLv3 variants; the BSD text
is retained. Original source makes its symmetric round-trip assumption explicit.
A one-time guessed offset is not equivalent to that implementation.

## Qualified continuation: clock, executor and state storage

The experiment's `references/mavros_clock_port.json` identifies the BSD filter
port and local modifications. `clock_reference_v1` compiles functions extracted
from the actual pinned C++ source and compares 1,124 observations; maximum
filter difference is 0.109375 ns, with matching rejection/reset/convergence.
`clock_live_v1` exercises the actual Mac/Linux channel. The adapter additionally
requires a fresh accepted sync observation and maps timestamps conservatively;
it does not implement the MAVLink wire protocol or change the original watchdog.

Primary sources inspected for subsequent measured failures:

| Source | Local observation and selected action | Boundary |
| --- | --- | --- |
| [ros2/rclpy1223](https://github.com/ros2/rclpy/issues/1223), [1452](https://github.com/ros2/rclpy/issues/1452) | Upstream reports poor high-frequency callback scheduling with MultiThreadedExecutor. Local matched probes show 2/150 versus149/149 body callbacks; use standard SingleThreadedExecutor in the entrypoint. | Issue reports motivated the test; they do not prove the exact internal cause on this Docker/ROS version. Core callbacks unchanged. |
| [docker/for-mac7494](https://github.com/docker/for-mac/issues/7494) and [Docker volumes](https://docs.docker.com/engine/storage/volumes/) | Local atomic-file minimal reproduction preserves truncated JSON for both overlapping and disjoint Mac bind mounts. Move hot state into Linux tmpfs using standard complete-message transfer. | This demonstrates the local failure class, not identity with the issue's Docker4.36 bug. Each probe retains up to10 failure examples, not the total count. |
| [PyZMQ26.4.0 serialization](https://pyzmq.readthedocs.io/en/v26.4.0/howto/serialization.html), [pinned repository](https://github.com/zeromq/pyzmq/tree/b273c0915abd45003dc6378a3c6e8750d39a34c0) | Standard REQ/REP with JSON bytes, sequence+SHA acknowledgment; original parser and reader validate inside Linux. Official MacCP312/LinuxCP310 wheels and all member hashes are recorded in `setup/zmq_dependency.json`. | BSD-3-Clause LICENSE.md inspected inside the distribution; bundled component licenses retained. No pickle, sensor protocol replacement or receipt-time restamping. |
| [moby22020](https://github.com/moby/moby/issues/22020), [Docker cp corner cases](https://docs.docker.com/reference/cli/docker/container/cp/#corner-cases) | Docker cp returns the directory underlying tmpfs. The first two channel probes recovered equal JSON payloads but wrong bytes. Use documented docker exec tar; `stair_native_walk_v2` returns the exact last acknowledged SHA. | Earlier copyback receipts remain archived and do not prove byte identity. Runtime acknowledgments remain separate evidence. |

The 3s ZeroMQ probe rejects stale, future, foreign-run and duplicate-sequence
messages independently. The28.056s integrated run has1,398 matching positive
acknowledgments and no applied-reader errors after the first snapshot. It still
records clock rejection/reconnects with zero commands. These results qualify a
bounded local integration, not stair completion or general timing reliability.

## Next diagnosis sources; no timing changes adopted

The integrated run produces a second1.5m native curve with duration34.250s,
retimed from1.6s; its frozen35wall-second command budget expires. Review the
archived `timed_cubic_initialization.h` and its source-backed retiming history
before modifying trajectory timing. Review [ROS2 Clock and Time](https://design.ros2.org/articles/clock_and_time.html)
and [Nav2 simple_progress_checker.cpp](https://github.com/ros-navigation/navigation2/blob/main/nav2_controller/plugins/simple_progress_checker.cpp)
for separation of simulation progress and transport watchdog clocks. These are
survey leads only; no timeout parameter, planner bound or clock semantic was
changed in this continuation. Pin any newly adopted implementation before use.
