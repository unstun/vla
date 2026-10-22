"""Wait for all owned formal runs to close, then analyze without physics contention."""
from pathlib import Path
import json,subprocess,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
until=time.monotonic()+2800
while True:
 try:rows=json.loads((HERE/'results/batch_status.json').read_text())
 except (FileNotFoundError,json.JSONDecodeError):rows=[]
 if len(rows)==3 and all(r['stage']!='running' for r in rows):break
 if time.monotonic()>until:raise RuntimeError('Formal batch did not close within its bound')
 time.sleep(3)
python='/home/sun/vla_exec/envs/newton_worker/bin/python'
with (BASE/'v252_postprocess_batch01.log').open('x') as log:
 code=subprocess.run([python,str(HERE/'postprocess_three.py')],stdout=log,stderr=subprocess.STDOUT).returncode
print(json.dumps(dict(postprocess_batch_exit_code=code)),flush=True)
with (BASE/'v252_raw_pose_audit01.log').open('x') as log:
 code=subprocess.run([python,str(HERE/'raw_pose_audit.py')],stdout=log,stderr=subprocess.STDOUT).returncode
print(json.dumps(dict(raw_pose_exit_code=code)),flush=True)
