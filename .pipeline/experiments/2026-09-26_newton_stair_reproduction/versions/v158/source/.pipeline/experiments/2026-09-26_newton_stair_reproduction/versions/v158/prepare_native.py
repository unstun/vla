"""Materialize two explicit changes on the hash-verified v151 native export."""
from pathlib import Path
import argparse,hashlib,json,shutil
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--task-root',type=Path,required=True);a=p.parse_args()
 root=a.task_root.resolve();parent=root/'recovery_v151';target=root/'recovery_v158'
 record=json.loads((parent/'source_identity.json').read_text());assert record['version']=='v151'
 target.mkdir(exist_ok=False);files=dict(record['files'])
 for name,digest in files.items():
  assert sha(parent/name)==digest,name
  (target/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(parent/name,target/name)
 changed=['src/plan_manage/include/plan_manage/scan_replan_fsm.h','src/plan_manage/src/scan_replan_fsm.cpp']
 for name in changed:
  assert sha(HERE/name)!=files[name];shutil.copyfile(HERE/name,target/name);files[name]=sha(target/name)
 assert sorted(n for n in files if files[n]!=record['files'][n])==sorted(changed)
 (target/'source_identity.json').write_text(json.dumps({'version':'v158','native_parent':'v151','parent_source_identity_sha256':sha(parent/'source_identity.json'),'changes':changed,'files':files},indent=2)+'\n')
 print(json.dumps({'source_files':len(files),'changes':changed}))
if __name__=='__main__':main()
