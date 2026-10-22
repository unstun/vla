"""Verify the actual v254 overlay and frozen v248 bridge with inherited v232 interfaces before physics."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_prefix

HERE = Path(__file__).resolve().parent
root = Path('/work')
rebuilt = {'plan_env','path_searching','bspline_opt','scan_planner','scan_nav2_controller','lite3_nav2_plugins','pct_planner'}
inherited = {'lite3_nav2_interfaces','lite3_nav2_bridge'}
reference = json.loads((HERE.parent/'v237/results/preflight01/native_preflight.json').read_text())['packages']
packages = {ET.parse(p).getroot().findtext('name'): get_package_prefix(ET.parse(p).getroot().findtext('name')) for p in (root/'src').glob('*/package.xml')}
assert len(packages) == 14
for name, prefix in packages.items():
    expected = '/work/install/'+name if name in rebuilt else '/task/physical_traversability_v248/native/install/lite3_nav2_bridge' if name=='lite3_nav2_bridge' else '/task/callback_failure_v232/install/'+name if name in inherited else reference[name]
    assert prefix == expected, (name, prefix, expected)
files = {}
for name in rebuilt | inherited:
    for p in (Path(packages[name])/'lib').rglob('*.so'):
        assert 'not found' not in subprocess.check_output(['ldd', str(p)], text=True), p
        files[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
library = Path('/work/install/scan_planner/lib/libscan_native_core.so')
symbols = subprocess.check_output(['nm','-D','-C',str(library)],text=True)
assert 'GridMap::refreshSensorInputs(char const*, int, bool)' in symbols
assert 'GridMap::refreshSensorInputs(char const*, int)' in symbols
assert b'astar_inputs_changed' in library.read_bytes()
linked = subprocess.check_output(['ldd', str(Path('/work/install/scan_nav2_controller/lib/libscan_nav2_controller.so'))], text=True)
assert 'libscan_native_core.so => /work/install/scan_planner/lib/' in linked
from lite3_nav2_interfaces.srv import RouteSession, FollowPathFailure, CheckTraversability
assert 'source_identity' in CheckTraversability.Response.get_fields_and_field_types()
import lite3_nav2_bridge.mission_bridge as mission
import lite3_nav2_bridge.runtime_failure as failure
for module in (mission, failure):
    assert str(module.__file__).startswith('/task/physical_traversability_v248/native/install/lite3_nav2_bridge/')
sys.path.insert(0,str(HERE.parent/'v198/runtime/bridge'))
import lite3_sim_bridge.execution_state
print(json.dumps(dict(passed=True,packages=packages,rebuilt_packages=sorted(rebuilt),inherited_v240_packages=[],
    inherited_v232_packages=sorted(inherited),installed_binaries=files,
    loaded_native_library=str(library),old_and_new_refresh_abi_present=True,
    controller_linked_to_v254_core=True,physics_steps=0),indent=2))
