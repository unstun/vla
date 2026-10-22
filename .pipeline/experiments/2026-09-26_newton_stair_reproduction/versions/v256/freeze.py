"""Freeze final native source/install, independent parity and unit evidence."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'generic_mechanisms_v256/native';OUT=BASE/'generic_mechanisms_v256/evaluation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
R=HERE/'results';R.mkdir(exist_ok=True)
source=json.loads((WORK/'source_inventory.json').read_text())
for rel,h in source.items():assert sha(WORK/rel)==h,rel
for p in (HERE/'src').rglob('*'):
 if p.is_file():assert source[str(p.relative_to(HERE))]==sha(p),p
for name,inventory in [('source_inventory',source),('installed_files',{str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}),('fixture_files',{str(p.relative_to(WORK)):sha(p) for p in (WORK/'fixtures').rglob('*') if p.is_file()}),('evaluator_files',{str(p.relative_to(OUT)):sha(p) for p in (OUT/'build').iterdir() if p.is_file() and (p.name in ('native_probe','support_probe','solid_probe','graph_probe','baseline_admission') or p.suffix=='.a')})]:
 (R/(name+'.json')).write_text(json.dumps(inventory,indent=2)+'\n')
unit={};D=R/'pct_unit';D.mkdir(exist_ok=True)
for p in (WORK/'build/lite3_nav2_plugins/test_results').rglob('*.xml'):
 root=ET.parse(p).getroot();assert int(root.get('failures',0))==int(root.get('errors',0))==0,p
 unit[p.stem]=int(root.get('tests'));shutil.copy2(p,D/p.name)
assert len(unit)==8 and sum(unit.values())==61,unit
reg={};D=R/'regressions';D.mkdir(exist_ok=True)
for p in (WORK/'regressions').glob('*.xml'):
 root=ET.parse(p).getroot();assert int(root.get('failures',0))==int(root.get('errors',0))==0,p
 reg[p.stem]=int(root.get('tests'));shutil.copy2(p,D/p.name)
 for ext in ('.log',):shutil.copy2(p.with_suffix(ext),D/p.with_suffix(ext).name)
assert len(reg)==12 and sum(reg.values())==97,reg
m=dict(line.split('=',1) for line in (OUT/'solids/metrics.txt').read_text().splitlines() if '=' in line)
assert int(m['solid_queries'])==10928 and m['raw_oracle_mismatch']==m['static_admission_mismatch']=='0' and float(m['max_margin_error'])<1e-6
assert m['b08_verdict']=='7'
controls=json.loads((OUT/'controls_binary_summary.json').read_text());assert len(controls['calls'])==14
for row in controls['calls']:
 if row['case_id']=='B09':assert not row['global_admitted'];continue
 if row['case_id']=='B08' and row['global_admitted']:
  assert row['end_to_end_pass'] and row['raw_solid_margin_min']>=0.;continue
 if row['case_id']=='B08' and not row['global_admitted']:continue
 assert row['global_admitted'] and row['first_gpmp_static_pass'],row['case_id']
 if row['case_id']!='A02_measured':assert row['end_to_end_pass'] and row['raw_solid_margin_min']>=0.,row['case_id']
shutil.copy2(OUT/'controls_binary_summary.json',R/'controls_summary.json');shutil.copy2(OUT/'solids/metrics.txt',R/'solid_parity.txt');shutil.copy2(OUT/'solids/independent_solid_audit.json',R/'independent_solid_audit.json')
raw=WORK/'fixtures/building/static_solids.env'
material=json.loads((raw.with_suffix('.json')).read_text())
assert material['unchanged_voxel_geometry'] and material['unchanged_floor_channel'] and material['unchanged_original_volume_associations']
shutil.copy2(raw.with_suffix('.json'),R/'solid_source.json')
shutil.copy2(BASE/'generic_mechanisms_v256/b08_original_material.json',R/'b08_original_material.json')
receipt=dict(version='v256',passed=True,stage='offline native repair and original controls, not expanded matrix or physical validation',unit_targets=8,unit_cases=61,native_regression_targets=12,native_regression_cases=97,overlap_cases=10,solid_parity=m,controls=14,source_files=len(source),raw_solid_source=str(raw),raw_solid_sha256=sha(raw),raw_solid_fnv64=material['fnv64'],parent='v254',hard_radius_m=.35,offset_m=.18,up_m=.55,down_m=.35,body_clearance_m=.3,sensor_period_s=.1,policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',physics_steps=0)
(R/'acceptance_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
for rel in files:
 p=HERE/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,p)
manifest=dict(version='v256',parent='v254',frozen=True,source_files=files,parent_manifest_sha256=sha(HERE.parent/'v254/manifest.json'),inventories={name:sha(R/(name+'.json')) for name in ('source_inventory','installed_files','fixture_files','evaluator_files')},acceptance_receipt_sha256=sha(R/'acceptance_receipt.json'),raw_solid_source=str(raw),raw_solid_sha256=sha(raw),raw_solid_fnv64=receipt['raw_solid_fnv64'],hard_radius_m=.35,sensor_period_s=.1,policy_sha256=receipt['policy_sha256'])
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(receipt),flush=True)
