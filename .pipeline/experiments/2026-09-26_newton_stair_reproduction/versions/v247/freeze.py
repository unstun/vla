"""Freeze verified source before the60fresh scored calls."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((HERE/'results/native_receipt.json').read_text());assert receipt['passed'] and receipt['historical_chain_passed']
assert not (HERE/'manifest.json').exists()
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
for rel in files:
 q=HERE/'source'/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,q)
manifest=dict(version='v247',parent='v240',control='v242',frozen=True,source_files=files,
 snapshot_locations={r:'source/'+r for r in files},parent_manifest_sha256=sha(HERE.parent/'v240/manifest.json'),
 cases_manifest_sha256=sha(HERE.parent/'v242/cases_manifest.json'),native_receipt_sha256=sha(HERE/'results/native_receipt.json'),
 static_support_sha256=receipt['static_support_sha256'],static_support_fnv64=receipt['static_support_fnv64'],
 hard_collision_support_m=.35,cylinder_offset_m=.18,sensor_period_s=.1,scan_deadline_s=.1,
 policy_sha256=receipt['policy_sha256'],scope='Native physical support and symmetric surface adjacency; ENV225soft only; no physical acceptance claim')
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(version='v247',source_files=len(files),manifest_sha256=sha(HERE/'manifest.json'))),flush=True)
