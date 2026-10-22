"""Return compact scored evidence; retain heavy source/captures remotely."""
from pathlib import Path
import collections,csv,hashlib,importlib.util,json,shutil
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'space_coverage_v257'
EXP=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
HERE=EXP/'audits/2026-10-18_v256_static_solids_and_space_coverage'
DEST=OUT/'compact_return'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('frozen257',EXP/'versions/v257/run_matrix.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.verify_frozen()
summary=json.loads((OUT/'matrix_summary.json').read_text());assert len(summary['calls'])==52
assert len(list((OUT/'scored').iterdir()))==52
for c in summary['calls']:
 cid=c['case_id'];folder=OUT/'scored'/cid;target=DEST/'cases'/cid
 target.mkdir(parents=True,exist_ok=True)
 for name in ('stdout.log','metrics.txt','summary.json','independent_solid_audit.json','independent_audit.log'):
  p=folder/name
  if p.exists():shutil.copy2(p,target/name)
 for name in ('scenario.json','endpoints.txt','fixture.json'):
  shutil.copy2(OUT/'cases'/cid/name,target/name)
 requests=[]
 for p in sorted(folder.glob('static_request_*.csv'),key=lambda p:int(p.stem.split('_')[-1])):
  rows=list(csv.DictReader(p.open()));bad=[r for r in rows if int(r['verdict'])]
  requests.append(dict(source=str(p),sha256=sha(p),samples=len(rows),rejected=len(bad),
   counts=dict(collections.Counter(r['verdict'] for r in bad)),
   first_rejected=bad[0] if bad else None,last_rejected=bad[-1] if bad else None,
   first_six_rejected=bad[:6]))
 write(target/'static_witnesses.json',requests)
 inventory={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for root in (folder,OUT/'cases'/cid) for p in root.rglob('*') if p.is_file()}
 write(target/'remote_inventory.json',inventory)
for name in ('matrix_summary.json','matrix_table.csv','offline_gate.json','selection.json','matrix.log','policy_golden.json','ground_core_components.json','ground_enclosure_audit.json','mesh_endpoint_audit.json'):
 shutil.copy2(OUT/name,DEST/name)
diag=OUT/'diagnosis'
if diag.exists() and (diag/'graph.log').exists():
 shutil.copy2(diag/'graph.log',DEST/'graph_diagnosis.log')
 write(DEST/'diagnostic_remote_inventory.json',{str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in diag.iterdir() if p.is_file()})
receipt=dict(frozen_verified_after_scoring=True,native_version='v256',evaluator='v257',
 native_manifest_sha256=sha(EXP/'versions/v256/manifest.json'),evaluator_manifest_sha256=sha(EXP/'versions/v257/manifest.json'),
 cases_manifest_sha256=sha(OUT/'cases_manifest.json'),scored_calls=52,physical_attempts=0,
 heavy_evidence_root=str(OUT),heavy_native_root=str(BASE/'generic_mechanisms_v256/native'),
 original_failed_gate_preserved=not summary['gate']['passed'],
 files={str(p.relative_to(DEST)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in DEST.rglob('*') if p.is_file() and p.name!='return_receipt.json'})
write(DEST/'return_receipt.json',receipt)
print(json.dumps(dict(files=len(receipt['files']),bytes=sum(v['bytes'] for v in receipt['files'].values()),frozen_verified=True,physics_attempts=0)))
