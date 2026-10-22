"""Read original v285 log evidence without re-running physics."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'versions/v196'))
from analyze_remote import Capture

rows=[]
for case in ['A04','G05','CU06','CM02','CD12']:
    root=Path('/home/sun/vla_exec/physical_runs_v285')/f'v285_{case}_attempt01/runs/v285_{case}_attempt01'
    capture=Capture(root)
    log=capture.read('nav2.log')
    blocked=[line for line in log.splitlines() if 'reactive_collision_blocked' in line]
    pairs=Counter()
    for line in blocked:
        match=re.search(r'verdict=(\d+) voxel=(\d+)',line)
        assert match,line
        pairs[(int(match[1]),int(match[2]))]+=1
    row=dict(case_id=case,reactive_blocked_lines=len(blocked),
        verdict_voxel_counts=[dict(verdict=v,voxel=o,lines=n) for (v,o),n in sorted(pairs.items())],
        first_blocked_lines=blocked[:3],refinement_error_mentions=log.count('Solver error while refining'),
        no_executable_mentions=log.count('Native SCAN has no executable trajectory'),
        progress_failure_lines=[l for l in log.splitlines() if 'Failed to make progress' in l],
        nav2_log_sha256=hashlib.sha256(log.encode()).hexdigest(),sources=capture.sources)
    rows.append(row)
    print(json.dumps({k:v for k,v in row.items() if k not in ['first_blocked_lines','sources']},ensure_ascii=False),flush=True)
output=HERE/'results/parent_v285_evidence.json'
assert not output.exists()
output.write_text(json.dumps(dict(physics_steps=0,cases=rows),indent=2)+'\n')
