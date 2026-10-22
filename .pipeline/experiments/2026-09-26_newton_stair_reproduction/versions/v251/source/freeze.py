"""Freeze locally owned source and actual offline binaries; no acceptance promotion."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;VERSION=HERE.name;BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/('generic_mechanisms_'+VERSION)/'native'
PARENT={'v249':'v247','v250':'v249','v251':'v250'}[VERSION]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists(),'Frozen versions are immutable'
results=HERE/'results';results.mkdir(exist_ok=True)
inv=json.loads((WORK/'source_inventory.json').read_text())
for rel,h in inv.items():assert sha(WORK/rel)==h,rel
for p in (HERE/'src').rglob('*'):
 if p.is_file():assert sha(p)==sha(WORK/p.relative_to(HERE)),p
shutil.copy2(WORK/'source_inventory.json',results/'source_inventory.json')
installed={str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
(results/'installed_files.json').write_text(json.dumps(installed,indent=2)+'\n')
evaluation=BASE/'generic_mechanisms_v251/evaluation'
evaluators={str(p.relative_to(evaluation)):sha(p) for p in (evaluation/'build').iterdir()
 if p.is_file() and (p.name in ('native_probe','support_probe','graph_probe','baseline_admission') or p.suffix=='.a')}
assert {'build/native_probe','build/support_probe','build/graph_probe'}<=set(evaluators)
(results/'evaluator_files.json').write_text(json.dumps(evaluators,indent=2)+'\n')
fixtures={str(p.relative_to(WORK)):sha(p) for p in (WORK/'fixtures').rglob('*') if p.is_file()}
parent_work=BASE/'generic_mechanisms_v250/native'
parent_fixtures={str(p.relative_to(parent_work)):sha(p) for p in (parent_work/'fixtures').rglob('*') if p.is_file()}
assert fixtures==parent_fixtures,'Runtime fixtures changed from frozen v250'
(results/'fixture_files.json').write_text(json.dumps(fixtures,indent=2)+'\n')
units=results/'pct_unit';units.mkdir(exist_ok=True);count=0
for p in (WORK/'build/lite3_nav2_plugins/test_results').rglob('*.xml'):
 root=ET.parse(p).getroot();assert int(root.get('failures',0))==0 and int(root.get('errors',0))==0,p
 count+=int(root.get('tests',0));shutil.copy2(p,units/p.name)
assert len(list(units.glob('*.xml')))==6
receipt=dict(version=VERSION,parent=PARENT,unit_targets=6,unit_test_cases=count,passed=True,
 source_files=len(inv),installed_files=len(installed),physics_steps=0,
 work=str(WORK),policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',
 hard_radius_m=.35,offset_m=.18,sensor_period_s=.1,claim='Source/build/unit verification; full matrix and physics are separate gates')
(results/'native_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
for rel in files:
 p=HERE/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,p)
manifest=dict(version=VERSION,parent=PARENT,frozen=True,source_files=files,snapshot_locations={r:'source/'+r for r in files},
 parent_manifest_sha256=sha(HERE.parent/PARENT/'manifest.json'),native_receipt_sha256=sha(results/'native_receipt.json'),
 installed_inventory_sha256=sha(results/'installed_files.json'),source_inventory_sha256=sha(results/'source_inventory.json'),
 evaluator_inventory_sha256=sha(results/'evaluator_files.json'),
 fixture_inventory_sha256=sha(results/'fixture_files.json'),
 policy_sha256=receipt['policy_sha256'],hard_collision_support_m=.35,cylinder_offset_m=.18,sensor_period_s=.1,scan_deadline_s=.1,
 cases_manifest_sha256=sha(HERE.parent/'v242/cases_manifest.json'),scope='Offline generic physical mechanism repair; no physical acceptance claim')
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(receipt),flush=True)
