"""Freeze tested native source/install; benchmark acceptance remains separate."""
from pathlib import Path
import hashlib,json,shutil,sys,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;B=Path('/data/sun/vla_mppi_20261009')
WORK=B/'generic_mechanisms_v261/native';OUT=B/'generic_mechanisms_v261/evaluation';R=HERE/'results'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tag=sys.argv[1];assert tag.isdigit() and not (HERE/'manifest.json').exists()
metrics=lambda p:dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line)
diff=metrics(B/f'generic_mechanisms_v261/differential{tag}.log')
assert diff['queries']=='70928' and diff['edges']=='5000'
assert all(diff[k]=='0' for k in ('binary_mismatches','nonidentical_values',
    'max_margin_gradient_witness_error','edge_mismatches','false_free_batches'))
rotation=metrics(B/f'generic_mechanisms_v261/rotation{tag}.log')
assert rotation['samples']=='4096' and rotation['false_free_certificates']=='0'
controls=json.loads((OUT/f'controls{tag}/receipt.json').read_text())
assert len(controls)==6 and all(c['metrics']['global_admitted']=='1' for c in controls)
source=json.loads((WORK/'source_inventory.json').read_text())
for rel,h in source.items():assert sha(WORK/rel)==h,rel
for p in (HERE/'src').rglob('*'):
    if p.is_file():assert sha(p)==source[str(p.relative_to(HERE))]
R.mkdir(exist_ok=True);counts={}
for name,folder in [('pct_unit',WORK/'build/lite3_nav2_plugins/test_results'),('regressions',WORK/'regressions')]:
    dest=R/name;dest.mkdir(exist_ok=True);cases=targets=0
    for p in folder.rglob('*.xml'):
        root=ET.parse(p).getroot();assert int(root.get('failures',0))==int(root.get('errors',0))==0,p
        cases+=int(root.get('tests'));targets+=1;shutil.copy2(p,dest/p.name)
    counts[name]=dict(targets=targets,cases=cases)
assert counts['pct_unit']['targets']==8 and counts['pct_unit']['cases']>=70
assert counts['regressions']==dict(targets=12,cases=97)
inventories=dict(source_inventory=source,
    installed_files={str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'},
    fixture_files={str(p.relative_to(WORK)):sha(p) for p in (WORK/'fixtures').rglob('*') if p.is_file()},
    evaluator_files={str(p.relative_to(OUT)):sha(p) for p in (OUT/'build').iterdir() if p.is_file() and (p.name.endswith('_probe') or p.name=='baseline_admission' or p.suffix=='.a')})
for k,v in inventories.items():(R/(k+'.json')).write_text(json.dumps(v,indent=2)+'\n')
for stem in ('build','probe_build','unit','rotation','differential','regressions'):
    p=B/f'generic_mechanisms_v261/{stem}{tag}.log';shutil.copy2(p,R/p.name)
(R/'controls.json').write_text(json.dumps(controls,indent=2)+'\n')
receipt=dict(version='v261',parent='v260',validation_generation=tag,tests=counts,
    differential=diff,rotation=rotation,control_cases=6,
    clean50_acceptance=False,physical_attempts=0,scope='Native unit/equivalence and hard control tests; full benchmark gate is separate')
(R/'native_test_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','development','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
for rel in files:
    dest=HERE/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,dest)
manifest=dict(version='v261',parent='v260',frozen=True,source_files=files,
    parent_manifest_sha256=sha(HERE.parent/'v260/manifest.json'),inventories={k:sha(R/(k+'.json')) for k in inventories},
    native_test_receipt_sha256=sha(R/'native_test_receipt.json'),
    native_support_fnv64='15212154834549674106',raw_solid_sha256=sha(WORK/'fixtures/building/static_solids.env'),
    hard_radius_m=.35,sensor_period_s=.1,policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b')
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(manifest_sha256=sha(HERE/'manifest.json'),receipt=receipt)),flush=True)
