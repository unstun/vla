set -eo pipefail
source /opt/ros/foxy/setup.bash
source /workspace/install/setup.bash
export ROS_DOMAIN_ID=94
export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/backend_ros:/backend_adapter:/bridge:${PYTHONPATH:-}
ros2 run scan_planner scan_planner_node --ros-args --params-file /config/planner.yaml -r body_pose:=/quad_0/body_pose -r sensor_pose:=/quad_0/lidar_pose -r cloud:=/quad_0/cloud > /logs/scan_planner_node.log 2>&1 &
scan_pid=$!
ros2 run scan_planner closed_loop_controller --ros-args --params-file /config/controller.yaml -r body_pose:=/quad_0/body_pose > /logs/closed_loop_controller.log 2>&1 &
controller_pid=$!
cleanup() {
  kill "$scan_pid" "$controller_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
python3 -m p2b_backend_ros.node --config /config/p2b_backend_ros.two_goal.resolved.json --run-id cpu-preflight --run-epoch-ns 123456789 --applied-snapshot /preflight/current_command.json --finish-request /preflight/finish_request.json --pct-port 47631 --http-port 8765
