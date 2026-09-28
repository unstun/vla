set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
python3 /archive/versions/v19/test_precision.py > /attempt/publisher_tests.log 2>&1
env VLA_GEOMETRY_INPUT=/expired VLA_GEOMETRY_OUTPUT=/attempt/expired.json /probe/legacy_probe --ros-args --params-file /version/building_planner.yaml > /attempt/expired.log 2>&1
env VLA_GEOMETRY_INPUT=/original VLA_GEOMETRY_OUTPUT=/attempt/original.json /probe/legacy_probe --ros-args --params-file /version/building_planner.yaml > /attempt/original.log 2>&1
env VLA_GEOMETRY_INPUT=/moving VLA_GEOMETRY_OUTPUT=/attempt/moving.json /probe/legacy_probe --ros-args --params-file /version/building_planner.yaml > /attempt/moving.log 2>&1
env VLA_GEOMETRY_INPUT=/moving VLA_GEOMETRY_OUTPUT=/attempt/moving_repeat.json /probe/legacy_probe --ros-args --params-file /version/building_planner.yaml > /attempt/moving_repeat.log 2>&1
