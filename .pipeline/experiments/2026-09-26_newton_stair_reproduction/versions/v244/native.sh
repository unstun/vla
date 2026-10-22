#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v188/install/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
source /task/cooperative_search_v240/install/setup.bash
source /work/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=142 ROS_LOCALHOST_ONLY=1
export REPLAY_INPUT=/work/fixtures/building PCT_INPUT=/work/fixtures/building/route.pct
source /task/callback_failure_v232/fixtures/probe225.env
here=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v244
if [[ "$1" == build ]]; then
 cmake -S "$here" -B /evaluation/build -DVERSIONS_ROOT="${here%/v244}" -DCMAKE_BUILD_TYPE=Release
 cmake --build /evaluation/build -j2
 ldd /evaluation/build/native_probe > /evaluation/linked_libraries.txt
elif [[ "$1" == test ]]; then
 /evaluation/build/test_geometry
 export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml PCT_TEST_MAP=/work/fixtures/flat.pct
 cd /work/build/lite3_nav2_plugins
 ctest --output-on-failure
else
 export CASE_INPUT="$1" PROBE_OUTPUT="$2"
 /evaluation/build/native_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level info
fi
