set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
env VLA_DIAGNOSTIC_SHARED_HEADING=1 VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/replay.json /probe/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml -p manager.use_upstream_search_plane:=false > /attempt/replay.log 2>&1
