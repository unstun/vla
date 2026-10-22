#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v188/install/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
source /task/cooperative_search_v240/install/setup.bash
source /task/physical_traversability_v247/native/install/setup.bash
source /work/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=153 ROS_LOCALHOST_ONLY=1
export REPLAY_INPUT=/work/fixtures/building PCT_INPUT=/work/fixtures/building/native_original.pct
source /work/fixtures/probe225.env
export CASE_INPUT="$1" PROBE_OUTPUT="$2"
export STATIC_SUPPORT_INPUT=/work/fixtures/building/native.support STATIC_SUPPORT_FNV=15212154834549674106
/task/generic_mechanisms_v261/evaluation/build/native_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level info
