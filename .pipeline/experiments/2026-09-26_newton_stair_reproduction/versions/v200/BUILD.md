# Rebuild the component overlay

Local repository sources are authoritative. The build uses the already installed
ARM64 image `vla-newton-foxy:v149` and the SHA-verified v196 recovery archives.
Archive identities and remote locations remain in
`../v196/verification/environment_archives.json` and the v196 archive receipts.

The current restored underlay root is
`/private/tmp/vla_navigation_refactor_20261014/underlay`. It is disposable;
restore the pinned archives again if missing. Preserve their `recovery_vNNN`
directory names because the installed overlays reference `/task` paths.

From this version directory, compose a **fresh** workspace:

```bash
python3 materialize_components.py \
  --underlay /private/tmp/vla_navigation_refactor_20261014/underlay/recovery_v196 \
  --workspace /private/tmp/vla-v200-rebuild
```

Run the following shell commands inside `vla-newton-foxy:v149` with no network,
the restored underlay root mounted **read-only** at `/task`, the fresh workspace
mounted at `/work`, and working directory `/work`. The checked run used four CPUs,
6 GiB container memory and `MAKEFLAGS=-j2`.

```bash
source /opt/ros/foxy/setup.bash
source /task/recovery_v196/install/setup.bash
export MAKEFLAGS=-j2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=200
colcon build --packages-select lite3_nav2_interfaces scan_nav2_controller nav2_controller lite3_nav2_bridge --executor sequential
source /work/install/setup.bash
colcon test --packages-select scan_nav2_controller nav2_controller lite3_nav2_bridge --executor sequential --return-code-on-test-failure --ctest-args -R '^(test_terminal_completion|test_terminal_tree|test_controller|test_tracking_parity|test_executor_shutdown|test_command_owner|test_mission_bridge|pctest|gctest)$'
colcon test-result --verbose
```

This selects behavior regressions, not the historical whole-package formatting
suites. The tests use synthetic feedback and loopback ROS/TCP; no physics or
full-route launcher is involved. The actual checked execution copy and logs are
under `/private/tmp/vla_navigation_refactor_20261014/workspaces/v200`; compact
logs, XML results and source identities are retained in this version.

Runtime composition must use the v198 bridge and producer plus the v200 native
overlay. The old v196/v197 entrypoints are preserved as their original versions;
do not run them under a silently substituted new overlay.
