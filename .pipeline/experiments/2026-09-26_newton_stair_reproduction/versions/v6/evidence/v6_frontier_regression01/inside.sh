set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /version/regression_probe -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j2
env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/attempt/legacy.json VLA_QUERY_DIAGNOSTICS=1 /attempt/probe_build/frontier_probe --ros-args --params-file /inputs/planner.yaml > /attempt/legacy.log 2>&1
env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/attempt/resolution01.json VLA_QUERY_DIAGNOSTICS=1 /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /attempt/resolution01.log 2>&1
env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/attempt/resolution02.json VLA_QUERY_DIAGNOSTICS=1 /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /attempt/resolution02.log 2>&1
