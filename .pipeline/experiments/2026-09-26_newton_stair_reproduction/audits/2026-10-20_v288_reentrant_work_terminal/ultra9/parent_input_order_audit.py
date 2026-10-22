"""Count the same body-time failure in preserved parent recordings only."""
from pathlib import Path
import hashlib
import json
import sys
R=Path('/home/ubuntu/sun/vla_v288_20261020')
P=Path('/home/ubuntu/sun/vla_v287_20261020')
E=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
sys.path.insert(0,str(E/'versions/v196'))
from analyze_remote import Capture
out=R/'evidence/parent_input_order_audit01.json';assert not out.exists()
rows=[]
for cid in json.loads((R/'cohort/cases_manifest.json').read_text())['physical_cases']:
    c=Capture(P/'physical_runs'/f'v287_{cid}_attempt01/runs/v287_{cid}_attempt01')
    log=c.read('nav2.log');result=c.json('result.json')
    rows.append(dict(case_id=cid,regressed_body_source_stamp_mentions=log.count('regressed_body_source_stamp'),
        failed_to_make_progress_mentions=log.count('Failed to make progress'),
        recorded_physics_duration_s=result['physics_duration_s'],finish=result.get('finish_request'),sources=c.sources))
out.write_text(json.dumps(dict(physics_steps=0,parent='v287',cases=rows,
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
print(json.dumps({r['case_id']:r['regressed_body_source_stamp_mentions'] for r in rows}))
