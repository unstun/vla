"""Wait for the one formal run to close, then analyze/render without contention."""
from pathlib import Path
import json,subprocess,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');until=time.monotonic()+1200
while True:
 try:rows=json.loads((HERE/'results/batch_status.json').read_text())
 except (FileNotFoundError,json.JSONDecodeError):rows=[]
 if len(rows)==1 and rows[0]['stage']!='running':break
 if time.monotonic()>until:raise RuntimeError('Formal attempt did not close within its bound')
 time.sleep(3)
worker='/home/sun/vla_exec/envs/newton_worker/bin/python';steps=[]
for name,script in [('postprocess','postprocess.py'),('raw_pose_audit','raw_pose_audit.py')]:
 if name=='raw_pose_audit' and not (HERE/'physical/A02/body_poses.txt').exists():break
 with (BASE/('v255_'+name+'_supervisor01.log')).open('x') as log:
  code=subprocess.run([worker,str(HERE/script)],stdout=log,stderr=subprocess.STDOUT).returncode
 row=dict(step=name,exit_code=code,physics_steps=0);steps.append(row)
 (HERE/'results/processing_status.json').write_text(json.dumps(steps,indent=2)+'\n');print(json.dumps(row),flush=True)
