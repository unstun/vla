"""Reuse installed launch/profile; append the frozen v244 opt-in PCT binding."""
from pathlib import Path
import importlib.util,yaml
from ament_index_python.packages import get_package_share_directory
FROZEN=Path(get_package_share_directory('lite3_nav2_bridge'))/'launch/navigation.launch.py'
spec=importlib.util.spec_from_file_location('v232_original_navigation_launch',FROZEN)
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
write_original=original.write_profile

def write_profile(*args,**kwargs):
 path=write_original(*args,**kwargs)
 data=yaml.safe_load(Path(path).read_text())
 data['planner_server']['ros__parameters']['PCT'].update(
  endpoint_recovery=True,static_body_path='/task/environment_score_v224/fixtures/building/environment03.env',
  static_body_fnv64='4316416882194453309',support_gap_path='/work/fixtures/building/support_gap.txt',
  support_gap_fnv64='10479033888964413526')
 Path(path).write_text(yaml.safe_dump(data));return path
original.write_profile=write_profile
generate_launch_description=original.generate_launch_description
