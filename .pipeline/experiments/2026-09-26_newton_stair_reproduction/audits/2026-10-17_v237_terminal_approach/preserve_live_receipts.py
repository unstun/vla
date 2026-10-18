"""One-off retention repair for this task's reused diagnostic output names."""
from pathlib import Path
import hashlib
import json
import shutil

w=Path('/work')
v=Path('/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v238/results')
out=w/'live_trigger01';out.mkdir(exist_ok=True)
for arm in ('baseline','candidate'):
    original=v/(arm+'03_frames.csv')
    assert len(original.read_text().splitlines())==142
    current=w/(arm+'03')
    shutil.copytree(current,out/arm,dirs_exist_ok=True)
    for prefix in ('','build_','configure_'):
        p=w/(prefix+arm+'03.log')
        if p.exists():shutil.copy2(p,out/p.name)
    shutil.copy2(original,current/'frames.csv')
summary={arm:json.loads((out/arm/'live_trigger.json').read_text()) for arm in ('baseline','candidate')}
assert summary['baseline']['emergency_message']==1 and summary['candidate']['emergency_message']==0
summary['scope']='Controlled real-clock native safety callback; fixed original map, fresh body heartbeats, no incoming new cloud, no physics; not full-window input-delivery replay.'
summary['retention_note']='Supplemental diagnostic reused WORK/*03 paths and superseded the original full-run stdout. Complete 141-row CSVs had already been returned/frozen and are restored. Original v237 raw evidence and v232 install were not changed. Old stdout hashes remain historical receipts, not current-file claims.'
summary['artifacts']={str(p.relative_to(out)):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in out.rglob('*') if p.is_file() and p.name!='summary.json'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({arm:summary[arm] for arm in ('baseline','candidate')},indent=2))
