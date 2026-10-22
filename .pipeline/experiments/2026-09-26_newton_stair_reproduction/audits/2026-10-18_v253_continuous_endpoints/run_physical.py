"""The single authorized A02 formal attempt, serially and without retries."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent;VERSION=HERE.parents[1]/'versions/v255'
BASE=Path('/data/sun/vla_mppi_20261009');STATUS=HERE/'results/batch_status.json'
assert json.loads((VERSION/'manifest.json').read_text())['frozen']
for cid in ('A02',):
 assert not (BASE/'generalization_v255'/cid/'execution/physical_launch_once.json').exists(),cid
rows=[]
for cid in ('A02',):
 row=dict(case_id=cid,attempt=1,stage='running',started_utc_s=time.time(),
  native_manifest_sha256=hashlib.sha256((VERSION.parent/'v254/manifest.json').read_bytes()).hexdigest(),
  execution_manifest_sha256=hashlib.sha256((VERSION/'manifest.json').read_bytes()).hexdigest())
 rows.append(row);STATUS.write_text(json.dumps(rows,indent=2)+'\n')
 with (BASE/f'v255_{cid}_physical_attempt01.log').open('x') as log:
  code=subprocess.run([sys.executable,str(VERSION/'launch.py')],env=dict(os.environ,V255_CASE_ID=cid),stdout=log,stderr=subprocess.STDOUT).returncode
 row.update(stage='execution_closed_pending_analysis',process_exit_code=code,finished_utc_s=time.time())
 STATUS.write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
