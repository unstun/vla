set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /audit/probe_source_checks -B /audit/probe_build_checks -DCMAKE_BUILD_TYPE=Release
cmake --build /audit/probe_build_checks -j2
env VLA_GEOMETRY_INPUT=/audit/inputs04 VLA_GEOMETRY_OUTPUT=/audit/baseline_checks.json VLA_QUERY_DIAGNOSTICS=1 /audit/probe_build_checks/frontier_probe --ros-args --params-file /audit/inputs04/planner.yaml > /audit/baseline_checks.log 2>&1
