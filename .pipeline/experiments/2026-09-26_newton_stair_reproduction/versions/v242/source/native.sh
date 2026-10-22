#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v188/install/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
source /work/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=142 ROS_LOCALHOST_ONLY=1
export REPLAY_INPUT=/work/fixtures/building
export PCT_INPUT=/work/fixtures/building/route.pct
source /task/callback_failure_v232/fixtures/probe225.env
here=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v242
if [[ "$1" == build ]]; then
  cmake -S "$here" -B /evaluation/build -DVERSIONS_ROOT="${here%/v242}" -DCMAKE_BUILD_TYPE=Release
  cmake --build /evaluation/build -j2
  ldd /evaluation/build/native_probe > /evaluation/linked_libraries.txt
elif [[ "$1" == reference_control ]]; then
  export ROUTE_ENDPOINTS=/task/callback_failure_v232/fixtures/route_endpoints.txt
  export PROBE_OUTPUT=/evaluation/development/historical_baseline
  /evaluation/build/baseline_admission --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn
  mkdir /evaluation/development/reference_case
  cat "$ROUTE_ENDPOINTS" > /evaluation/development/reference_case/endpoints.txt
  printf '0\n' >> /evaluation/development/reference_case/endpoints.txt
  export LEGACY_CONTROL=1 GLOBAL_ONLY=1 CASE_INPUT=/evaluation/development/reference_case
  export PROBE_OUTPUT=/evaluation/development/historical_adapter
  /evaluation/build/native_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn
else
  export CASE_INPUT="$1" PROBE_OUTPUT="$2"
  if [[ "$1" == screen ]]; then export SCREEN_POSES=/evaluation/discovery/poses.txt; fi
  /evaluation/build/native_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level info
fi
