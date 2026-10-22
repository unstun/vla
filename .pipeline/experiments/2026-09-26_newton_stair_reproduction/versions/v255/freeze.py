"""Freeze a process-only physical binding after the A02 zero-step preflight."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
identity=json.loads((HERE/'source_identity.json').read_text())
for rel,h in identity['files'].items():assert sha(HERE/rel)==h,rel
preflight={}
for cid in ('A02',):
 p=BASE/'generalization_v255'/cid/'preflight_passed.json';receipt=json.loads(p.read_text())
 assert receipt['passed'] and receipt['physics_steps']==0 and all(r['exit_code']==0 for r in receipt['steps'])
 preflight[cid]=sha(p)
 q=HERE/'results/preflight'/cid;q.mkdir(parents=True)
 shutil.copy2(p,q/p.name)
files=dict(identity['files']);files['source_identity.json']=sha(HERE/'source_identity.json')
for rel in files:
 p=HERE/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,p)
manifest=dict(version='v255',parent='v254',native_source='v254 PCT+SCAN / frozen v248 bridge',frozen=True,
 source_files=files,snapshot_locations={r:'source/'+r for r in files},source_identity_sha256=sha(HERE/'source_identity.json'),
 native_manifest_sha256=sha(HERE.parent/'v254/manifest.json'),
 offline_gate_sha256=sha(HERE/'results/offline_gate.json'),preflight_receipts=preflight,
 authorized_attempts_per_case=1,physical_cases=['A02'],hard_collision_support_m=.35,
 cylinder_offset_m=.18,sensor_period_s=.1,scan_deadline_s=.1,
 unchanged_policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',
 navigation_active_before_goal_required=True,claim='Frozen execution binding and zero-step qualification; physical outcomes recorded separately')
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(frozen=True,version='v255',sha256=sha(HERE/'manifest.json'))),flush=True)
