"""One pinned solid/support source for global and native static admission."""
from pathlib import Path
import hashlib,importlib.util,json,yaml
from ament_index_python.packages import get_package_share_directory
FROZEN=Path(get_package_share_directory('lite3_nav2_bridge'))/'launch/navigation.launch.py'
spec=importlib.util.spec_from_file_location('original_navigation_launch',FROZEN)
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
write_original=original.write_profile;node_original=original.Node
STACK_DIR=None

def write_profile(*args,**kwargs):
 global STACK_DIR
 path=write_original(*args,**kwargs);data=yaml.safe_load(Path(path).read_text())
 metadata=json.loads(Path('/work/fixtures/building/source_surface282.json').read_text())
 field=(Path('/work/fixtures/building')/metadata['file']).resolve();assert metadata['format']=='SURFACE271B'
 assert hashlib.sha256(field.read_bytes()).hexdigest()==metadata['sha256']
 solid=dict(static_solid_path=str(field),static_solid_fnv64=metadata['fnv64'])
 data['planner_server']['ros__parameters']['PCT'].update(static_support_path='/work/fixtures/building/native.support',static_support_fnv64='15212154834549674106',**solid)
 native_path=Path(path).with_suffix('.scan.yaml');native=yaml.safe_load(native_path.read_text())
 section='/quad_0/scan_planner_node' if '/quad_0/scan_planner_node' in native else 'scan_planner_node'
 native[section]['ros__parameters'].update({'grid_map.'+k:v for k,v in solid.items()})
 native_path.write_text(yaml.safe_dump(native));Path(path).write_text(yaml.safe_dump(data))
 STACK_DIR=Path(path).parent/'native_backtraces';STACK_DIR.mkdir(exist_ok=True)
 return path

def node(*args,**kwargs):
 if kwargs.get('executable')=='mission_bridge':kwargs['parameters']=list(kwargs.get('parameters',[]))+[{'require_active_navigation':True}]
 environment=dict(kwargs.get('additional_env',{}),PYTHONFAULTHANDLER='1')
 if kwargs.get('executable') in ('controller_server','planner_server','recoveries_server','bt_navigator','lifecycle_manager'):
  assert STACK_DIR is not None
  environment['V287_BACKTRACE_DIR']=str(STACK_DIR)
  kwargs['prefix']=['/usr/bin/python3 '+str(Path(__file__).with_name('native_debugger.py'))]
 kwargs['additional_env']=environment
 return node_original(*args,**kwargs)
original.write_profile=write_profile;original.Node=node
generate_launch_description=original.generate_launch_description
