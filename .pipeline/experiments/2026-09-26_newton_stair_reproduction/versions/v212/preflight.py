"""Read-only installed-package and dependency check inside the trial container."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_prefix
root=Path('/work');packages={}
for p in (root/'src').glob('*/package.xml'):
 name=ET.parse(p).getroot().findtext('name');packages[name]=get_package_prefix(name)
assert len(packages)==14,packages
owned=['pct_planner','lite3_nav2_interfaces','lite3_nav2_plugins','scan_planner','scan_nav2_controller','nav2_controller','lite3_nav2_bridge']
assert all(packages[n]==('/work/install/' if n in ('lite3_nav2_plugins','lite3_nav2_bridge') else '/task/command_continuity_v206_20261015/install/')+n for n in owned),packages
files={}
for name in owned:
 for p in (Path(packages[name])/'lib').rglob('*'):
  if p.is_file() and (p.suffix=='.so' or p.name in ('controller_server','mission_bridge')):
   files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
   if p.suffix=='.so':
    dependencies=subprocess.check_output(['ldd',str(p)],text=True)
    assert 'not found' not in dependencies,(p,dependencies)
from lite3_nav2_interfaces.srv import RouteSession,FollowPathFailure
from lite3_nav2_bridge.mission_bridge import MissionBridge
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'v198/runtime/bridge'))
import lite3_sim_bridge.execution_state
print(json.dumps(dict(passed=True,packages=packages,loaded_interfaces=['RouteSession','FollowPathFailure'],installed_binaries=files),indent=2))
