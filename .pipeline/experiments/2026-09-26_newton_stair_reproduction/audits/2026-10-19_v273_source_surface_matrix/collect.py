"""Collect compact complete-cohort evidence; retain full numerical tables remotely."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_benchmark_v273';DEST=HERE/'results'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((OUT/'complete.json').read_text())['native_calls']==105
allow={'run01.log','native_ledger.json','audit_ledger.json','complete.json','offline_gate.json','matrix_summary.json','matrix_table.csv','selection.json','summary.json','metrics.txt','stdout.log','independent_solid_audit.json','independent_audit.log','spline.txt'}
returned={};remote={}
for p in OUT.rglob('*'):
 if not p.is_file() or 'ros_home' in p.parts or 'ros_logs' in p.parts or 'build' in p.parts:continue
 rel=str(p.relative_to(OUT));entry=dict(sha256=sha(p),bytes=p.stat().st_size,remote_path=str(p))
 if p.name in allow:
  assert p.stat().st_size<8*1024*1024
  q=DEST/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);returned[rel]=entry
 else:remote[rel]=entry
receipt=dict(source_version='v272',benchmark_version='v273',complete_native_calls=105,
 returned=returned,remote_numerical_evidence=remote,physical_attempts=0,
 regeneration='Frozen v273 scripts and native v272; original case fixtures remain pinned. Do not overwrite once-only ledgers. Any rerun requires a new explicitly identified cohort.')
DEST.mkdir(exist_ok=True);(DEST/'return_inventory.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(returned_files=len(returned),returned_bytes=sum(r['bytes'] for r in returned.values()),remote_files=len(remote))),flush=True)
