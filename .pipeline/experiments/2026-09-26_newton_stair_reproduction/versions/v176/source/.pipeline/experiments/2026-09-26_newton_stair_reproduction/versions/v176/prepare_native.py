from pathlib import Path
import argparse,hashlib,json,shutil
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--task-root',type=Path,required=True);a=p.parse_args();parent=a.task_root/'recovery_v174';target=a.task_root/'recovery_v176';target.mkdir(exist_ok=False)
r=json.loads((parent/'source_identity.json').read_text());assert r['version']=='v174';files=dict(r['files'])
for n,h in files.items():
 assert sha(parent/n)==h,n
 (target/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(parent/n,target/n)
changed=[]
for f in (HERE/'src').rglob('*'):
 if f.is_file():
  n=str(f.relative_to(HERE));(target/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target/n);files[n]=sha(f);changed.append(n)
(target/'source_identity.json').write_text(json.dumps({'version':'v176','native_parent':'v174','parent_source_identity_sha256':sha(parent/'source_identity.json'),'changes':changed,'files':files},indent=2)+'\n');print(json.dumps({'files':len(files),'changed':changed}))
