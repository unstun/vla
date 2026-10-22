#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v188/install/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
source /task/cooperative_search_v240/install/setup.bash
source /task/physical_traversability_v247/native/install/setup.bash
source /work/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=157 ROS_LOCALHOST_ONLY=1
export REPLAY_INPUT=/work/fixtures/building PCT_INPUT=/work/fixtures/building/native_original.pct
source /work/fixtures/probe225.env
here=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v257
if [[ "$1" == build ]]; then
 cmake -S "$here" -B /evaluation/build -DVERSIONS_ROOT="${here%/v257}" -DCMAKE_BUILD_TYPE=Release
 cmake --build /evaluation/build -j2
 ldd /evaluation/build/native_probe > /evaluation/linked_libraries.txt
else
 export CASE_INPUT="$1" PROBE_OUTPUT="$2"
 export STATIC_SUPPORT_INPUT=/work/fixtures/building/native.support
 export STATIC_SUPPORT_FNV=1404261889151999461
 /evaluation/build/native_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level info
fi
