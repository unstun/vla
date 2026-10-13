"""Repeat the unchanged frozen v177 after the endpoint candidates; never overwrite01-05."""
from pathlib import Path
import json,subprocess,sys,hashlib
TASK=Path('/data/sun/vla_mppi_20261009')
VERSION=TASK/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v177'
assert Path(__file__).resolve().is_relative_to(TASK)
subprocess.run([sys.executable,str(VERSION/'freeze_host.py'),'verify'],check=True)
out=TASK/'results/v177_endpoint_control';out.mkdir(exist_ok=False)
(out/'request.json').write_text(json.dumps({'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'frozen_version':'v177','manifest_sha256':hashlib.sha256((VERSION/'manifest.json').read_bytes()).hexdigest(),'attempts':[6,7,8,9,10],'purpose':'Contemporaneous unchanged-baseline comparison; no code or policy changes'},indent=2)+'\n')
for attempt in range(6,11):
 tag=f'v177_full_candidate_attempt{attempt:02d}'
 with (out/f'attempt{attempt:02d}.log').open('w') as log:
  run=subprocess.run([sys.executable,str(VERSION/'run_remote_full.py'),'--variant','candidate','--attempt',str(attempt)],stdout=log,stderr=subprocess.STDOUT)
  if not (TASK/'trials'/tag/'evidence/execution.json').is_file():raise RuntimeError('Admission failed; stop cohort')
  closed=subprocess.run([sys.executable,str(VERSION/'close_trial.py'),'--attempt',str(attempt)],stdout=log,stderr=subprocess.STDOUT)
 if closed.returncode:raise RuntimeError('Closeout failed')
 summary=json.loads((TASK/'results/v177_full_repeats'/tag/'outcome.json').read_text())
 print(json.dumps(summary),flush=True)
 if run.returncode or 'analysis_error' in summary:raise RuntimeError('Infrastructure failure; diagnose before next attempt')
