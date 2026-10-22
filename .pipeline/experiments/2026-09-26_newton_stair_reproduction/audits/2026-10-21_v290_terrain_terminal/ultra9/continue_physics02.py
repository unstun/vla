"""Continue only never-started routes after a recorded scan-deadline abort."""
from pathlib import Path
import fcntl,hashlib,json,os,subprocess,sys,time
ROOT=Path('/home/ubuntu/sun/vla_v290_20261021')
M=ROOT/'migration'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)
def recorded(raw):
 p=raw/'result.json'
 if p.exists():return json.loads(p.read_text())['physics_steps'],'result.json'
 p=raw/'telemetry.jsonl'
 if p.exists():
  with p.open('rb') as f:f.seek(max(0,p.stat().st_size-32000));lines=f.read().splitlines()
  return json.loads(lines[-1])['physics_steps'],'last recorded telemetry (lower bound; result missing)'
 return None,None
def main():
 import batch
 frozen=M/'physical_manifest01.json';ids=json.loads(frozen.read_text())['physical_cases']
 original=ROOT/'evidence/physical_batch_status.json';prior=json.loads(original.read_text())
 assert [r['case_id'] for r in prior]==ids[:2]
 failure=ROOT/'physical_runs/v290_G05_attempt01/runs/v290_G05_attempt01'
 assert 'Captured scan did not finish before the next sensor period' in (failure/'run.log').read_text()
 rows=[]
 for previous in prior:
  cid=previous['case_id'];raw=ROOT/'physical_runs'/f'v290_{cid}_attempt01'/'runs'/f'v290_{cid}_attempt01'
  steps,source=recorded(raw);assert steps and steps>0
  ledger=ROOT/'generalization_v290'/cid/'execution/physical_launch_once.json';assert ledger.exists()
  rows.append(dict(previous,stage='closed',formal_attempt_started=True,physics_steps=steps,
   physics_steps_source=source,recording_complete=(raw/'result.json').exists(),
   terminal_exception='scan_deadline_exceeded' if cid=='G05' else None,original_batch_stage=previous['stage']))
 receipt=ROOT/'evidence/physical_batch_continuation02.json'
 assert not receipt.exists()
 save(receipt,dict(original_status_sha256=sha(original),original_status=prior,
  no_retries=True,preserved_aborted_case='G05',remaining_cases=ids[2:],navigation_unchanged=True))
 status=ROOT/'evidence/physical_batch_continuation02_status.json'
 with (ROOT/'evidence/physical_batch.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  save(status,rows)
  for cid in ids[2:]:
   ledger=ROOT/'generalization_v290'/cid/'execution/physical_launch_once.json'
   task=ROOT/'physical_runs'/f'v290_{cid}_attempt01'
   assert not ledger.exists() and not task.exists(),'Never retry an existing invocation'
   row=dict(case_id=cid,stage='starting',manifest_sha256=sha(frozen),started_utc_s=time.time())
   rows.append(row);save(status,rows)
   log=ROOT/'evidence'/f'physical_{cid}_attempt01.log'
   with log.open('x') as stream:
    code=subprocess.run([sys.executable,str(M/'physical.py')],env=dict(os.environ,V290_CASE_ID=cid),stdout=stream,stderr=subprocess.STDOUT).returncode
   raw=task/'runs'/task.name;steps,source=recorded(raw)
   row.update(exit_code=code,physics_steps=steps,physics_steps_source=source,
    formal_attempt_started=bool(steps and steps>0),stage='closed' if steps and steps>0 and ledger.exists() else 'startup_failure',
    recording_complete=(raw/'result.json').exists(),finished_utc_s=time.time(),log_sha256=sha(log))
   save(status,rows);print(json.dumps(row),flush=True)
   if row['stage']!='closed':raise SystemExit('Preserve startup failure; no automatic retry')
 save(ROOT/'evidence/physical_batch_complete.json',dict(cases=10,attempts_per_case=1,
  positive_physics_recordings=10,all_closed=True,manifest_sha256=sha(frozen),
  incomplete_recordings=[r['case_id'] for r in rows if not r['recording_complete']],
  status_source=str(status),original_status_preserved_sha256=sha(original)))
if __name__=='__main__':main()
