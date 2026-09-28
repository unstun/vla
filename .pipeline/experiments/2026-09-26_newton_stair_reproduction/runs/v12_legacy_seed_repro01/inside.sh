set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
python3 /audit/prepare_inputs.py /base /audit
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j2
env VLA_GEOMETRY_INPUT=/audit/inputs VLA_GEOMETRY_OUTPUT=/attempt/result.json /attempt/probe_build/frontier_probe --ros-args --params-file /audit/inputs/planner.yaml > /attempt/repro.log 2>&1
