"""Collect existing build results; never start a navigation or physics process."""
import hashlib
import json
import platform
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path('/work')
output = root / 'evidence'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected = json.loads((root / 'source_inventory.json').read_text())
for name, digest in expected.items():
    assert sha(root / name) == digest, name
cases = []
result_files = {}
(output / 'test_results').mkdir(exist_ok=True)
for path in sorted((root / 'build').glob('*/test_results/**/*.xml')):
    doc = ET.parse(path).getroot()
    for case in doc.iter('testcase'):
        assert case.find('failure') is None and case.find('error') is None, case.attrib
        cases.append({'suite': path.name, 'name': case.attrib['name'],
                      'skipped': case.find('skipped') is not None})
    shutil.copyfile(path, output / 'test_results' / path.name)
    result_files[path.name] = sha(path)
libraries = [root / 'install/scan_nav2_controller/lib/libscan_nav2_controller.so',
             root / 'install/scan_planner/lib/libscan_native_core.so',
             root / 'install/nav2_controller/lib/nav2_controller/controller_server']
library_record = {}
for path in libraries:
    if not path.exists():
        raise RuntimeError('Missing expected installed library: ' + str(path))
    dependency = subprocess.check_output(['ldd', str(path)], text=True)
    assert 'not found' not in dependency, dependency
    for line in dependency.splitlines():
        if any(name in line for name in ['libscan_native_core', 'libscan_nav2_controller',
                                         'libplan_env', 'libbspline_opt', 'libpath_searching']):
            assert '/work/install/' in line, line
    library_record[str(path.relative_to(root))] = {
        'sha256': sha(path), 'bytes': path.stat().st_size, 'ldd': dependency,
        'elf': subprocess.check_output(['readelf', '-h', str(path)], text=True)}
receipt = {'version': 'v206', 'host': 'gpu5070ti', 'architecture': platform.machine(),
           'image_id': (root / 'image_id.txt').read_text().strip(),
           'source_files_verified': len(expected), 'source_inventory': expected,
           'unique_cases': len(cases), 'failures': 0,
           'skipped': sum(c['skipped'] for c in cases), 'test_cases': cases,
           'test_xml_sha256': result_files, 'installed_libraries': library_record,
           'physical_steps': 0, 'local_compilation': False}
(output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
manifest = {str(p.relative_to(output)): sha(p) for p in output.rglob('*')
            if p.is_file() and p.name != 'return_manifest.json'}
(output / 'return_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ['version','architecture','source_files_verified',
                                      'unique_cases','failures','skipped','image_id']}))
