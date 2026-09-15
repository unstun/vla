"""Execute one task-owned command with a process-group deadline and raw logs."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--seconds',type=int,default=600);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
if not a.name.replace('_','').replace('-','').isalnum():p.error('Invalid job name')
root=Path(__file__).resolve().parents[1];out=root/'runs'/a.name;out.mkdir(parents=True,exist_ok=False)
cmd=a.command[1:] if a.command and a.command[0]=='--' else a.command
start=time.time();timed_out=False
with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
 proc=subprocess.Popen(cmd,cwd=root,stdout=stdout,stderr=stderr,start_new_session=True)
 (out/'process.json').write_text(json.dumps({'pid':proc.pid,'pgid':proc.pid,'command':cmd,'started_unix':start},indent=2)+'\n')
 try: code=proc.wait(timeout=a.seconds)
 except subprocess.TimeoutExpired:
  timed_out=True;os.killpg(proc.pid,signal.SIGTERM)
  try:code=proc.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
meta={'exit_code':code,'timed_out':timed_out,'wall_seconds':time.time()-start,'command':cmd}
(out/'meta.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta),flush=True)
raise SystemExit(code if code>=0 else 128-code)
