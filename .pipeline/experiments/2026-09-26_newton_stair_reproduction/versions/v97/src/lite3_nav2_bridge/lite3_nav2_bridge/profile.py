"""Compose the pinned Foxy package defaults with explicit Lite3 overrides."""
from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory


def write_profile(output, native_config, use_sim_time, *, external_planner=False,
                  base_frame='base_link', odom_topic='/odom'):
    output = Path(output)
    if output.exists():
        raise ValueError('Refuse to overwrite a previous launch profile')
    native_config = Path(native_config).resolve(strict=True)
    bringup = Path(get_package_share_directory('nav2_bringup'))
    candidates = list(bringup.rglob('nav2_params.yaml'))
    if len(candidates) != 1:
        raise RuntimeError('Foxy default parameters missing or ambiguous')
    data = yaml.safe_load(candidates[0].read_text())
    scan = Path(get_package_share_directory('scan_nav2_controller'))
    data.update(yaml.safe_load((scan/'config/controller.yaml').read_text()))
    controller = data['controller_server']['ros__parameters']
    controller['SCAN'].update(native_planner_config=str(native_config), native_worker_enabled=not external_planner)
    controller['SCAN']['base_frame'] = base_frame
    controller['odom_topic'] = odom_topic
    # The unchanged simple progress checker detects a stuck robot independently
    # of solver activity. No timeout is increased to hide mapper stalls.
    for key in ('global_costmap', 'local_costmap'):
        data[key] = {key: {'ros__parameters': {
            'global_frame': 'world', 'robot_base_frame': base_frame,
            'rolling_window': True, 'width': 6, 'height': 6, 'resolution': 0.1,
            'track_unknown_space': True, 'update_frequency': 10.0, 'publish_frequency': 2.0,
            'robot_radius': 0.25, 'plugins': ['terrain_layer', 'inflation_layer'],
            'terrain_layer': {'plugin': 'lite3_nav2/TerrainLayer', 'base_frame':base_frame},
            'inflation_layer': {'plugin': 'nav2_costmap_2d::InflationLayer',
                                'inflation_radius': 0.4, 'cost_scaling_factor': 3.0}}}}
    data['planner_server'] = {'ros__parameters': {
        'expected_planner_frequency': 1.0, 'planner_plugins': ['PCT'],
        'PCT': {'plugin': 'lite3_nav2/PCTPlanner', 'service': '/lite3_nav2/plan_route'}}}
    bt = data['bt_navigator']['ros__parameters']
    bt.update(global_frame='world', robot_base_frame=base_frame, odom_topic=odom_topic,
        default_bt_xml_filename=str(Path(get_package_share_directory('lite3_nav2_bridge'))/'config/navigate.xml'))
    bt['plugin_lib_names'].append('lite3_bind_route_bt_node')
    # Foxy's action endpoint remapping does not rename all action services.
    # A real namespace separates the internal action from the public gateway.
    data['/nav2_internal/bt_navigator'] = data.pop('bt_navigator')
    data['/nav2_internal/bt_navigator_rclcpp_node'] = {'ros__parameters': {'use_sim_time': bool(use_sim_time)}}
    def clocks(value):
        if isinstance(value, dict):
            if 'ros__parameters' in value:
                value['ros__parameters']['use_sim_time'] = bool(use_sim_time)
            for child in value.values(): clocks(child)
    clocks(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(data))
    return str(output)
