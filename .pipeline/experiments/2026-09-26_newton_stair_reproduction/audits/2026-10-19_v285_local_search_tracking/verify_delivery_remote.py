"""Final read-only source/attempt/history audit after the physical batch closes."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent;E=HERE.parents[1];V=E/'versions/v285'
ROOT=Path('/home/sun/vla_exec/local_search_tracking_v285')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(V));from identity import verify_sources
from run_physical import recorded_physics_steps
identity=verify_sources();m=json.loads((V/'manifest.json').read_text())
for rel,h in m['source_files'].items():assert sha(V/rel)==h and sha(V/'source'/rel)==h,rel
for ver in ['v283','v284']:
    base=V.parent/ver;parent=json.loads((base/'manifest.json').read_text())
    for rel,h in parent['source_files'].items():assert sha(base/rel)==h and sha(base/'source'/rel)==h,(ver,rel)
ledger=json.loads((ROOT/'benchmark/native_ledger.json').read_text());assert len(ledger)==53 and len({r['case_id'] for r in ledger})==53 and all(r['state']=='finished' for r in ledger)
rows=json.loads((HERE/'results/physical_batch_status.json').read_text());assert len(rows)==10 and all(r['formal_attempt_started'] and r['stage']=='execution_closed_pending_analysis' for r in rows)
for c in m['physical_cases']:
    raw=Path('/home/sun/vla_exec/physical_runs_v285')/f'v285_{c}_attempt01'
    assert raw.is_dir() and (recorded_physics_steps(raw/'runs'/raw.name) or 0)>0
    assert len(list(raw.parent.glob(f'v285_{c}_attempt*')))==1,c
    assert (Path('/data/sun/vla_mppi_20261009/generalization_v285')/c/'execution/physical_launch_once.json').is_file()
oldroot=E/'audits/2026-10-19_v283_navigation_geometry/results/recovery/zero_physics_launch_failures01'
old=[]
for c in ['A04','G05','CU06','D07','S04']:
    p=oldroot/c/'preservation.json';d=json.loads(p.read_text());assert d['physics_steps']==0 and not d['formal_attempt_started']
    count=0
    for label,root in [('task_inventory','task_archive'),('execution_inventory','execution_archive')]:
        for entry in d[label]:
            if entry['kind']=='file':
                q=Path(d[root])/entry['path'];assert q.is_file() and sha(q)==entry['sha256'],str(q);count+=1
    original=Path(d['original_launch_log']);assert sha(original)==sha(p.parent/original.name)
    old.append(dict(case_id=c,archived_files_verified=count,original_launch_log_verified=True,preservation_receipt_sha256=sha(p)))
report=dict(passed=True,physics_steps=0,source_identity=identity,native_manifest_sha256=sha(V/'native_manifest.json'),
    execution_manifest_sha256=sha(V/'manifest.json'),source_and_snapshot_files=len(m['source_files']),
    prior_v283_v284_frozen_sources_unchanged=True,scored_calls=53,physical_attempts=10,one_actual_attempt_each=True,
    preserved_zero_physics_launch_failures=old,coordinator_receipts={p.name:sha(p) for p in ROOT.glob('*.json')},
    audit_source_sha256=sha(Path(__file__)))
(HERE/'results/final_remote_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['source_identity','coordinator_receipts','preserved_zero_physics_launch_failures']}))
