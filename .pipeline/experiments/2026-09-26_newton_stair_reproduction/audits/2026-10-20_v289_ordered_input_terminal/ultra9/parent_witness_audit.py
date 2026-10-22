from pathlib import Path
import sys,json,hashlib,re
P=Path('/home/ubuntu/sun/vla_v288_20261020');R=Path('/home/ubuntu/sun/vla_v289_20261020')
sys.path.insert(0,str(P/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v196'))
from analyze_remote import Capture
rows=[]
for cid in ('D07','S04','CS03','G05','CM07'):
 c=Capture(P/'physical_runs'/f'v288_{cid}_attempt01/runs/v288_{cid}_attempt01')
 lines=c.read('nav2.log').splitlines();witness=[]
 for i,line in enumerate(lines):
  if 'The robot is inside an obstacle' in line:
   context=[dict(line=j+1,text=lines[j][:1600]) for j in range(max(0,i-30),min(len(lines),i+10)) if 'spline_seed_capture' not in lines[j]]
   witness.append(dict(line=i+1,context=context))
 row=dict(case_id=cid,inside_obstacle=witness,unresponsive=[dict(line=i+1,text=s) for i,s in enumerate(lines) if 'unresponsive' in s],sources=c.sources)
 rows.append(row)
 print(cid,'inside=',len(witness),'unresponsive=',len(row['unresponsive']))
(R/'evidence/parent_witnesses01.json').write_text(json.dumps(dict(cases=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),physics_steps=0),indent=2)+'\n')
