"""Archive closed owned evidence with per-file hashes; never use GPU compute."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--case',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
root=args.root.resolve()
assert root.is_relative_to('/private/tmp') and args.case.replace('_','').replace('-','').isalnum()
def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()
files={str(path.relative_to(root)):{'bytes':path.stat().st_size,'sha256':sha(path)}
       for path in root.rglob('*') if path.is_file() and not path.is_symlink()}
destination='/home/sun/vla_artifacts/2026-10-05_safe_mapping_repair/'+args.case
args.output.mkdir(parents=True,exist_ok=True)
manifest={'local_root':str(root),'remote_root':destination,'files':files,
          'bytes':sum(row['bytes'] for row in files.values()),'gpu_job_started':False}
path=args.output/(args.case+'_storage.json')
path.write_text(json.dumps(manifest,indent=2)+'\n')
listing=args.output/(args.case+'_transfer.txt')
listing.write_text(''.join(name+'\n' for name in sorted(files)))
subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','gpu5070ti','mkdir -p '+destination],check=True,timeout=30)
subprocess.run(['rsync','-a','--files-from='+str(listing),'-e','ssh -o BatchMode=yes -o ConnectTimeout=10',
                str(root)+'/','gpu5070ti:'+destination+'/'],check=True,timeout=900)
subprocess.run(['scp','-q',str(path),'gpu5070ti:'+destination+'/storage_manifest.json'],check=True,timeout=30)
code='''from pathlib import Path
import hashlib,json,sys,time
manifest=json.loads(Path(sys.argv[1]).read_text())
for name,row in manifest['files'].items():
 path=Path(manifest['remote_root'])/name
 assert path.stat().st_size==row['bytes'],name
 digest=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
 assert digest.hexdigest()==row['sha256'],name
print(json.dumps({'passed':True,'files':len(manifest['files']),'bytes':manifest['bytes'],'verified_epoch_s':time.time(),'gpu_job_started':False}))
'''
checked=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','gpu5070ti',
                        'python3 - '+destination+'/storage_manifest.json'],input=code,capture_output=True,text=True,check=True,timeout=60)
verification=json.loads(checked.stdout)
(args.output/(args.case+'_remote_verification.json')).write_text(json.dumps(verification,indent=2)+'\n')
print(json.dumps(verification))
