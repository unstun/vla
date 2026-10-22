"""Freeze source after negative/positive controls and before scored60calls."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
snap=HERE/'source';snap.mkdir()
for rel in files:
 q=snap/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,q)
value=dict(version='v244',parent='v240',control='v242',frozen=True,status='native_tests_and12development_calls_complete_before_scored_matrix',source_files=files,snapshot_locations={r:'source/'+r for r in files},parent_manifest_sha256=sha(HERE.parent/'v240/manifest.json'),cases_manifest_sha256=sha(HERE.parent/'v242/cases_manifest.json'),cases_version='v242',hard_collision_support_m=.35,sensor_period_s=.1,scan_deadline_s=.1,policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',body_geometry=dict(file='/task/environment_score_v224/fixtures/building/environment03.env',fnv64='4316416882194453309'),support_gap=dict(file='/work/fixtures/building/support_gap.txt',fnv64='10479033888964413526'),scope='Opt-in bounded exact-endpoint association and geometry-checked proposal graph; unchanged native final gates. No physical acceptance claim.')
(HERE/'manifest.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(dict(version=value['version'],source_files=len(files),manifest_sha256=sha(HERE/'manifest.json'))))
