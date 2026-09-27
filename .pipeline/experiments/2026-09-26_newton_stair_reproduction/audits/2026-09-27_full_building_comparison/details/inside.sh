set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/details/probe_source -B /attempt/details/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/details/probe_build -j2
env VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/details/replay.json /attempt/details/probe_build/frontier_probe --ros-args --params-file /attempt/inputs/planner.yaml > /attempt/details/replay.log 2>&1
