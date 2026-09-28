set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j1
ulimit -v 1500000
env VLA_GEOMETRY_INPUT=/expired VLA_GEOMETRY_OUTPUT=/attempt/expired01.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /attempt/expired01.log 2>&1
env VLA_GEOMETRY_INPUT=/expired VLA_GEOMETRY_OUTPUT=/attempt/expired02.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /attempt/expired02.log 2>&1
env VLA_GEOMETRY_INPUT=/original VLA_GEOMETRY_OUTPUT=/attempt/original66.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml > /attempt/original66.log 2>&1
