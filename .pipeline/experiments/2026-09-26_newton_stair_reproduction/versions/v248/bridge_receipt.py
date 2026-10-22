from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'physical_traversability_v248/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results=HERE/'results';results.mkdir(exist_ok=True)
for p in (HERE/'src').rglob('*'):
 if p.is_file():assert sha(p)==sha(WORK/p.relative_to(HERE)),str(p)
root=ET.parse(WORK/'readiness_tests.xml').getroot()
assert all(int(p.get('failures',0))==0 and int(p.get('errors',0))==0 for p in root.iter('testsuite'))
assert sum(int(p.get('tests',0)) for p in root.iter('testsuite'))>=24
installed_mission=list((WORK/'install/lite3_nav2_bridge').rglob('mission_bridge.py'))
assert len(installed_mission)==1 and sha(installed_mission[0])==sha(HERE/'src/lite3_nav2_bridge/lite3_nav2_bridge/mission_bridge.py')
files={str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts}
(results/'bridge_installed_files.json').write_text(json.dumps(files,indent=2)+'\n')
shutil.copy2(WORK/'source_inventory.json',results/'source_inventory.json');shutil.copy2(WORK/'readiness_tests.xml',results/'readiness_tests.xml')
for name in ('v248_build01.log','v248_tests01.log','v248_tests02.log'):
 p=BASE/name
 if p.exists():shutil.copy2(p,results/name)
print(json.dumps(dict(passed=True,bridge_installed_files=len(files),readiness_test_cases=sum(int(p.get('tests',0)) for p in root.iter('testsuite')),native_parent='v247')),flush=True)
