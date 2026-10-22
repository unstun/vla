"""Retain a qualified-equivalence but slower candidate, without adopting it."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009/generic_mechanisms_v265')
OUT=BASE/'evaluation';WORK=BASE/'native';RESULT=HERE/'results';RESULT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inventory=json.loads((WORK/'source_inventory.json').read_text())
for rel,h in inventory.items():assert sha(WORK/rel)==h,rel
counts={}
for label,folder in [('plugin',WORK/'build/lite3_nav2_plugins/test_results'),('native',WORK/'regressions')]:
    files=list(folder.rglob('*.xml'));cases=0;target=RESULT/label;target.mkdir(exist_ok=True)
    for p in files:
        r=ET.parse(p).getroot();assert int(r.get('failures',0))==int(r.get('errors',0))==0
        cases+=int(r.get('tests',0));shutil.copy2(p,target/p.name)
    counts[label]=dict(targets=len(files),cases=cases)
assert counts['native']==dict(targets=12,cases=97)
assert counts['plugin']['cases']>=74
for name in ('build','probe_build','unit','rotation','differential','support_differential','environmental_differential','regressions','legacy_requests'):
    p=BASE/(name+'01.log');assert p.exists();shutil.copy2(p,RESULT/p.name)
controls=json.loads((OUT/'controls01/receipt.json').read_text())
parent=json.loads((HERE.parent/'v261/results/controls.json').read_text())
prior={r['case_id']:float(r['metrics']['global_s']) for r in parent}
timing=[dict(case_id=r['case_id'],candidate_global_s=float(r['metrics']['global_s']),parent_recorded_global_s=prior[r['case_id']]) for r in controls]
assert all(r['candidate_global_s']>r['parent_recorded_global_s'] for r in timing)
report=dict(version='v265',adopted=False,frozen_as_accepted=False,reason='All six recorded controls slower; retain frozen v261 four-anchor cache',
    controls=timing,tests=counts,planning_matrix_calls=0,physical_attempts=0,
    timing_caveat='Recorded same-host CPU2 component controls; not a replicated performance distribution',
    source_inventory=inventory,installed_files={str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts},
    parent_manifest_sha256=sha(HERE.parent/'v261/manifest.json'),
    source_files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','__pycache__') and p.name!='RESULTS.md'},
    evidence={p.name:sha(p) for p in RESULT.glob('*.log')})
(RESULT/'rejected_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(adopted=False,tests=counts,controls=timing)))
