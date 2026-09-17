"""Launch P2B SCAN, bridge and backend ROS/HTTP binding.

All config paths are explicit launch arguments so the lead-owned pilot can pass
frozen absolute files from p2b_execution/baseline_config and run artifacts.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    backend_config = LaunchConfiguration("backend_config")
    planner_config = LaunchConfiguration("planner_config")
    controller_config = LaunchConfiguration("controller_config")
    bridge_config = LaunchConfiguration("bridge_config")
    run_id = LaunchConfiguration("run_id")
    run_epoch_ns = LaunchConfiguration("run_epoch_ns")
    applied_snapshot = LaunchConfiguration("applied_snapshot")
    finish_request = LaunchConfiguration("finish_request")
    pct_port = LaunchConfiguration("pct_port")
    http_port = LaunchConfiguration("http_port")
    start_bridge = LaunchConfiguration("start_bridge")

    return LaunchDescription([
        DeclareLaunchArgument("backend_config"),
        DeclareLaunchArgument("planner_config"),
        DeclareLaunchArgument("controller_config"),
        DeclareLaunchArgument("bridge_config"),
        DeclareLaunchArgument("run_id"),
        DeclareLaunchArgument("run_epoch_ns"),
        DeclareLaunchArgument("applied_snapshot"),
        DeclareLaunchArgument("finish_request"),
        DeclareLaunchArgument("pct_port", default_value="47631"),
        DeclareLaunchArgument("http_port", default_value="8765"),
        DeclareLaunchArgument("start_bridge", default_value="true"),
        Node(
            package="scan_planner",
            executable="scan_planner_node",
            name="scan_planner_node",
            output="screen",
            parameters=[planner_config],
            remappings=[
                ("body_pose", "/quad_0/body_pose"),
                ("sensor_pose", "/quad_0/lidar_pose"),
                ("cloud", "/quad_0/cloud"),
            ],
        ),
        Node(
            package="scan_planner",
            executable="closed_loop_controller",
            name="closed_loop_controller",
            output="screen",
            parameters=[controller_config],
            remappings=[
                ("body_pose", "/quad_0/body_pose"),
            ],
        ),
        ExecuteProcess(
            condition=IfCondition(start_bridge),
            cmd=[
                "python3",
                "-c",
                "from lite3_sim_bridge.foxy_bridge_node import main; main()",
                "--ros-args",
                "--params-file",
                bridge_config,
            ],
            name="lite3_sim_bridge",
            output="screen",
        ),
        Node(
            package="p2b_backend_ros",
            executable="p2b_backend_ros",
            name="p2b_backend_ros",
            output="screen",
            arguments=[
                "--config", backend_config,
                "--run-id", run_id,
                "--run-epoch-ns", run_epoch_ns,
                "--applied-snapshot", applied_snapshot,
                "--finish-request", finish_request,
                "--pct-port", pct_port,
                "--http-port", http_port,
            ],
        ),
    ])
