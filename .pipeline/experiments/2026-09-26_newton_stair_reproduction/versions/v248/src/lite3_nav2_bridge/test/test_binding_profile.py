"""The actual case launch emits the new map/support and ACTIVE gate."""
from pathlib import Path
import importlib.util,json,os
from unittest.mock import patch
import yaml
from launch import LaunchContext


def test_actual_launch_binds_physical_support_and_active_gate(tmp_path):
 source=Path(os.environ['V248_SOURCE'])/'navigation_physical.launch.py'
 spec=importlib.util.spec_from_file_location('physical_launch',source)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 base=Path('/task/physical_traversability_v247/native/fixtures')
 config=tmp_path/'backend.json';config.write_text(json.dumps({'run_id':'unit','run_epoch_ns':42,'map':{'nominal_body_height_m':.3}}))
 context=LaunchContext();context.launch_configurations.update(dict(use_sim_time='false',base_frame='base',odom_topic='/quad_0/body_pose',generated_params=str(tmp_path/'params.yaml'),terrain_manifest=str(base/'building/terrain247.json'),environmental_manifest=str(base/'building/environment247.json'),backend_config=str(config),native_planner_config=str(base/'building_planner.yaml')))
 with patch.object(module,'node_original',side_effect=lambda **kw:kw),patch.object(module.original,'OnProcessExit',side_effect=lambda **kw:kw),patch.object(module.original,'RegisterEventHandler',side_effect=lambda action:{'monitor':action}):
  actions=module.original.nodes(context)
 bridge=next(a for a in actions if a.get('executable')=='mission_bridge')
 assert any(p.get('require_active_navigation') is True for p in bridge['parameters'])
 parameters=yaml.safe_load((tmp_path/'params.yaml').read_text())
 pct=parameters['planner_server']['ros__parameters']['PCT']
 assert pct['map_bundle']==str(base/'building/native_original.pct')
 assert pct['static_support_path']=='/work/fixtures/building/native.support'
 assert pct['static_support_fnv64']=='1404261889151999461'
 assert 'endpoint_recovery' not in pct and 'static_body_path' not in pct
 assert pct['reference_height']==.3 and pct['shared_traversability'] is True
