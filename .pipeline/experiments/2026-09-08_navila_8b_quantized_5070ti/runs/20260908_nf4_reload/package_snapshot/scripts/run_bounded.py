"""Run a task-owned inference process with provenance and a wall deadline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

parser=argparse.ArgumentParser()
parser.add_argument('run_id')
parser.add_argument('--reload',action='store_true')
parser.add_argument('--limit',type=int,default=12)
args=parser.parse_args()
if not args.run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.run_id):
    parser.error('Invalid run identifier')
root=Path(__file__).resolve().parents[1]
run=root/'runs'/args.run_id
run.mkdir(parents=True,exist_ok=False)
source_manifest=json.loads((root/'setup/work_source_manifest.json').read_text())
for item in source_manifest['files']:
    path=root/'work/NaVILA'/item['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],str(path)
package_manifest=json.loads((root/'setup/package_manifest.json').read_text())
for item in package_manifest['files']:
    assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
(run/'sync_gate.json').write_text(json.dumps({'passed':True,
 'source_files':len(source_manifest['files']), 'package_files':len(package_manifest['files'])},indent=2))
for name in ['work_source_manifest.json','package_manifest.json','compatibility.patch','original_weight_manifest.json']:
    (run/name).write_bytes((root/'setup'/name).read_bytes())
model=root/'models'/('navila-nf4' if args.reload else 'navila-llama3-8b-8f')
cmd=[str(root/'venv/bin/python'),'-u',str(root/'scripts/probe.py'),
 '--model',str(model),'--source',str(root/'work/NaVILA'),
 '--fixtures',str(root/'fixtures'),'--output',str(run/'results'),'--limit',str(args.limit)]
if not args.reload:cmd+=['--export',str(root/'models/navila-nf4')]
stop=threading.Event()
def sample():
    with (run/'gpu_samples.jsonl').open('w') as stream:
        while not stop.is_set():
            result=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu,power.draw',
                                   '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
            stream.write(json.dumps({'unix_time':time.time(),'gpu':result.stdout.strip(),
                                     'exit_code':result.returncode})+'\n');stream.flush()
            stop.wait(0.5)
thread=threading.Thread(target=sample,daemon=True);thread.start()
start=time.monotonic();timed_out=False
env=dict(os.environ,TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
with (run/'stdout.log').open('w') as stdout,(run/'stderr.log').open('w') as stderr:
    process=subprocess.Popen(cmd,cwd=root,stdout=stdout,stderr=stderr,env=env,start_new_session=True)
    (run/'process.json').write_text(json.dumps({'pid':process.pid,'pgid':process.pid,
              'command':cmd,'started_unix':time.time()},indent=2))
    try:code=process.wait(timeout=600)
    except subprocess.TimeoutExpired:
        timed_out=True;os.killpg(process.pid,signal.SIGTERM)
        try:code=process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);code=process.wait()
stop.set();thread.join(timeout=15)
meta={'exit_code':code,'timed_out':timed_out,'wall_seconds':time.monotonic()-start,
      'command':cmd,'reload':args.reload}
(run/'meta.json').write_text(json.dumps(meta,indent=2))
files=[]
for path in sorted(run.rglob('*')):
    if path.is_file():files.append({'path':path.relative_to(run).as_posix(),
                'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(run/'artifact_manifest.json').write_text(json.dumps({'files':files},indent=2))
print(json.dumps(meta),flush=True)
raise SystemExit(code if code>=0 else 128-code)
