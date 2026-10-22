"""Local freeze of the source-qualified case-owned execution after real graph gates."""
from pathlib import Path
import ast,hashlib,json,shutil
HERE=Path(__file__).resolve().parent;V=HERE.parents[1]/'versions/v246'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (V/'manifest.json').exists()
identity=json.loads((V/'source_identity.json').read_text())
for rel,h in identity['files'].items():assert sha(V/rel)==h,rel
preflight={}
for case in ('A02','G07','R11'):
 p=HERE/'preflight'/case/'preflight_passed.json';a=json.loads(p.read_text());assert a['passed'] and a['physics_steps']==0 and all(s['exit_code']==0 for s in a['steps']);preflight[case]=sha(p)
for p in V.glob('*.py'):ast.parse(p.read_text())
files={str(p.relative_to(V)):sha(p) for p in V.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
(V/'source').mkdir()
for rel in files:
 p=V/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(V/rel,p)
value=dict(version='v246',parent='v244',native_source='v244 PCT + v240 SCAN',evaluation='v245',frozen=True,status='three case-specific real graph/profile/ABI/scanner preflights passed before physical attempts',source_files=files,snapshot_locations={r:'source/'+r for r in files},source_identity_sha256=sha(V/'source_identity.json'),native_manifest_sha256=sha(V.parent/'v244/manifest.json'),evaluation_manifest_sha256=sha(V.parent/'v245/manifest.json'),protocol_gate_sha256=sha(V.parent/'v245/results/protocol_offline_gate.json'),preflight_receipts=preflight,authorized_attempts_per_case=1,physical_cases=['A02','G07','R11'],hard_collision_support_m=.35,sensor_period_s=.1,scan_deadline_s=.1,unchanged_policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',claim='Qualified execution source freeze; no physical outcome asserted before execution')
(V/'manifest.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(version=value['version'],source_files=len(files),manifest_sha256=sha(V/'manifest.json'))))
