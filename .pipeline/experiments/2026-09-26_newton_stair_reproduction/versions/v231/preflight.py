"""Verify actual v230 package, interface and binary bindings before physics."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_prefix
HERE=Path(__file__).resolve().parent
root=Path('/work');rebuilt={'plan_env','path_searching','bspline_opt','scan_planner','pct_planner','lite3_nav2_interfaces','scan_nav2_controller','lite3_nav2_plugins','lite3_nav2_bridge'}
reference=json.loads((HERE.parent/'v219/native_preflight.json').read_text())['packages']
packages={ET.parse(p).getroot().findtext('name'):get_package_prefix(ET.parse(p).getroot().findtext('name')) for p in (root/'src').glob('*/package.xml')}
assert len(packages)==14,packages
for name,prefix in packages.items():
 expected='/work/install/'+name if name in rebuilt else reference[name]
 assert prefix==expected,(name,prefix,expected)
files={}
for name in rebuilt:
 for p in (Path(packages[name])/'lib').rglob('*'):
  if p.is_file() and p.suffix=='.so':
   files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
   assert 'not found' not in subprocess.check_output(['ldd',str(p)],text=True),p
from lite3_nav2_interfaces.srv import RouteSession,FollowPathFailure,CheckTraversability
assert 'source_identity' in CheckTraversability.Response.get_fields_and_field_types()
from lite3_nav2_bridge.mission_bridge import MissionBridge
sys.path.insert(0,str(HERE.parent/'v198/runtime/bridge'))
import lite3_sim_bridge.execution_state
print(json.dumps(dict(passed=True,packages=packages,rebuilt_packages=sorted(rebuilt),loaded_interfaces=['RouteSession','FollowPathFailure','CheckTraversability+source_identity'],installed_binaries=files),indent=2))
