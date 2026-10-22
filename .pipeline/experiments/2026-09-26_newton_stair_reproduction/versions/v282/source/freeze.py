"""Freeze one process/configuration binding for all ten formal attempts."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
identity=json.loads((HERE/'source_identity.json').read_text())
for rel,h in identity['files'].items():assert sha(HERE/rel)==h,rel
selection=json.loads((HERE/'selection.json').read_text());cases=[r['case_id'] for r in selection['selected']];assert len(cases)==len(set(cases))==10
preflight={}
for cid in cases:
 p=BASE/'generalization_v282'/cid/'preflight_passed.json';receipt=json.loads(p.read_text())
 assert receipt['passed'] and receipt['physics_steps']==0 and all(r['exit_code']==0 for r in receipt['steps'])
 preflight[cid]=sha(p);q=HERE/'results/preflight'/cid;q.mkdir(parents=True);shutil.copy2(p,q/p.name)
files=dict(identity['files']);files['source_identity.json']=sha(HERE/'source_identity.json')
for rel in files:
 p=HERE/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,p)
manifest=dict(version='v282',parent='v280',frozen=True,source_files=files,source_identity_sha256=sha(HERE/'source_identity.json'),native_manifest_sha256=sha(HERE.parent/'v280/manifest.json'),benchmark_manifest_sha256=sha(HERE.parent/'v281/manifest.json'),
 offline_gate_sha256=sha(HERE/'results/offline_gate.json'),preflight_receipts=preflight,authorized_attempts_per_case=1,physical_cases=cases,
 hard_collision_support_m=.35,cylinder_offset_m=.18,sensor_period_s=.1,scan_deadline_s=.1,
 unchanged_policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',explicit_terminal_heading=True,navigation_active_before_goal_required=True,claim='Common frozen execution binding with zero-step qualification; formal physical outcomes separate')
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(frozen=True,version='v282',sha256=sha(HERE/'manifest.json'),cases=cases)),flush=True)
