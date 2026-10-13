set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v130/install/setup.bash
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/origin_contract -B /task/results/recovery_origin_contract/candidate01/build
cmake --build /task/results/recovery_origin_contract/candidate01/build -j2
set +e
/task/results/recovery_origin_contract/candidate01/build/origin_probe --ros-args --params-file /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/../../versions/v128/building_planner.yaml --log-level error
code=$?
set -e
test "$code" = 0
