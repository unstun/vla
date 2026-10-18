"""Run real zero-step scanner/policy and graph gates before one physical trial."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
PREFIX=Path('/data/sun/vla_mppi_20261009')
EVIDENCE=PREFIX/'evidence'

def main():
    EVIDENCE.mkdir(exist_ok=True)
    env=os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        PATH=str(HERE.parent/'v233/bin')+':'+env['PATH'],
        WARP_CACHE_PATH=str(PREFIX/'v237_scan_probe_cache'))
    commands=[
        ('tests01',[sys.executable,str(HERE/'test_scan_deadline.py')]),
        ('scan_probe01',[sys.executable,str(HERE/'probe_scans.py'),'--output',str(EVIDENCE/'v237_scan_probe01.json'),'--scans','50','--fixed','--flexible']),
        ('preflight01',[sys.executable,str(HERE/'launch.py'),'--preflight-only'])]
    reports=[]
    for name,command in commands:
        with (EVIDENCE/('v237_'+name+'.log')).open('x') as log:
            started=time.monotonic()
            result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
        reports.append(dict(name=name,command=command,exit_code=result.returncode,wall_s=time.monotonic()-started))
        (EVIDENCE/'v237_preflight_steps.json').write_text(json.dumps(reports,indent=2)+'\n')
        print(json.dumps(reports[-1]),flush=True)
        if result.returncode:raise SystemExit(result.returncode)
    (EVIDENCE/'v237_preflight_passed.json').write_text(json.dumps(dict(passed=True,physics_steps=0,steps=reports),indent=2)+'\n')

if __name__=='__main__':main()
