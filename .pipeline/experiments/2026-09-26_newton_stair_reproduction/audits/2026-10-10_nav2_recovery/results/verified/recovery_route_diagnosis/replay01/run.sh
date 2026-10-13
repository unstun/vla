set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v131/install/setup.bash
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/admission_replay -B /task/results/recovery_route_diagnosis/replay01/build -DVERSIONS_ROOT=/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/admission_replay/../../../versions
cmake --build /task/results/recovery_route_diagnosis/replay01/build -j2
/task/results/recovery_route_diagnosis/replay01/build/admission_probe --ros-args --params-file /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/admission_replay/../../../versions/v131/building_planner.yaml --log-level error
