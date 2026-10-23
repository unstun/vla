"""Run exactly the frozen24 slots sequentially, preserving every physical failure."""
from common import *
import fcntl,subprocess,time,sys,zipfile

def save(p,data):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(p)

def sample(raw):
 if (raw/'result.json').exists():
  d=json.loads((raw/'result.json').read_text());return {'physics_steps':d.get('physics_steps'), 'result_present':True,'terminal':(d.get('finish_request') or {}).get('backend_terminal_status'),'fallen':d.get('fallen')}
 path=raw/'telemetry.jsonl'
 if path.exists():
  with path.open('rb') as f:f.seek(max(0,path.stat().st_size-20000));lines=f.read().splitlines()
  for line in reversed(lines):
   try:
    r=json.loads(line);return {'physics_steps':r.get('physics_steps',0),'physics_time_s':r.get('physics_time_s'),'stance_mode':r.get('stance_mode'),'result_present':False}
   except (ValueError,KeyError):continue
 archive=raw/'raw_capture.zip'
 if archive.exists():
  with zipfile.ZipFile(archive) as z:
   if 'result.json' in z.namelist():
    d=json.loads(z.read('result.json'));return {'physics_steps':d.get('physics_steps'),'result_present':True,'terminal':(d.get('finish_request') or {}).get('backend_terminal_status'),'fallen':d.get('fallen')}
 return {'physics_steps':0,'result_present':False}

def main():
 manifest=BINDING/'campaign_manifest.json';m=json.loads(manifest.read_text());assert m['frozen'] and m['authorized_physical_runs']==24
 status=CAMPAIGN/'evidence/batch_status.json';rows=json.loads(status.read_text()) if status.exists() else []
 with (CAMPAIGN/'evidence/batch.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for slot in m['request']['schedule']:
   old=next((r for r in rows if r['index']==slot['index']),None)
   if old and old['state']=='closed':continue
   assert old is None,'Inspect incomplete invocation before resuming; no blind rerun'
   run=slot['run'];task=CAMPAIGN/'physical_runs'/run;assert not task.exists(),task
   verify();row=dict(slot,state='starting',started_utc_s=time.time(),load_average=list(os.getloadavg()),manifest_sha256=sha(manifest));rows.append(row);save(status,rows)
   env=dict(os.environ,PAIR_VARIANT=slot['variant'],PAIR_CASE=slot['case_id'],PAIR_REPEAT=str(slot['repeat']))
   log=CAMPAIGN/'evidence'/(run+'.log');print(json.dumps(dict(index=slot['index'],run=run,state='starting')),flush=True)
   with log.open('x') as f:
    process=subprocess.Popen([sys.executable,str(BINDING/'launch.py')],env=env,stdout=f,stderr=subprocess.STDOUT)
    inspected=False
    while process.poll() is None:
     live=sample(task/'runs'/run);save(CAMPAIGN/'evidence/live.json',dict(slot,**live,updated_utc_s=time.time(),load_average=list(os.getloadavg())))
     if not inspected and (CAMPAIGN/'evidence'/run/'physical_launch_once.json').exists():
      q=subprocess.run(['docker','inspect',run.lower().replace('_','-'),'--format','{{json .HostConfig}}'],capture_output=True,text=True)
      if q.returncode==0:
       cfg=json.loads(q.stdout);record={k:cfg.get(k) for k in ('NanoCpus','CpuPeriod','CpuQuota','CpusetCpus','Memory','NetworkMode')};assert record['NanoCpus']==6000000000 and record['Memory']==6*1024**3
       save(CAMPAIGN/'evidence'/run/'actual_resources.json',record);inspected=True
     time.sleep(5)
   final=sample(task/'runs'/run);row.update(final,exit_code=process.returncode,finished_utc_s=time.time(),log_sha256=sha(log),resource_inspected=inspected)
   row['state']='closed' if (final.get('physics_steps') or 0)>0 else 'startup_failure';save(status,rows);print(json.dumps(row),flush=True)
   if row['state']!='closed':raise SystemExit('Retained startup failure: diagnose without consuming another physical slot')
  verify();save(CAMPAIGN/'evidence/batch_complete.json',dict(completed=24,positive_physics_recordings=24,manifest_sha256=sha(manifest),finished_utc_s=time.time()))
if __name__=='__main__':main()
