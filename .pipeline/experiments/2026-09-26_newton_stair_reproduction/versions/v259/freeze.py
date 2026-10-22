"""Freeze only after exact original52 equivalence, boundary tests and timing."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'generic_mechanisms_v259/native';OUT=BASE/'generic_mechanisms_v259/evaluation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
gate=json.loads((OUT/'equivalence52/receipt.json').read_text());assert gate['passed'] and gate['equivalent']==52 and gate['admitted']==34
diff=dict(line.split('=',1) for line in (OUT/'differential.txt').read_text().splitlines() if '=' in line)
assert diff['queries']=='70928' and diff['edges']=='5000'
assert all(float(diff[k])==0 for k in ('binary_mismatches','nonidentical_values','max_margin_gradient_witness_error','edge_mismatches'))
R=HERE/'results';R.mkdir(exist_ok=True)
source=json.loads((WORK/'source_inventory.json').read_text())
for rel,h in source.items():assert sha(WORK/rel)==h,rel
for p in (HERE/'src').rglob('*'):
 if p.is_file():assert sha(p)==source[str(p.relative_to(HERE))],p
inventories={'source_inventory':source,
 'installed_files':{str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'},
 'fixture_files':{str(p.relative_to(WORK)):sha(p) for p in (WORK/'fixtures').rglob('*') if p.is_file()},
 'evaluator_files':{str(p.relative_to(OUT)):sha(p) for p in (OUT/'build').iterdir() if p.is_file() and (p.name in ('native_probe','solid_probe','support_probe','graph_probe','baseline_admission','differential_probe','profile_graph') or p.suffix=='.a')}}
for name,value in inventories.items():(R/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
counts={}
for name,folder in [('pct_unit',WORK/'build/lite3_nav2_plugins/test_results'),('regressions',WORK/'regressions')]:
 dest=R/name;dest.mkdir(exist_ok=True);total=0;files=0;names=[]
 for p in folder.rglob('*.xml'):
  root=ET.parse(p).getroot();assert int(root.get('failures',0))==int(root.get('errors',0))==0,p
  total+=int(root.get('tests'));files+=1;names.extend(t.attrib.get('name') for t in root.iter('testcase'));shutil.copy2(p,dest/p.name)
 counts[name]=dict(targets=files,cases=total)
 if name=='pct_unit':assert files==8 and total==62 and 'FreeCellIndexRetainsEveryContactAndFloorBoundary' in names,counts
 else:assert files==12 and total==97,counts
raw=WORK/'fixtures/building/static_solids.env';assert sha(raw)=='e27f308f4bf6e69a6cb09ed72f3ad32f493933114319ba7ba0b7d51f2d02f3ac'
for name in ('differential.txt','equivalence52/receipt.json','equivalence52/table.csv'):
 p=OUT/name;dest=R/p.name;shutil.copy2(p,dest)
receipt=dict(version='v259',parent='v256',passed=True,stage='Exact equivalent accelerator, no new-floor/orientation/physical claim',tests=counts,overlap_cases=10,differential=diff,old52=gate,raw_solid_sha256=sha(raw),policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',hard_radius_m=.35,sensor_period_s=.1,physics_steps=0)
(R/'acceptance_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
for rel in files:
 p=HERE/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,p)
manifest=dict(version='v259',parent='v256',frozen=True,source_files=files,parent_manifest_sha256=sha(HERE.parent/'v256/manifest.json'),inventories={name:sha(R/(name+'.json')) for name in inventories},acceptance_receipt_sha256=sha(R/'acceptance_receipt.json'),raw_solid_source=str(raw),raw_solid_sha256=sha(raw),hard_radius_m=.35,sensor_period_s=.1,policy_sha256=receipt['policy_sha256'])
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(receipt),flush=True)
