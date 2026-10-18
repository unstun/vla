#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MAKEFLAGS=-j2
cd /work
colcon --log-base /work/build_logs build --base-paths src --packages-select scan_planner --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3 > /work/build_candidate.log 2>&1
source /work/install/setup.bash
cmake -S /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-17_v237_terminal_approach -B /work/probe_candidate -DV238_CONTRACTS=ON -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions -DCMAKE_BUILD_TYPE=Release > /work/configure_candidate.log 2>&1
cmake --build /work/probe_candidate -j2 > /work/build_probe_candidate.log 2>&1
export REPLAY_INPUT=/work/input02 REPLAY_OUTPUT=/work/candidate REPLAY_OPTIMIZE=1
/work/probe_candidate/replay_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error > /work/candidate.log 2>&1
