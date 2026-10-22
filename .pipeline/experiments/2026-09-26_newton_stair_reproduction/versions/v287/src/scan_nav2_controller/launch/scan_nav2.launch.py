"""Start the native SCAN controller plugin; no actuator or stop-proof generator."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    parameters = PathJoinSubstitution([
        FindPackageShare("scan_nav2_controller"), "config", "controller.yaml"])
    configured_parameters = RewrittenYaml(
        source_file=parameters, convert_types=True,
        param_rewrites={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "native_planner_config": LaunchConfiguration("native_planner_config"),
        })
    return LaunchDescription([
        DeclareLaunchArgument("native_planner_config"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        Node(package="nav2_controller", executable="controller_server", output="screen",
             parameters=[configured_parameters], remappings=[("cmd_vel", "/quad_0/cmd_vel")]),
        Node(package="nav2_lifecycle_manager", executable="lifecycle_manager",
             name="lifecycle_manager_scan", output="screen",
             parameters=[{"autostart": True, "node_names": ["controller_server"],
                          "use_sim_time": LaunchConfiguration("use_sim_time")}]),
    ])
