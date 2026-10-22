"""Freeze floor evidence repair, never promote it to full benchmark acceptance."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET,re
HERE=Path(__file__).resolve().parent;B=Path('/data/sun/vla_mppi_20261009');WORK=B/'generic_mechanisms_v260/native';OUT=B/'generic_mechanisms_v260/evaluation';R=HERE/'results'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
m=dict(line.split('=',1) for line in (OUT/'support/metrics.txt').read_text().splitlines() if '=' in line)
assert m['snapshot_fnv64']=='15212154834549674106' and m['parity_queries']=='12219' and m['old_typed_mismatch']==m['field_admission_mismatch']=='0'
assert sha(OUT/'support/native.support')==sha(WORK/'fixtures/building/native.support')
controls=json.loads((OUT/'controls04/receipt.json').read_text());assert len(controls)==8 and all(r['code']==0 for r in controls)
for c in ('A04','G05'):
 assert next(r for r in controls if r['case_id']==c)['metrics']['global_admitted']=='1'
 assert 'pct_optimizer_rejected' not in (OUT/'controls04'/c/'stdout.log').read_text()
lines=(B/'generic_mechanisms_v260/east_graph_final.log').read_text().splitlines();graphs=[l for l in lines if l.startswith('GRAPH case=')];assert len(graphs)==12
assert all(('solids=0 pass=1' in l) if 'solids=0' in l else 'solids=1 pass=0' in l for l in graphs)
R.mkdir(exist_ok=True);source=json.loads((WORK/'source_inventory.json').read_text())
for rel,h in source.items():assert sha(WORK/rel)==h,rel
for p in (HERE/'src').rglob('*'):
 if p.is_file():assert sha(p)==source[str(p.relative_to(HERE))]
inventories=dict(source_inventory=source,
 installed_files={str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'},
 fixture_files={str(p.relative_to(WORK)):sha(p) for p in (WORK/'fixtures').rglob('*') if p.is_file()},
 evaluator_files={str(p.relative_to(OUT)):sha(p) for p in (OUT/'build').iterdir() if p.is_file() and (p.name in ('native_probe','solid_probe','support_probe','graph_probe','baseline_admission') or p.suffix=='.a')})
for k,v in inventories.items():(R/(k+'.json')).write_text(json.dumps(v,indent=2)+'\n')
counts={}
for name,folder in [('pct_unit',WORK/'build/lite3_nav2_plugins/test_results'),('regressions',WORK/'regressions')]:
 d=R/name;d.mkdir(exist_ok=True);n=f=0
 for p in folder.rglob('*.xml'):
  root=ET.parse(p).getroot();assert int(root.get('failures',0))==int(root.get('errors',0))==0,p;n+=int(root.get('tests'));f+=1;shutil.copy2(p,d/p.name)
 counts[name]=dict(targets=f,cases=n)
 assert (f,n)==((8,62) if name=='pct_unit' else (12,97)),counts
summary=json.loads((WORK/'fixtures/building/mesh_floor_source.json').read_text());summary.pop('added_selected_records');summary['full_source_receipt_sha256']=sha(WORK/'fixtures/building/mesh_floor_source.json')
(R/'mesh_floor_source.json').write_text(json.dumps(summary,indent=2)+'\n')
shutil.copy2(OUT/'support/metrics.txt',R/'support_parity.txt');shutil.copy2(OUT/'controls04/receipt.json',R/'controls.json')
(R/'east_graph.txt').write_text('\n'.join(l for l in lines if l.startswith(('GRAPH case=','-1=','SOLID ')))+'\n')
receipt=dict(version='v260',parent='v259',passed=True,stage='Finite original-floor source and source-to-graph completeness; not clean50 acceptance or physics',tests=counts,synthetic_mesh_tests=4,support_parity=m,controls=8,first_gpmp_controls=['A04','G05'],east_support_only_connected=6,east_full_solid_refused=6,hard_radius_m=.35,sensor_period_s=.1,physics_steps=0,policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b')
(R/'acceptance_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
for rel in files:
 p=HERE/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,p)
manifest=dict(version='v260',parent='v259',frozen=True,source_files=files,parent_manifest_sha256=sha(HERE.parent/'v259/manifest.json'),inventories={k:sha(R/(k+'.json')) for k in inventories},acceptance_receipt_sha256=sha(R/'acceptance_receipt.json'),native_support_fnv64=m['snapshot_fnv64'],raw_solid_sha256=sha(WORK/'fixtures/building/static_solids.env'),hard_radius_m=.35,sensor_period_s=.1,policy_sha256=receipt['policy_sha256'])
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(receipt),flush=True)
