"""Hash closed raw recordings in place; never delete or replace physical evidence."""
from pathlib import Path
import hashlib,json,sys,time
CAMPAIGN=Path('/home/ubuntu/sun/vla_v291_pair24_20261022')
sys.path.insert(0,str(CAMPAIGN/'source'))
from common import verify

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def main():
 complete=json.loads((CAMPAIGN/'evidence/batch_complete.json').read_text())
 slots=json.loads((CAMPAIGN/'evidence/batch_status.json').read_text())
 assert complete['completed']==24 and len(slots)==24 and all(r['state']=='closed' and r['physics_steps']>0 for r in slots)
 verification=verify();records=[];full={}
 for slot in slots:
  run=slot['run'];root=CAMPAIGN/'physical_runs'/run;files={}
  for p in sorted(root.rglob('*')):
   if not p.is_file():continue
   before=p.stat();digest=sha(p);after=p.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),p
   files[str(p.relative_to(root))]={'bytes':before.st_size,'sha256':digest}
  assert files
  full[run]=files;records.append(dict(run=run,files=len(files),bytes=sum(r['bytes'] for r in files.values()),physics_steps=slot['physics_steps'],raw_root=str(root)))
  print(json.dumps(records[-1]),flush=True)
 out=CAMPAIGN/'analysis';manifest=out/'raw_manifest.json';manifest.write_text(json.dumps(full,indent=2)+'\n')
 receipt=dict(verified_utc_s=time.time(),frozen_sources=verification,recordings=24,all_positive_physics=True,raw_manifest_path=str(manifest),raw_manifest_sha256=sha(manifest),raw_files=sum(r['files'] for r in records),raw_bytes=sum(r['bytes'] for r in records),runs=records,retention='Original expanded recordings preserved on ultra9; original retention helper errors are retained. No deletion, replacement, physics retries or new physics steps.')
 (out/'preservation_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
