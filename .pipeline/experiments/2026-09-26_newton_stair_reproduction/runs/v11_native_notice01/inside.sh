set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j2
env VLA_NOTICE_OUTPUT=/attempt/result.json /attempt/probe_build/failure_probe --ros-args --params-file /version/building_planner.yaml
