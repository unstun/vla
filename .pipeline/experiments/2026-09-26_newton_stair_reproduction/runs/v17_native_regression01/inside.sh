set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j2
ulimit -v 1500000
env  VLA_GEOMETRY_INPUT=/expired VLA_GEOMETRY_OUTPUT=/attempt/expired01.json /attempt/probe_build/legacy_probe --ros-args --params-file /version/building_planner.yaml > /attempt/expired01.log 2>&1
env  VLA_GEOMETRY_INPUT=/original VLA_GEOMETRY_OUTPUT=/attempt/original66.json /attempt/probe_build/legacy_probe --ros-args --params-file /version/building_planner.yaml > /attempt/original66.log 2>&1
env  VLA_GEOMETRY_INPUT=/moving VLA_GEOMETRY_OUTPUT=/attempt/moving_selected.json /attempt/probe_build/moving_probe --ros-args --params-file /version/building_planner.yaml > /attempt/moving_selected.log 2>&1
mv /attempt/neighborhoods.json /attempt/moving_selected_neighborhoods.json
env VLA_DIAGNOSTIC_PHYSICAL_GROUND=1 VLA_GEOMETRY_INPUT=/moving VLA_GEOMETRY_OUTPUT=/attempt/moving_physical.json /attempt/probe_build/moving_probe --ros-args --params-file /version/building_planner.yaml > /attempt/moving_physical.log 2>&1
mv /attempt/neighborhoods.json /attempt/moving_physical_neighborhoods.json
env VLA_DIAGNOSTIC_PHYSICAL_GROUND=1 VLA_GEOMETRY_INPUT=/moving VLA_GEOMETRY_OUTPUT=/attempt/moving_physical_repeat.json /attempt/probe_build/moving_probe --ros-args --params-file /version/building_planner.yaml > /attempt/moving_physical_repeat.log 2>&1
mv /attempt/neighborhoods.json /attempt/moving_physical_repeat_neighborhoods.json
env VLA_GEOMETRY_INPUT=/v5input VLA_GEOMETRY_OUTPUT=/attempt/v5_fixed.json VLA_QUERY_DIAGNOSTICS=1 /attempt/probe_build/height_probe --ros-args --params-file /v5audit/replay_inputs/planner.yaml > /attempt/v5_fixed.log 2>&1
env VLA_GEOMETRY_INPUT=/v5input VLA_GEOMETRY_OUTPUT=/attempt/v5_height.json VLA_QUERY_DIAGNOSTICS=1 /attempt/probe_build/height_probe --ros-args --params-file /v5version/building_planner.yaml > /attempt/v5_height.log 2>&1
