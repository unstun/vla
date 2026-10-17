"""Compose the pinned Foxy package defaults with explicit Lite3 overrides."""
from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory


def write_profile(output, native_config, use_sim_time, *, pct_map_bundle, reference_height_m=0.35,
                  external_planner=False,
                  base_frame='base_link', odom_topic='/quad_0/body_pose'):
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
    controller['SCAN']['route_topic'] = '/pct_path'
    # Local curve capture must be tighter than the 5 cm recovery prefix.
    # Final mission goal tolerances remain independently configured.
    controller['SCAN']['finish_dist'] = 0.02
    controller['SCAN']['route_lookahead_heading_enabled'] = True
    controller['SCAN']['route_lookahead_dist'] = 0.5
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
        'PCT': {'plugin': 'lite3_nav2/PCTPlanner',
                'map_bundle': str(Path(pct_map_bundle).resolve(strict=True)),
                'reference_height': float(reference_height_m), 'use_quintic': True, 'max_heading_rate': 10.0}}}
    tree_path=output.with_suffix('.bt.xml')
    if tree_path.exists():raise ValueError('Refuse to overwrite a previous BT profile')
    output.parent.mkdir(parents=True, exist_ok=True)
    tree_path.write_text((Path(get_package_share_directory('lite3_nav2_bridge')) /
                          'config/navigate.xml').read_text())
    bt = data['bt_navigator']['ros__parameters']
    bt.update(global_frame='world', robot_base_frame=base_frame, odom_topic=odom_topic,
        default_bt_xml_filename=str(tree_path))
    # Foxy's action endpoint remapping does not rename all action services.
    # A real namespace separates the internal action from the HTTP mission bridge.
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
