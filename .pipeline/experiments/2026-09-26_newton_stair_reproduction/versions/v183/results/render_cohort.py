"""Resume missing render artifacts only; never rerun completed physics/video."""
from pathlib import Path
import json, os, subprocess, sys, time, hashlib
import psutil
HERE=Path(__file__).resolve().parents[1]
VERSIONS=HERE.parent
ROOT=Path('/private/tmp/vla_policy_stop_20261012')
os.environ.update(V179_TEMP_ROOT=str(ROOT),PYTHONPATH='/private/tmp/vla_stop_audit_20261012/host_python',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
with (ROOT/'render183_resume_20261013.jsonl').open('x') as ledger:
 for terrain in ('flat','stairs'):
  for attempt in range(1,7):
   run=f'v182_{terrain}{attempt:02d}';out=ROOT/'render183'/run
   proof=out/'video_verification.json'
   if proof.exists():
    d=json.loads(proof.read_text());video=out/'newton_stair_recorded.mp4'
    assert hashlib.sha256(video.read_bytes()).hexdigest()==d['sha256']
    r=dict(run=run,status='existing_closed_video_preserved')
   else:
    assert not out.exists(),f'Partial render needs separate inspection: {out}'
    assert psutil.virtual_memory().available >= 8*1024**3
    name='v183_render_'+run[5:]
    command=[sys.executable,str(VERSIONS/'v182/supervise.py'),'--run-id',name,'--deadline','600','--',sys.executable,str(HERE/'render.py'),'--run',str(ROOT/'runs'/run),'--output',str(out),'--archive-receipt',str(ROOT/'receipts182'/(run+'.json'))]
    print('RENDER',run,flush=True)
    with (ROOT/(name+'_supervisor.log')).open('x') as stream:
     result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=630)
    r=dict(run=run,status='render_closed',exit_code=result.returncode)
    if result.returncode:raise RuntimeError(r)
   r['epoch']=time.time();ledger.write(json.dumps(r)+'\n');ledger.flush();print(json.dumps(r),flush=True)
(ROOT/'render183_resume_complete.json').write_text(json.dumps(dict(complete=True,epoch=time.time()))+'\n')
