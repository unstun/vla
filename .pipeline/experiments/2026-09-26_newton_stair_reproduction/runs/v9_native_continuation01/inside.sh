set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
for trial in 01 02; do
 env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/result/result${trial}.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /result/result${trial}.log 2>&1
done
