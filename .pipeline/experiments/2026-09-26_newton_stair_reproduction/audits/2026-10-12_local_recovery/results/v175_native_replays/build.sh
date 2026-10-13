set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v175/install/setup.bash
cmake -S /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v167 -B /task/replay_v175_native_build -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions
cmake --build /task/replay_v175_native_build -j2
