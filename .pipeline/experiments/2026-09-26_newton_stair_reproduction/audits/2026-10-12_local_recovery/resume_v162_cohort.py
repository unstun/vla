"""Resume unchanged v162 after the preserved slot02 port-preflight failure."""
from pathlib import Path
import json,socket,subprocess,sys,time
BASE=Path(__file__).resolve().parents[2];V=BASE/'versions/v162';T=Path('/data/sun/vla_mppi_20261009');OUT=T/'results/v162_full_repeats'
# Physical cohort is attempt01 plus attempts03-06. Slot02 never ran physics.
for attempt in [3,4,5,6]:
 deadline=time.monotonic()+120
 while True:
  unavailable=[]
  for port in [46200,46201,46202,46203,8785]:
   try:
    with socket.socket() as s:s.bind(('127.0.0.1',port))
   except OSError:unavailable.append(port)
  if not unavailable:break
  if time.monotonic()>deadline:raise RuntimeError('Existing listeners or TIME_WAIT; no launch: '+str(unavailable))
  time.sleep(5)
 with (OUT/f'attempt{attempt:02d}.log').open('x') as log:
  r=subprocess.run([sys.executable,str(V/'run_remote_full.py'),'--variant','candidate','--attempt',str(attempt)],stdout=log,stderr=subprocess.STDOUT)
  if not (T/f'trials/v162_full_candidate_attempt{attempt:02d}/evidence/execution.json').exists():raise RuntimeError('Admission failed before physics')
  c=subprocess.run([sys.executable,str(V/'close_trial.py'),'--attempt',str(attempt)],stdout=log,stderr=subprocess.STDOUT)
 if c.returncode:raise RuntimeError('Closeout failed')
 result=json.loads((OUT/f'v162_full_candidate_attempt{attempt:02d}/outcome.json').read_text());print(json.dumps(result),flush=True)
 if r.returncode or 'analysis_error' in result:raise RuntimeError('Infrastructure failure; preserve and diagnose')
