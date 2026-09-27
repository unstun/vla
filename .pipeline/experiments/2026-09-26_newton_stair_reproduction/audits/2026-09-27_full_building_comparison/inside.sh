set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
python3 /attempt/prepare_inputs.py /base /attempt
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j2
for trial in 01 02; do
 env VLA_GEOMETRY_INPUT=/attempt/inputs VLA_GEOMETRY_OUTPUT=/attempt/replay${trial}.json /attempt/probe_build/frontier_probe --ros-args --params-file /attempt/inputs/planner.yaml > /attempt/replay${trial}.log 2>&1
done
