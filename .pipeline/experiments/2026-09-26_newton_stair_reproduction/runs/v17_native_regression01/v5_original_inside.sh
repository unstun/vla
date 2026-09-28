set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /version/regression_probe -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j2
env VLA_GEOMETRY_INPUT=/audit/frozen_map VLA_GEOMETRY_OUTPUT=/attempt/fixed.json VLA_QUERY_DIAGNOSTICS=1 /attempt/probe_build/measured_cloud_probe --ros-args --params-file /audit/replay_inputs/planner.yaml > /attempt/fixed.log 2>&1
env VLA_GEOMETRY_INPUT=/audit/frozen_map VLA_GEOMETRY_OUTPUT=/attempt/height.json VLA_QUERY_DIAGNOSTICS=1 /attempt/probe_build/measured_cloud_probe --ros-args --params-file /version/building_planner.yaml > /attempt/height.log 2>&1
