"""Analyze/render each closed formal attempt; never start or retry physics."""
from pathlib import Path
import json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
rows=json.loads((HERE/'results/batch_status.json').read_text())
assert len(rows)==3 and all(r['stage']!='running' for r in rows)
results=[]
for cid in ('A02','G07','R11'):
 began=time.time()
 with (BASE/f'v252_{cid}_postprocess01.log').open('x') as log:
  code=subprocess.run([sys.executable,str(HERE/'postprocess_case.py')],env=dict(os.environ,V252_CASE_ID=cid),stdout=log,stderr=subprocess.STDOUT).returncode
 results.append(dict(case_id=cid,returncode=code,wall_s=time.time()-began))
 (HERE/'results/postprocess_status.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps(results[-1]),flush=True)
