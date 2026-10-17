import importlib.util
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext
from unittest.mock import patch
from lite3_nav2_bridge.profile import write_profile
from lite3_nav2_bridge.terrain_bundle import TerrainBundle

MANIFEST = Path(os.environ['TERRAIN_TEST_MANIFEST'])
NATIVE = Path(os.environ['TERRAIN_NATIVE_CONFIG'])


@pytest.mark.parametrize('frame', ['base', 'base_link'])
def test_profile_retains_scan_geometry_and_removes_map_work(tmp_path, frame):
    target = tmp_path/'profile.yaml'
    original = yaml.safe_load(NATIVE.read_text())['scan_planner_node']['ros__parameters']
    write_profile(target,NATIVE,False,terrain_manifest=MANIFEST,base_frame=frame)
    data = yaml.safe_load(target.read_text())
    for name in ['global_costmap','local_costmap']:
        parameters = data[name][name]['ros__parameters']
        assert parameters['plugins'] == ['map_shell']
        assert parameters['map_shell']['enabled'] is False
        assert parameters['map_shell']['observation_sources'] == ''
        assert 'terrain_layer' not in parameters and 'inflation_layer' not in parameters
        assert parameters['update_frequency'] == 1 and parameters['publish_frequency'] == 0
        assert parameters['robot_base_frame'] == frame and parameters['global_frame'] == 'world'
        assert parameters['width'] == parameters['height'] == parameters['resolution'] == 1
    native = yaml.safe_load(target.with_suffix('.scan.yaml').read_text())['scan_planner_node']['ros__parameters']
    rebound = TerrainBundle(MANIFEST).native_parameters()
    assert all(native[k] == v for k,v in original.items() if k not in rebound and k != 'use_sim_time')
    assert all(native[k] == v for k,v in rebound.items())
    assert data['planner_server']['ros__parameters']['PCT']['map_bundle'] == str(MANIFEST.parent/'route.pct')
    assert data['recoveries_server']['ros__parameters']['recovery_plugins'] == ['wait']
    tree = ET.parse(target.with_suffix('.bt.xml'))
    assert tree.find('.//Wait').get('wait_duration') == '1'
    assert tree.find('.//RecoveryNode').get('number_of_retries') == '6'
    assert tree.find('.//RateController').get('hz') == '1.0'  # Step 5 is separate.
    with pytest.raises(ValueError): write_profile(target,NATIVE,False,terrain_manifest=MANIFEST)


def test_launch_owns_one_static_publisher_and_wait_recovery_server(tmp_path):
    launch_file = Path(get_package_share_directory('lite3_nav2_bridge'))/'launch/navigation.launch.py'
    spec = importlib.util.spec_from_file_location('terrain_launch',launch_file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    backend = tmp_path/'backend.json'; backend.write_text('{}')
    context = LaunchContext()
    context.launch_configurations.update({'terrain_manifest':str(MANIFEST), 'native_planner_config':str(NATIVE),
        'generated_params':str(tmp_path/'profile.yaml'), 'backend_config':str(backend),
        'use_sim_time':'false','base_frame':'base','odom_topic':'/quad_0/body_pose'})
    with patch.object(module, 'Node', side_effect=lambda **kwargs: kwargs):
        actions = module.nodes(context)
    names = [action['executable'] for action in actions]
    assert names == ['static_terrain','mission_bridge','controller_server','planner_server','recoveries_server','bt_navigator','lifecycle_manager']
