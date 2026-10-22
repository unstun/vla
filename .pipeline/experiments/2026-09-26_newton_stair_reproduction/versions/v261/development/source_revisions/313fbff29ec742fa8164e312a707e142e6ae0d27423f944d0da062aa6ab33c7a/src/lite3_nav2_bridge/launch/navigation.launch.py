from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from lite3_nav2_bridge.runtime_failure import critical_exit_handler
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from lite3_nav2_bridge.profile import write_profile
from pathlib import Path
import json


def nodes(context):
    get = lambda name: LaunchConfiguration(name).perform(context)
    use_sim = get('use_sim_time').lower() == 'true'
    backend = json.loads(Path(get('backend_config')).read_text())
    profile = write_profile(get('generated_params'), get('native_planner_config'), use_sim,
                            terrain_manifest=get('terrain_manifest'),
                            environmental_manifest=LaunchConfiguration('environmental_manifest', default='').perform(context) or None,
                            reference_height_m=backend.get('map', {}).get('nominal_body_height_m', 0.35),
                            base_frame=get('base_frame'),odom_topic=get('odom_topic'))
    failure_path=str(Path(get('generated_params')).parent/'native_process_failure.json')
    actions = [
        Node(package='lite3_nav2_bridge', executable='static_terrain', name='static_terrain',
             parameters=[{'terrain_manifest': get('terrain_manifest'), 'use_sim_time': use_sim}], output='screen'),
        Node(package='lite3_nav2_bridge', executable='mission_bridge', name='lite3_nav2_mission_bridge',
             parameters=[{'config_path': get('backend_config'),
                          'odom_topic': get('odom_topic'), 'use_sim_time': use_sim,
                          'native_process_failure_path': failure_path,
                          'critical_liveness_timeout_s': 1.0}], output='screen'),
        Node(package='nav2_controller', executable='controller_server', name='controller_server',
             parameters=[profile], remappings=[('cmd_vel', '/quad_0/cmd_vel')], output='screen'),
        Node(package='nav2_planner', executable='planner_server', name='planner_server',
             parameters=[profile], output='screen'),
        Node(package='nav2_recoveries', executable='recoveries_server', name='recoveries_server',
             parameters=[profile], output='screen'),
        Node(package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator',
             namespace='nav2_internal', parameters=[profile], output='screen'),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_navigation',
             parameters=[{'use_sim_time': use_sim, 'autostart': True,
                          'node_names': ['controller_server', 'planner_server', 'recoveries_server',
                                         '/nav2_internal/bt_navigator']}], output='screen')]
    # Attach to actual ROS children; the ros2 launch parent may remain alive.
    components=('static_terrain','mission_bridge','controller_server','planner_server',
                'recoveries_server','bt_navigator','lifecycle_manager_navigation')
    monitors=[RegisterEventHandler(OnProcessExit(target_action=action,
        on_exit=critical_exit_handler(failure_path,backend.get('run_id',''),backend.get('run_epoch_ns',0),component)))
        for component,action in zip(components,actions)]
    return monitors+actions



def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('native_planner_config'), DeclareLaunchArgument('backend_config'),
        DeclareLaunchArgument('terrain_manifest'),
        DeclareLaunchArgument('environmental_manifest', default_value=''),
        DeclareLaunchArgument('base_frame',default_value='base_link'),
        DeclareLaunchArgument('odom_topic',default_value='/quad_0/body_pose'),
        DeclareLaunchArgument('generated_params'), DeclareLaunchArgument('use_sim_time', default_value='false'),
        OpaqueFunction(function=nodes)])
