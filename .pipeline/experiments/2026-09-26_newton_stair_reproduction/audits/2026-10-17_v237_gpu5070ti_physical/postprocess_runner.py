"""Wait for the one owned route, then preserve/analyze/render/package it only."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
PREFIX=Path('/data/sun/vla_mppi_20261009')
RUN='v237_linux_full_attempt01'
RAW=PREFIX/'trials'/RUN/'runs'/RUN

def main():
    deadline=time.monotonic()+1000
    execution=BASE/'versions/v237/execution.json'
    while True:
        if execution.exists():
            row=json.loads(execution.read_text())
            if row.get('run')==RUN:break
        if time.monotonic()>deadline:raise TimeoutError('Owned route did not close within its declared supervisor window')
        time.sleep(5)
    assert (RAW/'process.json').exists()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        PATH='/home/sun/vla_exec/envs/newton_worker/bin:'+str(BASE/'versions/v233/bin')+':'+os.environ['PATH'])
    steps=['preserve.py','analyze.py']
    steps+=['render_run.py' if (RAW/'result.json').exists() else 'render_partial.py','run_margin.py','compare.py','deliver.py']
    reports=[]
    for name in steps:
        with (PREFIX/'evidence'/('v237_'+name.replace('.py','')+'01.log')).open('x') as log:
            started=time.monotonic()
            result=subprocess.run([sys.executable,'-u',str(HERE/name)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
        reports.append(dict(script=name,exit_code=result.returncode,wall_s=time.monotonic()-started))
        (HERE/'results/postprocess_steps.json').write_text(json.dumps(reports,indent=2)+'\n')
        print(json.dumps(reports[-1]),flush=True)
        if result.returncode:raise SystemExit(result.returncode)

if __name__=='__main__':main()
