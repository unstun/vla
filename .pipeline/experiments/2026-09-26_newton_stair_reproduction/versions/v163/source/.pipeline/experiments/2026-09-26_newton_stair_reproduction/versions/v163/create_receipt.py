from pathlib import Path
import argparse,hashlib,json,platform
from ament_index_python.packages import get_package_prefix
import lite3_nav2_bridge.gateway as gateway
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--image-id',required=True);a=p.parse_args();assert platform.machine()=='aarch64'
t=Path('/task');w=t/'recovery_v163';parent=t/'evidence/v160_native_receipt.json';r=json.loads(parent.read_text());assert r['native_version']=='v160' and r['image_id']==a.image_id
for n,h in r['files'].items():assert sha(Path(n))==h,n
source=json.loads((w/'source_identity.json').read_text());assert source['version']=='v163'
for n,h in source['files'].items():assert sha(w/n)==h,n
assert get_package_prefix('scan_nav2_controller')=='/task/recovery_v160/install/scan_nav2_controller'
for name in ['lite3_nav2_bridge','lite3_nav2_plugins']:assert get_package_prefix(name)==str(w/'install'/name)
assert Path(gateway.__file__).is_relative_to(w/'install/lite3_nav2_bridge') if hasattr(Path(gateway.__file__),'is_relative_to') else str(gateway.__file__).startswith(str(w/'install/lite3_nav2_bridge')+'/')
log=t/'evidence/v163_native_build.log';s=log.read_text();assert '5 tests, 0 errors, 0 failures' in s and 'Ran 9 tests' in s and '\nOK' in s
files=dict(r['files'])
for directory in ['src','install']:
 for f in (w/directory).rglob('*'):
  if f.is_file() and '__pycache__' not in f.parts:files[str(f)]=sha(f)
files[str(w/'source_identity.json')]=sha(w/'source_identity.json')
out={'passed':True,'platform':'linux/arm64','ros_distro':'foxy','variant':'candidate','native_version':'v163','image_id':a.image_id,'files':files,'source_identity_sha256':sha(w/'source_identity.json'),'underlay_receipt_sha256':sha(parent),'underlay_native_version':'v160','test_log_sha256':sha(log),'selected_gateway':gateway.__file__,'tests':{'controller_colcon_unchanged':40,'plugins_colcon':5,'gateway_python':9}}
f=t/'evidence/v163_native_receipt.json';f.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'passed':True,'files':len(files),'receipt_sha256':sha(f)}))
