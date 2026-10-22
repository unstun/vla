"""Freeze all ten preflighted physical bindings without modifying native freeze."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
native=json.loads((HERE/'native_manifest.json').read_text());identity=json.loads((HERE/'source_identity.json').read_text())
files=dict(native['source_files'],**identity['files']);files.update({'native_manifest.json':sha(HERE/'native_manifest.json'),'source_identity.json':sha(HERE/'source_identity.json')})
for rel,h in files.items():assert sha(HERE/rel)==h,rel
receipts={}
for cid in native['physical_cases']:
    p=BASE/'generalization_v283'/cid/'preflight_passed.json';r=json.loads(p.read_text())
    assert r['passed'] and r['physics_steps']==0 and all(s['exit_code']==0 for s in r['steps'])
    receipts[cid]=sha(p);q=HERE/'results/preflight'/cid;q.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q/p.name)
for rel,h in files.items():
    q=HERE/'source'/rel;q.parent.mkdir(parents=True,exist_ok=True)
    if q.exists():assert sha(q)==h,rel
    else:shutil.copy2(HERE/rel,q)
manifest=dict(version='v283',parent='v282',native_parent='v280',frozen=True,source_files=files,
    native_manifest_sha256=sha(HERE/'native_manifest.json'),benchmark_manifest_sha256=native['cohort_sha256'],
    source_identity_sha256=sha(HERE/'source_identity.json'),offline_gate_sha256=sha(HERE/'results/offline_gate.json'),
    preflight_receipts=receipts,authorized_attempts_per_case=1,physical_cases=native['physical_cases'],
    hard_collision_support_m=.35,cylinder_offset_m=.18,sensor_period_s=.1,scan_deadline_s=.1,
    unchanged_policy_sha256=native['policy_sha256'],explicit_terminal_heading=True,navigation_active_before_goal_required=True,
    claim='Frozen native plus qualified execution binding; physical results remain separate')
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(version='v283',frozen=True,manifest_sha256=sha(HERE/'manifest.json'))))
