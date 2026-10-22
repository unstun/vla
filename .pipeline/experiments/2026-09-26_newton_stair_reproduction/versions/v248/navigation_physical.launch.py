"""Bind one native support field and require actual navigation ACTIVE."""
from pathlib import Path
import importlib.util,yaml
from ament_index_python.packages import get_package_share_directory
FROZEN=Path(get_package_share_directory('lite3_nav2_bridge'))/'launch/navigation.launch.py'
spec=importlib.util.spec_from_file_location('original_navigation_launch',FROZEN)
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
write_original=original.write_profile
node_original=original.Node

def write_profile(*args,**kwargs):
 path=write_original(*args,**kwargs);data=yaml.safe_load(Path(path).read_text())
 data['planner_server']['ros__parameters']['PCT'].update(static_support_path='/work/fixtures/building/native.support',static_support_fnv64='1404261889151999461')
 Path(path).write_text(yaml.safe_dump(data));return path

def node(*args,**kwargs):
 if kwargs.get('executable')=='mission_bridge':
  kwargs['parameters']=list(kwargs.get('parameters',[]))+[{'require_active_navigation':True}]
 return node_original(*args,**kwargs)
original.write_profile=write_profile;original.Node=node
generate_launch_description=original.generate_launch_description
