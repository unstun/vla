set -e
. /opt/ros/humble/setup.sh
. /task/workspace/install/setup.sh
export ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1 V84_INPUT=/task/prepared_inputs
version=/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions
mkdir -p /task/results/admission
for schedule in nominal blackout; do
  for mode in fifo timer latest; do
    export V84_MODE="$mode" V84_SCHEDULE="$schedule" V84_OUTPUT="/task/results/admission/${schedule}_${mode}"
    /task/workspace/v84_probe/admission_probe --ros-args --params-file "$version/v81/sync_planner.yaml" > "/task/results/admission/${schedule}_${mode}.log" 2>&1
    tail -n 1 "/task/results/admission/${schedule}_${mode}.log"
  done
done
/task/workspace/v84_probe/transient_probe --ros-args --params-file "$version/v81/sync_planner.yaml" > /task/results/transient.log 2>&1
tail -n 1 /task/results/transient.log
