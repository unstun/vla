# v202 component rebuild

Run `materialize_components.py --underlay UNDERLAY/recovery_v196 --workspace NEW_WORKSPACE`
with Python 3. The workspace must be new. The script verifies and composes the
frozen v196/v198/v199/v200/v201 chain, then replaces `plan_manage` and
`scan_nav2_controller` with this version. Old sources are never edited.

Use the existing ARM64 `vla-newton-foxy:v149` image, pinned by digest in
PROVENANCE.md. Mount UNDERLAY at `/task:ro`, NEW_WORKSPACE at `/work`, and work in
`/work`. Use `--network=none --cpus=4 --memory=6g`; no simulator is started.

```bash
source /opt/ros/foxy/setup.bash
source /task/recovery_v196/install/setup.bash
export CMAKE_PREFIX_PATH=/task/recovery_v167/dependencies/osqp-install:$CMAKE_PREFIX_PATH
export MAKEFLAGS=-j2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
colcon build --packages-select pct_planner lite3_nav2_interfaces lite3_nav2_plugins scan_planner scan_nav2_controller nav2_controller lite3_nav2_bridge --executor sequential
source /work/install/setup.bash
export ROS_DOMAIN_ID=202
colcon test --packages-select scan_planner scan_nav2_controller nav2_controller lite3_nav2_bridge --executor sequential --return-code-on-test-failure --ctest-args -R '^(test_reference_path_utils|test_motion_exchange|test_controller|test_tracking_parity|test_executor_shutdown|test_terminal_completion|test_command_owner|test_terminal_tree|test_mission_bridge)$'
colcon test-result --verbose
```

The real native worker lifecycle fixture starts no sensor stream or physics. It
checks three activate/cancel/deactivate cycles and direct route receipt. The
native direct-output fixture injects a completed fixed spline through the real
SCAN output function and observes Tracker consumption; it is not a solver or
navigation trial. The existing 300-sample tracker comparison checks unchanged
phase, velocity and heading calculations. Standalone SCAN still uses its ROS
interface unless supplied `DirectIO`.

The runtime profile and launch remain inherited from v201. `spline_topic` has
been removed from the standalone controller YAML because no internal ROS spline
subscriber exists. `native_worker_enabled=false` is for component fixtures only;
it no longer enables an external ROS spline producer. Route and freeze topic
parameters now select observation outlets. External pose, sensor, clock and
physical execution-state input remain ROS interfaces.
