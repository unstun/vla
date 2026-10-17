"""Bind fresh tests, all package prefixes, effective headers and installed bytes."""
import hashlib
import json
from pathlib import Path
import platform
import shlex
import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_prefix
from source_gate import verify_source
from verify_fresh_tests import verify

HERE = Path(__file__).resolve().parent
WORK = Path('/work')
BINDING = json.loads((HERE / 'binding.json').read_text())
PREFIX = Path(BINDING['remote_root'])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

verify_source(WORK)
assert platform.machine() == 'x86_64'
attempt = BINDING['component_attempt']
request = json.loads((PREFIX / f'evidence/tests{attempt}/request.json').read_text())
tests = verify(WORK, request['started_ns'], 'v234_attempt' + attempt)
prefixes = {}
for path in (WORK / 'src').glob('*/package.xml'):
    name = ET.parse(path).getroot().findtext('name')
    prefixes[name] = get_package_prefix(name)
    assert prefixes[name] == '/work/install/' + name, (name, prefixes[name])
assert len(prefixes) == 14
libraries = {}
for path in (WORK / 'install').rglob('*.so'):
    output = subprocess.check_output(['ldd', str(path)], text=True)
    assert 'not found' not in output, (path, output)
    for line in output.splitlines():
        if any(token in line for token in ('libplan_env.so', 'libbspline_opt.so', 'libscan_native_core.so',
                                          'libscan_nav2_controller.so', 'libpct_route_planner.so')):
            assert '/work/install/' in line, line
    libraries[str(path)] = dict(sha256=sha(path), ldd=output)
headers = {}
for path in (WORK / 'build').glob('*/compile_commands.json'):
    for entry in json.loads(path.read_text()):
        args = shlex.split(entry['command'])
        include, system = [], []
        for index, arg in enumerate(args):
            if arg.startswith('-I') and len(arg) > 2:
                include.append(arg[2:])
            elif arg == '-I':
                include.append(args[index + 1])
            elif arg == '-isystem':
                system.append(args[index + 1])
        for header in ('plan_env/grid_map.h', 'bspline_opt/environmental_curve_cost.h'):
            found = next((Path(p) / header for p in include + system if (Path(p) / header).is_file()), None)
            if found:
                assert str(found).startswith(('/work/src/', '/work/install/')), (entry['file'], header, found)
                headers[entry['file'] + ':' + header] = str(found)
assert len(headers) >= 60, len(headers)
installed = {str(p.relative_to(WORK)): sha(p) for p in (WORK / 'install').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
original = json.loads((HERE.parent / 'v232/results/offline_gate.json').read_text())
missing = sorted(set(original['installed_files']) - installed.keys())
assert not missing, missing
report = dict(passed=True, physics_steps=0, native_packages=14, package_prefixes=prefixes,
              all_package_prefixes_current=True, native_image=BINDING['native_image'],
              original_install_byte_identity=False, original_607_paths_present=True,
              source_identity_sha256=sha(HERE.parent / 'v232/source_identity.json'),
              source_inventory=json.loads((WORK / 'source_inventory.json').read_text()),
              installed_files=installed, modified_header_resolution=headers, native_libraries=libraries,
              unique_test_cases=tests['unique_test_cases'], colcon_records=tests['colcon_records'],
              test_evidence=tests, historical_dynamic_replay_rerun=False)
target = WORK / 'native_rebuild_receipt.json'
assert not target.exists()
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ('passed', 'physics_steps', 'native_packages',
                                       'unique_test_cases', 'colcon_records', 'original_install_byte_identity')}, indent=2))
