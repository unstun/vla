set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
export ROS_DOMAIN_ID=219
export ROS_LOCALHOST_ONLY=1
export V78_INPUT=/inputs
for repetition in 1 2 3; do
  if [ "$repetition" = 2 ]; then
    targets="instrumented baseline"
  else
    targets="baseline instrumented"
  fi
  for target in $targets; do
    export V78_OUTPUT=/results/${target}_${repetition}.jsonl
    /workspace/map_probe_build/${target}_map_probe --ros-args --params-file /profile/building_planner.yaml > /results/${target}_${repetition}.log 2>&1
  done
done
