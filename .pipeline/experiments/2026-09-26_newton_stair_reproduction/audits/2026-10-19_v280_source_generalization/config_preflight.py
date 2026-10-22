"""Actual profile generation and numerical/source checks without starting nodes."""
from pathlib import Path
import importlib.util,json,shutil,os
from unittest.mock import patch
from launch import LaunchContext
HERE=Path('/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v282')
tag=os.environ['CONFIG_PREFLIGHT_TAG'];assert tag.isdigit()
OUT=Path('/audit')/('configuration'+tag);OUT.mkdir(exist_ok=False)
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module=load(HERE/'navigation_physical.launch.py','actual_v282_profile')
base=Path('/work/fixtures');config=OUT/'backend_config.json';config.write_text(json.dumps(dict(run_id='configuration_only',run_epoch_ns=42,map=dict(nominal_body_height_m=.3))))
shutil.copy2(HERE.parent/'v196/building_planner.yaml',OUT/'planner.yaml')
ctx=LaunchContext();ctx.launch_configurations.update(dict(use_sim_time='false',base_frame='base',odom_topic='/quad_0/body_pose',generated_params=str(OUT/'nav2_params.yaml'),terrain_manifest=str(base/'building/terrain282.json'),environmental_manifest=str(base/'building/environment282.json'),backend_config=str(config),native_planner_config=str(OUT/'planner.yaml')))
with patch.object(module,'node_original',side_effect=lambda **kw:kw),patch.object(module.original,'OnProcessExit',side_effect=lambda **kw:kw),patch.object(module.original,'RegisterEventHandler',side_effect=lambda action:{'monitor':action}):
 actions=module.original.nodes(ctx)
bridge=next(a for a in actions if a.get('executable')=='mission_bridge');assert any(p.get('require_active_navigation') is True for p in bridge['parameters'])
verify=load(HERE/'verify_profile.py','v282_numerical_verifier').verify
report=verify(OUT);report.update(processes_started=0,physics_steps=0,lifecycle_active_claim=False,scope='Actual profile generation; node construction mocked only to avoid launching processes')
(OUT/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,physics_steps=0,processes_started=0)))
