set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_DIAGNOSTIC_PHYSICAL_GROUND=1 VLA_GEOMETRY_INPUT=/moving VLA_GEOMETRY_OUTPUT=/attempt/replay.json /probe/moving_probe --ros-args --params-file /version/building_planner.yaml > /attempt/replay.log 2>&1
