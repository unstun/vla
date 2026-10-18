"""Verify frozen inputs/install and return compact evidence, never build caches."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
TASK=Path('/data/sun/vla_mppi_20261009')
WORK=TASK/'terminal_approach_v238'
PARENT=TASK/'callback_failure_v232'
OUT=HERE/'results';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):(OUT/name).write_text(json.dumps(data,indent=2)+'\n')

parent=json.loads((PARENT/'offline_gate.json').read_text())
for group in ('source_inventory','installed_files'):
    for rel,expected in parent[group].items():assert sha(PARENT/rel)==expected,rel
inventory=json.loads((WORK/'source_inventory.json').read_text())
for rel,expected in inventory.items():assert sha(WORK/rel)==expected,rel
owned={str(p.relative_to(HERE)):sha(p) for p in (HERE/'src').rglob('*') if p.is_file()}
assert inventory==dict(parent['source_inventory'],**owned)
linked=(WORK/'regressions/linked_libraries.txt').read_text()
assert 'libscan_native_core.so => /work/install/scan_planner/lib/' in linked
tests=[]
for p in sorted((WORK/'regressions').glob('*.xml')):
    tree=ET.parse(p);cases=tree.findall('.//testcase')
    assert cases and all(case.find('failure') is None and case.find('error') is None for case in cases),p
    tests.append(dict(name=p.stem,cases=len(cases),sha256=sha(p)))
assert len(tests)==12
shutil.copytree(WORK/'regressions',OUT/'regressions',dirs_exist_ok=True)
for p in (OUT/'regressions').iterdir():
    if p.suffix not in ('.xml','.txt'):p.unlink()
source_log=(WORK/'candidate03.log').read_text()
assert 'BOUNDARY_CONTRACTS passed=4 frame=90' in source_log
reference=re.search(r'REFERENCE_DURATION ([0-9.]+)',source_log)
assert reference and abs(float(reference[1])-78.5743906257)<1e-8
write('native_regressions.json',dict(passed=True,executables=len(tests),test_cases=sum(t['cases'] for t in tests),tests=tests,
    boundary_contracts=4,original_reference_duration_s=float(reference[1]),physics_steps=0))
installed={str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
write('installed_files.json',installed)
write('source_inventory.json',inventory)
shutil.copy2(WORK/'composition.json',OUT/'composition.json')
for arm in ('baseline03','candidate03'):
    shutil.copy2(WORK/arm/'frames.csv',OUT/(arm+'_frames.csv'))
shutil.copy2(WORK/'input02/identity.json',OUT/'replay_input_identity.json')
shutil.copy2(WORK/'build_candidate.log',OUT/'build.log')
artifacts=[WORK/'baseline03.log',WORK/'candidate03.log',WORK/'input02/identity.json',WORK/'build_candidate.log',WORK/'build_baseline03.log',WORK/'build_candidate03.log']
artifacts.extend((WORK/'regressions').glob('*.log'))
write('sync_gate.json',dict(passed=True,parent_source_files_verified=len(parent['source_inventory']),parent_installed_files_unchanged=len(parent['installed_files']),
    candidate_source_files_verified=len(inventory),owned_native_files=len(owned),candidate_installed_files=len(installed),
    loaded_native_library='/work/install/scan_planner/lib/libscan_native_core.so',
    remote_work=str(WORK),host='gpu5070ti',physics_steps=0,
    bulk_artifacts={str(p):dict(sha256=sha(p),bytes=p.stat().st_size) for p in artifacts}))
print(json.dumps(dict(tests=sum(t['cases'] for t in tests),executables=len(tests),boundary_contracts=4,parent_install_unchanged=len(parent['installed_files']),output=str(OUT))))
