"""Compact immutable matrix return; all clouds, full CSVs and caches stay remote."""
from pathlib import Path
import collections,csv,hashlib,importlib.util,json,shutil,statistics
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');DEST=BASE/'saved_output_audit_v264/compact_return'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2)+'\n')
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
native=load(HERE.parent/'v261/verify_frozen.py','native_identity').verify()
benchmark=load(HERE.parent/'v262/run_matrix.py','benchmark_identity').verify()
clean=BASE/'mesh_benchmark_v262';original=BASE/'generic_mechanisms_v261/evaluation/original52_final'
new=json.loads((clean/'matrix_summary.json').read_text());old=json.loads((original/'progress.json').read_text())
assert len(new['calls'])==53 and len(old)==52 and json.loads((original/'complete.json').read_text())['calls']==52
for group,root,cases,rows in [('clean',clean/'scored',clean/'cases',new['calls']),('original',original,BASE/'space_coverage_v257/cases',old)]:
 for row in rows:
  cid=row['case_id'];folder=root/cid;target=DEST/group/cid;target.mkdir(parents=True,exist_ok=True)
  for name in ('stdout.log','metrics.txt','summary.json','independent_solid_audit.json','independent_audit.log'):
   p=folder/name
   if p.exists():shutil.copy2(p,target/name)
  for name in ('scenario.json','endpoints.txt','fixture.json'):shutil.copy2(cases/cid/name,target/name)
  requests=[]
  for p in sorted(folder.glob('static_request_*.csv')):
   data=list(csv.DictReader(p.open()));bad=[r for r in data if int(r['verdict'])]
   requests.append(dict(remote_path=str(p),sha256=sha(p),samples=len(data),rejected=len(bad),counts=dict(collections.Counter(r['verdict'] for r in bad)),first_rejected=bad[:6]))
  write(target/'static_witnesses.json',requests)
  write(target/'remote_inventory.json',{str(p.relative_to(BASE)):dict(bytes=p.stat().st_size,sha256=sha(p)) for r in (folder,cases/cid) for p in r.rglob('*') if p.is_file()})
 for name in (('matrix_summary.json','matrix_table.csv','offline_gate.json','selection.json','matrix.log','policy_golden.json','cases_manifest.json','component_receipt.json','construction_proposals.json') if group=='clean' else ('progress.json','complete.json','source_inventory.json')):
  q=DEST/group/name;q.parent.mkdir(exist_ok=True);shutil.copy2((clean if group=='clean' else original)/name,q)
base=json.loads((BASE/'space_coverage_v257/matrix_summary.json').read_text())
before={r['case_id']:r for r in base['calls']};table=[]
for r in old:
 a=before[r['case_id']];table.append(dict(case_id=r['case_id'],expected=r['expected'],stratum=r['stratum'],before_global=a['global_admitted'],after_global=r['global_admitted'],before_full=a['end_to_end_pass'],after_full=r['end_to_end_pass'],before_first_gpmp=a['first_gpmp_static_pass'],after_first_gpmp=r['first_gpmp_static_pass'],before_global_s=a['metrics'].get('global_s'),after_global_s=r['metrics'].get('global_s'),after_reason=r['metrics'].get('global_error'),after_edge_margin=r['edge_margin_min'],after_raw_solid_margin=r['raw_solid_margin_min']))
with (DEST/'original52_comparison.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
p=[r for r in old if r['expected']=='admit'];n=[r for r in old if r['expected']=='reject'];a=[r for r in p if r['global_admitted']]
write(DEST/'original52_summary.json',dict(calls=52,original_labels_unchanged=True,positive_passed=sum(r['end_to_end_pass'] for r in p),positive_total=len(p),global_admitted=len(a),first_gpmp=sum(r['first_gpmp_static_pass'] for r in a),illegal_correct=sum(r['expected_outcome_pass'] for r in n),illegal_total=len(n),global_median_s=statistics.median(r['metrics']['global_s'] for r in a),source_manifest_sha256=native['native_manifest_sha256'],original_evaluator_manifest_sha256=sha(HERE.parent/'v257/manifest.json')))
receipt=dict(native_manifest_sha256=native['native_manifest_sha256'],benchmark_manifest_sha256=sha(HERE.parent/'v262/manifest.json'),original_calls=52,clean_calls=53,
 original_labels_preserved=True,as_scored_clean_gate_passed=new['gate']['passed'],physical_attempts=0,source_and_install_verified_after_scoring=True,
 heavy_storage_roots=[str(clean),str(original),str(BASE/'generic_mechanisms_v261/native')],
 files={str(p.relative_to(DEST)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in DEST.rglob('*') if p.is_file() and p.name!='return_receipt.json'})
write(DEST/'return_receipt.json',receipt)
print(json.dumps(dict(files=len(receipt['files']),bytes=sum(v['bytes'] for v in receipt['files'].values()),native_verified=True,benchmark_verified=True,physical_attempts=0)),flush=True)
