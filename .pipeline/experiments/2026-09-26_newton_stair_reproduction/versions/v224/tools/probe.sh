#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /work/install/setup.bash
python3 /source/tools/prepare_probe.py
source /work/fixtures/probe03.env
export REPLAY_INPUT=/task/stair_collision_replay_20261016/input
export PCT_INPUT=/work/fixtures/building/route.pct
export BENCH_POSES=/work/fixtures/bench_poses.txt
export ROUTE_ENDPOINTS=/work/fixtures/route_endpoints.txt
export PROBE_OUTPUT=/work/field_probe_output03
/work/export_build/field_probe --ros-args --params-file /work/fixtures/environment_candidate03.scan.yaml --log-level error
