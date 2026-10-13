"""Launch truthful live Lite3 path/pose visualization for native Foxy RViz."""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _launch_nodes(context):
    urdf_path = Path(LaunchConfiguration("robot_urdf_path").perform(context))
    if not urdf_path.is_file():
        raise FileNotFoundError(urdf_path)
    source_description = urdf_path.read_text(encoding="utf-8")
    relative_mesh_prefix = 'filename="./meshes/'
    if relative_mesh_prefix not in source_description:
        raise ValueError("Lite3 URDF does not contain the expected relative mesh prefix")
    absolute_mesh_prefix = 'filename="file://{}/meshes/'.format(urdf_path.parent)
    robot_description = source_description.replace(
        relative_mesh_prefix, absolute_mesh_prefix
    )

    return [
        # Start the observation-only live-cloud audit before the heavier URDF
        # publisher so the short preflight does not lose its startup scans.
        Node(
            package="lite3_sim_bridge",
            executable="rviz_replay_node",
            name="lite3_native_rviz_review",
            output="screen",
            parameters=[
                {
                    "source_mode": "live",
                    "frame_id": "world",
                    "robot_root_frame": "TORSO",
                    "sample_count": 160,
                    "audit_path": LaunchConfiguration("audit_path"),
                    "preload_first_snapshot": False,
                    "require_live_lidar": True,
                }
            ],
        ),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="lite3_robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_description}],
            remappings=[("joint_states", "/quad_0/joint_states")],
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("robot_urdf_path"),
            DeclareLaunchArgument("audit_path"),
            OpaqueFunction(function=_launch_nodes),
        ]
    )
