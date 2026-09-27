set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j2
env VLA_GEOMETRY_INPUT=/inputs VLA_GEOMETRY_OUTPUT=/attempt/retime.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/flat_planner.yaml > /attempt/native.log 2>&1
