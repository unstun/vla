set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/counterfactual/probe_source -B /attempt/counterfactual/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/counterfactual/probe_build -j2
env VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/counterfactual/replay.json /attempt/counterfactual/probe_build/frontier_probe --ros-args --params-file /attempt/inputs/planner.yaml > /attempt/counterfactual/replay.log 2>&1
