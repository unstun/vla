#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
export REPLAY_OUTPUT=/audit/output/original_$1
if [ "$1" = author ]; then export AUTHOR_GEOMETRY=1; fi
/audit/build_original/original_probe --ros-args --params-file /audit/input/planner.yaml --log-level error
