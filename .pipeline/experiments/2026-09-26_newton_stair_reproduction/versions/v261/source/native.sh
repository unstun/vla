#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v188/install/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
source /task/cooperative_search_v240/install/setup.bash
source /task/physical_traversability_v247/native/install/setup.bash
source /work/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=152 ROS_LOCALHOST_ONLY=1
export REPLAY_INPUT=/work/fixtures/building PCT_INPUT=/work/fixtures/building/native_original.pct
source /work/fixtures/probe225.env
here=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v261
if [[ "$1" == build ]]; then
 cmake -S "$here" -B /evaluation/build -DVERSIONS_ROOT="${here%/v261}" -DCMAKE_BUILD_TYPE=Release
 cmake --build /evaluation/build -j2
 ldd /evaluation/build/native_probe > /evaluation/linked_libraries.txt
elif [[ "$1" == solids ]]; then
 export CASE_INPUT=/evaluation PROBE_OUTPUT=/evaluation/solids
 /evaluation/build/solid_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn
elif [[ "$1" == differential ]]; then
 /evaluation/build/differential_probe /task/generic_mechanisms_v256/evaluation/solids/poses.csv
elif [[ "$1" == support_differential ]]; then
 /evaluation/build/support_differential /task/generic_mechanisms_v256/evaluation/solids/poses.csv
elif [[ "$1" == environmental_differential ]]; then
 /evaluation/build/environmental_differential /task/generic_mechanisms_v256/evaluation/solids/poses.csv
elif [[ "$1" == rotation ]]; then
 /evaluation/build/rotation_probe
elif [[ "$1" == endpoint ]]; then
 /evaluation/build/endpoint_probe /task/space_coverage_v257/cases/E03/endpoints.txt
elif [[ "$1" == graph ]]; then
 /evaluation/build/graph_probe /task/generalization_v242/cases/*/endpoints.txt
elif [[ "$1" == support ]]; then
 export CASE_INPUT=/evaluation PROBE_OUTPUT=/evaluation/support
 /evaluation/build/support_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn
elif [[ "$1" == test ]]; then
 export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml PCT_TEST_MAP=/work/fixtures/flat.pct
 cd /work/build/lite3_nav2_plugins
 ctest --output-on-failure

else
 export CASE_INPUT="$1" PROBE_OUTPUT="$2"
 export STATIC_SUPPORT_INPUT=/work/fixtures/building/native.support
 export STATIC_SUPPORT_FNV=15212154834549674106
 /evaluation/build/native_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level info
fi
