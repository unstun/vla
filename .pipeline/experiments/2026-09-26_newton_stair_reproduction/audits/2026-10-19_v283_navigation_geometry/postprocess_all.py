"""Analyze and deliver every actual attempt after physics; no replayed actuation."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
from render_resources import sample
from physical_support_margins import audit as audit_support
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
rows=json.loads((HERE/'results/physical_batch_status.json').read_text());results=[]
for row in rows:
 if not row['formal_attempt_started']:continue
 cid=row['case_id'];began=time.monotonic()
 receipt=HERE/'physical'/cid/'results/local_video_delivery.json'
 if receipt.exists():
  video=json.loads(receipt.read_text());path=Path(video['video'])
  assert path.is_file() and not path.is_symlink()
  assert hashlib.sha256(path.read_bytes()).hexdigest()==video['sha256']
  audit_support(cid)
  results.append(dict(case_id=cid,exit_code=0,already_delivered=True,physics_steps=0))
  continue
 while not sample()['passed']:time.sleep(60)
 number=next(n for n in range(1,1000) if not (BASE/f'v283_{cid}_analysis{n:02d}.log').exists())
 with (BASE/f'v283_{cid}_analysis{number:02d}.log').open('x') as log:
  code=subprocess.run(['nice','-n','10',sys.executable,str(HERE/'postprocess_case.py')],env=dict(os.environ,V283_CASE_ID=cid,V283_RENDER_ID=f'{number:02d}'),stdout=log,stderr=subprocess.STDOUT).returncode
 if code==0:audit_support(cid)
 results.append(dict(case_id=cid,exit_code=code,wall_s=time.monotonic()-began,physics_steps=0))
 (HERE/'results/analysis_batch_status.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results[-1]),flush=True)
 if code:raise SystemExit('Analysis failed; retain this log and repair tooling before resuming')
