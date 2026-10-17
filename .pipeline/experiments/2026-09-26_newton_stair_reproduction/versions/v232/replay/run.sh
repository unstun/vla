#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /work/install/setup.bash
cmake -S /source/replay -B /work/replay_build -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions -DCMAKE_BUILD_TYPE=Release
cmake --build /work/replay_build -j4
export TORSO_BOXES=/task/floor_reason_v223/torso_boxes.txt
result_root=${V232_REPLAY_ROOT:-/work/replay_output02}
for input in input critical_input; do
  export REPLAY_INPUT=/task/stair_collision_replay_20261016/$input
  export REPLAY_OUTPUT=$result_root/$input
  test ! -e "$REPLAY_OUTPUT/frames.csv"
  /work/replay_build/collision_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error
done
