"""Freeze qualified case execution after all zero-step process/profile checks."""
from pathlib import Path
import ast,hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
identity=json.loads((HERE/'source_identity.json').read_text())
for rel,h in identity['files'].items():assert sha(HERE/rel)==h,rel
selection=json.loads((HERE/'selection.json').read_text());assert selection['physical_admission_passed'] and len(selection['selected'])==3
preflight={}
for item in selection['selected']:
 cid=item['case_id'];p=BASE/'generalization_v248'/cid/'preflight_passed.json';row=json.loads(p.read_text())
 assert row['passed'] and row['physics_steps']==0 and all(s['exit_code']==0 for s in row['steps']);preflight[cid]=sha(p)
for p in HERE.rglob('*.py'):
 if '__pycache__' not in p.parts:ast.parse(p.read_text())
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('source','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
for rel in files:
 q=HERE/'source'/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,q)
manifest=dict(version='v248',parent='v247',native_source='v247 PCT+SCAN / v248 bridge',frozen=True,source_files=files,
 snapshot_locations={r:'source/'+r for r in files},source_identity_sha256=sha(HERE/'source_identity.json'),native_manifest_sha256=sha(HERE.parent/'v247/manifest.json'),
 offline_gate_sha256=sha(HERE.parent/'v247/results/offline_gate.json'),preflight_receipts=preflight,
 authorized_attempts_per_case=1,physical_cases=[r['case_id'] for r in selection['selected']],
 hard_collision_support_m=.35,cylinder_offset_m=.18,sensor_period_s=.1,scan_deadline_s=.1,
 unchanged_policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',
 navigation_active_before_goal_required=True,claim='Source/config/process/scanner qualification; physical outcome pending')
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(version='v248',source_files=len(files),manifest_sha256=sha(HERE/'manifest.json'))),flush=True)
