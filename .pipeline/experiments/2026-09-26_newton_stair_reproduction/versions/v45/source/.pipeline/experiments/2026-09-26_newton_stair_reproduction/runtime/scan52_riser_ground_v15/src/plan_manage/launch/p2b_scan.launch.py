from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package="scan_planner", executable="scan_planner_node", name="scan_planner_node", output="screen", parameters=["config/planner.yaml"]),
        Node(package="scan_planner", executable="closed_loop_controller", name="closed_loop_controller", output="screen", parameters=["config/controllers.yaml"]),
    ])
