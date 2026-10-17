#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /work/install/setup.bash
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-201} ROS_LOG_DIR=/work/ros_logs ROS_HOME=/work/ros_home
export REPLAY_INPUT=/task/stair_collision_replay_20261016/input
source /work/fixtures/probe225.env
python3 /source/tools/prepare_profile.py
export PCT_INPUT=/work/fixtures/building/route.pct ROUTE_ENDPOINTS=/work/fixtures/route_endpoints.txt BENCH_POSES=/work/fixtures/bench_poses.txt
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
cmake -S /source/tools -B /work/probe_build -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions -DCMAKE_BUILD_TYPE=Release
cmake --build /work/probe_build -j4
result_root=${V232_PROBE_ROOT:-/work}
mkdir -p "$result_root"
export PROBE_OUTPUT=$result_root/field_probe_output03
/work/probe_build/field_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error > "$result_root/field_probe03.log" 2>&1
export PROBE_OUTPUT=$result_root/admission_output03
/work/probe_build/admission_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error > "$result_root/admission_probe03.log" 2>&1
