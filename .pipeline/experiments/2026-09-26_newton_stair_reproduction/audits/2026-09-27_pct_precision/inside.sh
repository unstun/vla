set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_GEOMETRY_INPUT=/precise VLA_GEOMETRY_OUTPUT=/attempt/native_replay.json /probe/legacy_probe --ros-args --params-file /version/building_planner.yaml > /attempt/native_replay.log 2>&1
