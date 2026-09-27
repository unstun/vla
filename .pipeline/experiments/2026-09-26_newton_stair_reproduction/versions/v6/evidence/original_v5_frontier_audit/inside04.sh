set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
python3 /audit/prepare_inputs04.py /base /audit
cmake -S /audit/probe_source -B /audit/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /audit/probe_build -j2
env VLA_GEOMETRY_INPUT=/audit/inputs04 VLA_GEOMETRY_OUTPUT=/audit/baseline01.json VLA_QUERY_DIAGNOSTICS=1 /audit/probe_build/frontier_probe --ros-args --params-file /audit/inputs04/planner.yaml > /audit/baseline01.log 2>&1
env VLA_GEOMETRY_INPUT=/audit/inputs04 VLA_GEOMETRY_OUTPUT=/audit/baseline02.json VLA_QUERY_DIAGNOSTICS=1 /audit/probe_build/frontier_probe --ros-args --params-file /audit/inputs04/planner.yaml > /audit/baseline02.log 2>&1
