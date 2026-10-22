"""Analyze and deliver every actual attempt after physics; no replayed actuation."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
from watch_resources import sample
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
  results.append(dict(case_id=cid,exit_code=0,already_delivered=True,physics_steps=0))
  continue
 while not sample()['passed']:time.sleep(60)
 with (BASE/f'v282_{cid}_analysis01.log').open('x') as log:
  code=subprocess.run([sys.executable,str(HERE/'postprocess_case.py')],env=dict(os.environ,V282_CASE_ID=cid),stdout=log,stderr=subprocess.STDOUT).returncode
 results.append(dict(case_id=cid,exit_code=code,wall_s=time.monotonic()-began,physics_steps=0))
 (HERE/'results/analysis_batch_status.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results[-1]),flush=True)
 if code:raise SystemExit('Analysis failed; retain this log and repair tooling before resuming')
