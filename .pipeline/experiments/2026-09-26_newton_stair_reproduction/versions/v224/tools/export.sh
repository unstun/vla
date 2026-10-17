#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /work/install/setup.bash
cmake -S /source/tools -B /work/export_build -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions -DCMAKE_BUILD_TYPE=Release
cmake --build /work/export_build -j4
export REPLAY_INPUT=/task/stair_collision_replay_20261016/input
export STATIC_PCD=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/static_background/building2_9.pcd
export ENVIRONMENT_OUTPUT=/work/fixtures/building/environment03.env
/work/export_build/export_field --ros-args --params-file "$REPLAY_INPUT/planner.yaml" --log-level error
