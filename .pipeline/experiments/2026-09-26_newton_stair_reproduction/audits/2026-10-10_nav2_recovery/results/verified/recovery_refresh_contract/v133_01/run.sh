set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v133/install/setup.bash
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/refresh_contract -B /task/results/recovery_refresh_contract/v133_01/build -DVERSIONS_ROOT=/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/../../versions
cmake --build /task/results/recovery_refresh_contract/v133_01/build -j2
for mode in 0 1 2; do
  REFRESH_CASE=$mode /task/results/recovery_refresh_contract/v133_01/build/refresh_probe --ros-args --params-file /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/../../versions/v131/building_planner.yaml --log-level error
done
