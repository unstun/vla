set -e
. /opt/ros/humble/setup.sh
. /task/workspace/install/setup.sh
export ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1 V84_INPUT=/task/prepared_inputs V85_INPUT=/task/prepared_inputs
export V85_OUTPUT=/task/results/lanes_attempt01
versions=/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions
/task/workspace/v84_probe/transient_probe --ros-args --params-file "$versions/v81/sync_planner.yaml" > /task/results/transient_attempt02.log 2>&1
tail -n 1 /task/results/transient_attempt02.log
/task/workspace/v85_probe/lane_probe --ros-args --params-file "$versions/v81/sync_planner.yaml" > /task/results/lanes_attempt01.log 2>&1
tail -n 1 /task/results/lanes_attempt01.log
