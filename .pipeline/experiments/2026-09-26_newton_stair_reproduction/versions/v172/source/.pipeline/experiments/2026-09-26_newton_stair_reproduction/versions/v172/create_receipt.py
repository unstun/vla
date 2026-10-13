from pathlib import Path
import argparse,hashlib,json,platform
from ament_index_python.packages import get_package_prefix
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--image-id',required=True);a=p.parse_args();assert platform.machine()=='aarch64'
t=Path('/task');w=t/'recovery_v172';parent=t/'evidence/v170_native_receipt.json';r=json.loads(parent.read_text());assert r['native_version']=='v170' and r['image_id']==a.image_id
for n,h in r['files'].items():assert sha(Path(n))==h,n
source=json.loads((w/'source_identity.json').read_text());assert source['version']=='v172'
for n,h in source['files'].items():assert sha(w/n)==h,n
for n in ['lite3_nav2_bridge','lite3_nav2_plugins']:assert get_package_prefix(n)==str(w/'install'/n)
for n in ['scan_planner','scan_nav2_controller']:assert get_package_prefix(n)==str(t/'recovery_v167/install'/n)
log=t/'evidence/v172_native_build.log';text=log.read_text();assert '13 tests, 0 errors, 0 failures' in text and 'Ran 9 tests' in text and '\nOK\n' in text
files=dict(r['files'])
for directory in ['src','install']:
 for f in (w/directory).rglob('*'):
  if f.is_file() and '__pycache__' not in f.parts:files[str(f)]=sha(f)
files[str(w/'source_identity.json')]=sha(w/'source_identity.json')
out={'passed':True,'platform':'linux/arm64','ros_distro':'foxy','variant':'candidate','native_version':'v172','image_id':a.image_id,'files':files,'source_identity_sha256':sha(w/'source_identity.json'),'underlay_receipt_sha256':sha(parent),'underlay_native_version':'v170','test_log_sha256':sha(log),'tests':{'controller_colcon_inherited':42,'plugins_colcon':13,'gateway_callbacks':9}}
f=t/'evidence/v172_native_receipt.json';f.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'passed':True,'files':len(files),'receipt_sha256':sha(f)}))
