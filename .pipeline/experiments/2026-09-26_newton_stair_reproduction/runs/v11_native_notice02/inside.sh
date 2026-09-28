set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_NOTICE_OUTPUT=/second/result.json /attempt/probe_build/failure_probe --ros-args --params-file /version/building_planner.yaml
