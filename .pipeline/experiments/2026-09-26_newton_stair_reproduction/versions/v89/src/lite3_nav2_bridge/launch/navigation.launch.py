from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from lite3_nav2_bridge.profile import write_profile
from p2b_backend_ros.config import load_runtime_config
from pathlib import Path
import sys


def nodes(context):
    get = lambda name: LaunchConfiguration(name).perform(context)
    use_sim = get('use_sim_time').lower() == 'true'
    profile = write_profile(get('generated_params'), get('native_planner_config'), use_sim)
    backend = load_runtime_config(Path(get('backend_config')))
    import pct_planner
    pct_root = str(Path(pct_planner.__file__).resolve().parents[1])
    pct_map = Path(get('pct_map')).resolve(strict=True)
    worker = backend['pct_worker']
    return [
        ExecuteProcess(cmd=[sys.executable, '-m', 'backend_adapter.pct_worker',
            '--host', worker['host'], '--port', str(worker['port']),
            '--pct-source-root', pct_root, '--rsg-root', str(pct_map.parent),
            '--tomogram-path', str(pct_map),
            '--reference-height-m', str(backend['map']['nominal_body_height_m'])], output='screen'),
        Node(package='lite3_nav2_bridge', executable='mission_gateway', name='lite3_nav2_gateway',
             parameters=[{'config_path': get('backend_config'), 'use_sim_time': use_sim}], output='screen'),
        Node(package='nav2_controller', executable='controller_server', name='controller_server',
             parameters=[profile], output='screen'),
        Node(package='nav2_planner', executable='planner_server', name='planner_server',
             parameters=[profile], output='screen'),
        Node(package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator',
             namespace='nav2_internal', parameters=[profile], output='screen'),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_navigation',
             parameters=[{'use_sim_time': use_sim, 'autostart': True,
                          'node_names': ['controller_server', 'planner_server', '/nav2_internal/bt_navigator']}], output='screen')]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('native_planner_config'), DeclareLaunchArgument('backend_config'),
        DeclareLaunchArgument('pct_map'),
        DeclareLaunchArgument('generated_params'), DeclareLaunchArgument('use_sim_time', default_value='false'),
        OpaqueFunction(function=nodes)])
