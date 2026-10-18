#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
source /task/terminal_approach_v238/install/setup.bash
source /work/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml
export TERRAIN_TEST_MANIFEST=/work/fixtures/building/terrain.json TERRAIN_TEST_DIRECTORY=/work/fixtures/building
export TERRAIN_NATIVE_CONFIG=/work/fixtures/building_planner.yaml TERRAIN_NATIVE_PROFILE=/work/fixtures/component.scan.yaml
export TERRAIN_TEST_PROFILE=/work/fixtures/component.yaml PCT_TEST_MAP=/work/fixtures/flat.pct FEEDBACK_OUTPUT=/work/feedback_output
mkdir /work/regressions
for name in test_controller test_tracking_behavior test_tracking_parity test_shared_support test_static_support test_terminal_completion test_executor_shutdown test_motion_exchange test_map_shell; do
  /work/build/scan_nav2_controller/$name --gtest_output=xml:/work/regressions/$name.xml > /work/regressions/$name.log 2>&1
done
for pair in scan_planner/test_reference_path_utils bspline_opt/test_uniform_bspline lite3_nav2_plugins/test_environmental_cost; do
  name=${pair##*/}
  /work/build/$pair --gtest_output=xml:/work/regressions/$name.xml > /work/regressions/$name.log 2>&1
done
ldd /work/build/scan_nav2_controller/test_controller > /work/regressions/linked_libraries.txt
