"""Five sequential trials; closed failures count and are retained."""
from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent
TASK=Path('/data/sun/vla_mppi_20261009')
def main():
 out=TASK/'results/v162_full_repeats';out.mkdir(exist_ok=False)
 for attempt in range(1,6):
  with (out/f'attempt{attempt:02d}.log').open('w') as log:
   r=subprocess.run([sys.executable,str(HERE/'run_remote_full.py'),'--variant','candidate','--attempt',str(attempt)],stdout=log,stderr=subprocess.STDOUT)
   if not (TASK/f'trials/v162_full_candidate_attempt{attempt:02d}/evidence/execution.json').exists():raise RuntimeError('Admission failed; do not proceed: '+str(attempt))
   c=subprocess.run([sys.executable,str(HERE/'close_trial.py'),'--attempt',str(attempt)],stdout=log,stderr=subprocess.STDOUT)
  if c.returncode:raise RuntimeError('Closeout failed; preserve before next trial')
  summary=json.loads((out/f'v162_full_candidate_attempt{attempt:02d}/outcome.json').read_text());print(json.dumps(summary),flush=True)
  if r.returncode or 'analysis_error' in summary:raise RuntimeError('Infrastructure failure; diagnose before next trial')
if __name__=='__main__':main()
