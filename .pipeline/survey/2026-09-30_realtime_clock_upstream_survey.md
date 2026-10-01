---
origin: primary_source_inspection
reviewed: false
---

# Simulation clocks and real-time pacing

Date: 2026-09-30. Stage: experiment + analysis. Status: **surveyed**.
Dr Sun asked whether upstream systems consider matching simulation and real
time. Sources below were inspected; their pacing implementations were not
executed or imported in this survey. The separate local physics audit is an
execution of our pinned existing path, not an upstream reproduction.

## Two separate contracts

Clock coherence means observations, TF and trajectory progress use one time
source. Real-time pacing means solver elapsed time advances approximately as
fast as wall elapsed time. Publishing `/clock` solves the former, not the latter.
RTF is actual simulated elapsed time divided by actual wall elapsed time.
Neither a configured frequency nor encoded video FPS establishes RTF.

## Verified upstream mechanisms

| System / source | Inspected mechanism | Limit relevant to this project |
|---|---|---|
| [ROS 2 Clock and Time](https://design.ros2.org/articles/clock_and_time.html) | `ROSTime`, `SystemTime` and `SteadyTime` are distinct. `/clock` plus `use_sim_time` distributes simulation time. Pauses and backward jumps are explicitly supported. Hardware timeout clocks should be isolated from ROS message timestamps. | Shared ROS time does not force the simulator to compute in real time. A watchdog must still detect a stalled simulator. |
| [Nav2 controller source](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_controller/src/controller_server.cpp#L355), commit `3c3db59d6969d8ecee8e68468693d006397f4a0c` | `ControllerServer::computeControl` uses `rclcpp::WallRate(controller_frequency_)`. Missed rates produce a warning and reset the loop rate. Goal/cancel/error paths publish zero velocity. | The requested rate is a schedule; a compute overrun is not converted into proof of actual rate. This source motivated v36's wall-clock scheduling. |
| [Gazebo physics tutorial](https://get.gazebosim.org/tutorials?cat=physics&tut=physics_params) and [current SDF world example](https://gazebosim.org/docs/dome/sdf_worlds/) | A 0.001 s fixed step and 1000 updates per real second target RTF 1.0. Current world examples explicitly select `<real_time_factor>1.0</real_time_factor>`. | The Classic tutorial explicitly says insufficient compute runs as fast as available hardware allows. Target RTF 1 does not guarantee it. |
| [Gazebo performance metrics](https://get.gazebosim.org/tutorials?cat=tools_utilities&tut=performance_metrics) | Reports `real_update_rate`, `sim_update_rate`, FPS and RTF separately. Lockstep synchronizes sensor updates with physics. | Lockstep improves temporal consistency; slow compute can still reduce real update rate. Sensor timing and renderer FPS are not interchangeable. |
| [Isaac Sim physics timeline](https://docs.isaacsim.omniverse.nvidia.com/latest/physics/simulation_fundamentals.html), [clock](https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/tutorial_series/tutorial_ros2_clock.html), [RTF](https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/tutorial_series/tutorial_ros2_rtf.html) | The documented default limiter aims to match real-time playback. Simulation time can be published over `/clock`; RTF is observable through a ROS Float32 publisher. | The clock tutorial also offers system timestamps for specific workflows. Relabeling simulation samples with system time does not establish physical RTF. |
| [Isaac Sim publish-rate tutorial](https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/tutorial_series/tutorial_ros2_publish_rate.html) | Distinguishes app-update publishers from simulation-time scheduled sensors, with actual publish rates limited by RTF, configured sensor tick rate and application FPS. | Verify message arrival intervals and sample stamps separately; do not infer 30 real Hz from a simulated-time counter. |
| [MuJoCo Python viewer example](https://mujoco.readthedocs.io/en/stable/python.html#passive-viewer) | After `mj_step` and viewer synchronization, sleep for the positive remainder of the physical timestep minus elapsed computation. The example labels this rudimentary timing and notes drift. | Sleep throttles a fast loop. It cannot make a slow solver meet its budget. An absolute monotonic deadline is preferable for our sustained pacing. |
| [Newton examples](https://github.com/newton-physics/newton/blob/c2ca70bec5998062b0b2d35869865cbe3a49feee/newton/examples/__init__.py), v1.6.0, commit `c2ca70bec5998062b0b2d35869865cbe3a49feee` | Local pinned source: `_throttle_render_fps` at line 484 caps wall rendering FPS after step/render. `--render-fps` at line 663 defaults to no cap and does not change simulation frame timing. `--realtime` at line 709 raises benchmark process priority through `_raise_benchmark_priority`. | `--realtime` is not a 1:1 simulation-clock mode. Our custom headless Newton episode does not call this example runner, so its throttle is not automatically active. Matching a render cap to simulation frame dt can throttle a fast example, but does not solve full-stack capacity. |

Newton is already acquired at the pinned official v1.6.0 source under
`.pipeline/experiments/2026-09-26_newton_macos_policy/source/`; source/ref and
source SHA-256 inventory are in that experiment's `setup/`. Code license:
Apache-2.0. Nav2's inspected controller is Apache-2.0. Remaining entries are
official documentation snapshots read on this date, without new repository
acquisition or a claimed release pin.

## Application to Lite3

The frozen CPU Building physics audit advances **2.000030 s** in **3.731837 s**
wall time: **RTF 0.535937**. This includes 200 Hz measured-pose reads but excludes
LiDAR, transport, navigation and factory/PD startup. Its zero-policy-input
condition is a physics-only ceiling, not whole-system real-time acceptance.
Solver processing takes about 1.366 ms and collision processing 0.415 ms per
1 ms step; policy inference averages 0.204 ms per 20 ms interval. The model
really is CPU; an RTX 5070 Ti host name does not alter `builder.finalize("cpu")`.
See the experiment's `audits/2026-09-30_realtime_budget/` returned raw records.

The implementation direction is to preserve the fixed physical step and causal
simulation stamps, obtain spare compute capacity (first evaluate the supported
CUDA model/contact path), and then pace actual solver progress to monotonic
wall deadlines. Keep one ROS simulation clock for measured-state/trajectory
semantics and independent steady-clock timeout/rate accounting. Record RTF,
lag, overruns and both real/sim update rates continuously.

v36 selects global planning 1 Hz and local/controller 30 Hz on wall time, with
trajectory progress still on simulation time. The physical-speed change belongs
to a later version. Its final bounded component evidence measures controller
29.9993 wall Hz and actual PCT 1.000280884 wall Hz, but recorded successful native
local plans take 87.804795 ms and 120.263012 ms, both over the 33.333 ms budget.
The v36 freeze is explicitly a component candidate, not whole-system alignment.
See `versions/v36/RESULTS.md` in the stair reproduction experiment.
CUDA numerical/contact behavior, paced RTF and the complete
sensor/navigation stack remain unvalidated. No renderer/policy frequency,
physics step, collision geometry or acceptance tolerance is reduced by this
survey. No long trial, training or hardware actuation was run.
