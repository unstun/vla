# v204 rebuild and behavior equivalence

Local source of truth: this version. The materializer verifies frozen sources,
composes v203, and overlays five owned packages. Use a fresh workspace. Do not
modify the restored underlay or any frozen predecessor.

```bash
python3 materialize_components.py --underlay UNDERLAY/recovery_v196 --workspace WORKSPACE
```

Generate the identical terrain and fixed PCT fixtures as documented in
`../v203/BUILD.md`, or reuse those existing fixtures. Copy frozen
`../v196/building_planner.yaml` to `WORKSPACE/fixtures/building_planner.yaml` and
`../v196/src/lite3_nav2_bridge/config/navigate.xml` to
`WORKSPACE/fixtures/v196-navigate.xml`. Never reuse generated component YAML/XML
profiles: `write_profile` intentionally refuses overwrites.

Use the existing ARM64 `vla-newton-foxy:v149` image, without network, with four
CPUs and 6 GiB memory. Mount UNDERLAY at `/task:ro`, WORKSPACE at `/work`, and the
local versions directory at `/versions:ro`. Work in `/work`:

```bash
source /opt/ros/foxy/setup.bash
source /task/recovery_v196/install/setup.bash
export CMAKE_PREFIX_PATH=/task/recovery_v167/dependencies/osqp-install:$CMAKE_PREFIX_PATH
export MAKEFLAGS=-j2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
colcon build --packages-select pct_planner lite3_nav2_interfaces lite3_nav2_plugins scan_planner scan_nav2_controller nav2_controller lite3_nav2_bridge --executor sequential --cmake-clean-first --cmake-force-configure
source /work/install/setup.bash
python3 /versions/v204/tools/legacy_route_oracle.py --source /versions/v196/src/lite3_nav2_bridge/lite3_nav2_bridge/mission_bridge.py --output /work/fixtures/route-oracle.yaml
python3 /versions/v204/tools/prepare_component_profiles.py --fixtures /work/fixtures
export ROS_DOMAIN_ID=204
export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml
export TERRAIN_TEST_MANIFEST=/work/fixtures/building/terrain.json
export TERRAIN_TEST_DIRECTORY=/work/fixtures/building
export TERRAIN_NATIVE_CONFIG=/work/fixtures/building_planner.yaml
export TERRAIN_NATIVE_PROFILE=/work/fixtures/component.scan.yaml
export TERRAIN_TEST_PROFILE=/work/fixtures/component.yaml
export PCT_TEST_MAP=/work/fixtures/flat.pct
colcon test --packages-select lite3_nav2_plugins scan_planner scan_nav2_controller nav2_controller lite3_nav2_bridge --executor sequential --return-code-on-test-failure --ctest-args -R '^(test_route_policy|test_direct_pct|test_wait_recovery|test_static_terrain|test_terrain_profile|test_map_shell|test_static_support|test_reference_path_utils|test_motion_exchange|test_controller|test_tracking_parity|test_executor_shutdown|test_terminal_completion|test_command_owner|test_terminal_tree|test_mission_bridge)$'
colcon test-result --verbose
```

On the host, `python3 tests/test_native_graph.py` checks launch command assembly
with fake subprocesses. No command above runs a full route, Newton physics,
training, or a real robot. Synthetic ROS actions and stock Wait are component
fixtures; they do not send a navigation goal to an actual moving robot.

For a later authorized integration, the launch interface remains the v203
`terrain_manifest`, native config, backend config, and fresh generated profile.
`native_graph.py` accepts integration identity v204; it is not executed during
these component checks.
