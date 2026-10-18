"""Resume only offline evidence/video steps after first renderer path rejection."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
PREFIX=Path('/data/sun/vla_mppi_20261009')
def main():
    execution=json.loads((BASE/'versions/v237/execution.json').read_text())
    assert execution['run']=='v237_linux_full_attempt01' and execution['process_exit_code']==0
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        PATH='/home/sun/vla_exec/envs/newton_worker/bin:'+str(BASE/'versions/v233/bin')+':'+os.environ['PATH'])
    reports=[]
    for name in ['analyze.py','render_run.py','run_margin.py','compare.py','deliver.py']:
        with (PREFIX/'evidence'/('v237_'+name.replace('.py','')+'02.log')).open('x') as log:
            started=time.monotonic();result=subprocess.run([sys.executable,'-u',str(HERE/name)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
        reports.append(dict(script=name,exit_code=result.returncode,wall_s=time.monotonic()-started))
        (HERE/'results/postprocess_steps02.json').write_text(json.dumps(reports,indent=2)+'\n')
        print(json.dumps(reports[-1]),flush=True)
        if result.returncode:raise SystemExit(result.returncode)
if __name__=='__main__':main()
