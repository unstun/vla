#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
source /task/terminal_approach_v238/install/setup.bash
source /task/cooperative_search_v239/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MAKEFLAGS=-j2
cd /work
# path_searching exports a static archive. Rebuild all native consumers so
# old embedded AStar symbols cannot preempt the repaired implementation.
colcon --log-base /work/build_logs build --base-paths src --packages-select plan_env path_searching bspline_opt scan_planner scan_nav2_controller lite3_nav2_plugins --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3 > /work/build_candidate.log 2>&1
