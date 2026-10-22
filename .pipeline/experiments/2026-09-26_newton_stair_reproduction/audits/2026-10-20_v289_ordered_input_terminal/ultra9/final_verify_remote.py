"""Verify closed attempts and frozen sources without launching any experiment."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

R = Path('/home/ubuntu/sun/vla_v289_20261020')
P = Path('/home/ubuntu/sun/vla_v288_20261020')
E = R / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
os.environ.setdefault('V289_CASE_ID', 'A04')
sys.path.insert(0, str(R / 'migration'))
import physical

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
proof = physical.verify_sources()
rows = json.loads((R / 'evidence/physical_batch_status.json').read_text())
complete = json.loads((R / 'evidence/physical_batch_complete.json').read_text())
assert len(rows) == 10 and all(r['stage'] == 'closed' and r['physics_steps'] > 0 for r in rows)
assert complete['all_closed'] and complete['positive_physics_recordings'] == 10
assert len(list((R / 'physical_runs').glob('v289_*_attempt01'))) == 10
assert json.loads((R / 'evidence/after_physics01.json').read_text())['returncode'] == 0
names = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).splitlines()
owned = [name for name in names if name.startswith('v289-')]
assert not owned, owned
parent = P / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288/native_manifest.json'
assert sha(parent) == 'e8935ba2b1d1ba3d8931641afda7eec0e951ef66805e49a7f6be7ab8233010af'
result = dict(passed=True, physics_steps=0, script_sha256=sha(Path(__file__)),
    source_verification=proof, parent_manifest_sha256=sha(parent), physical_attempts=10,
    positive_physics_steps=sum(row['physics_steps'] for row in rows), active_v289_containers=owned,
    other_containers_left_running=len(names), disk_free_gib=shutil.disk_usage(R).free / 2**30,
    hard_radius_m=.35, sensor_period_s=.1, physics_reruns_for_analysis=0, verified_utc_s=time.time())
out = R / 'evidence/final_frozen_sources01.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'source_verification'}))
