from pathlib import Path
import argparse,hashlib,json,platform
from ament_index_python.packages import get_package_prefix
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--image-id',required=True);a=p.parse_args();assert platform.machine()=='aarch64'
t=Path('/task');w=t/'recovery_v184';parent=t/'evidence/v176_native_receipt.json';r=json.loads(parent.read_text());assert r['native_version']=='v176' and r['image_id']==a.image_id
for n,h in r['files'].items():assert sha(Path(n))==h,n
source=json.loads((w/'source_identity.json').read_text());assert source['version']=='v184'
for n,h in source['files'].items():assert sha(w/n)==h,n
assert get_package_prefix('lite3_nav2_bridge')==str(w/'install/lite3_nav2_bridge')
assert get_package_prefix('pct_planner')==str(t/'recovery_v174/install/pct_planner')
assert get_package_prefix('lite3_nav2_plugins')==str(t/'recovery_v172/install/lite3_nav2_plugins')
assert get_package_prefix('scan_planner')==str(t/'recovery_v167/install/scan_planner')
assert get_package_prefix('scan_nav2_controller')==str(w/'install/scan_nav2_controller')
log=t/'evidence/v184_native_build.log';text=log.read_text();assert '2 packages finished' in text and 'V184_TERMINAL_CAPTURE_PASS' in text
files=dict(r['files'])
for directory in ['src','install']:
 for f in (w/directory).rglob('*'):
  if f.is_file() and '__pycache__' not in f.parts:files[str(f)]=sha(f)
files[str(w/'source_identity.json')]=sha(w/'source_identity.json')
out={'passed':True,'platform':'linux/arm64','ros_distro':'foxy','variant':'candidate','native_version':'v184','image_id':a.image_id,'files':files,'source_identity_sha256':sha(w/'source_identity.json'),'underlay_receipt_sha256':sha(parent),'underlay_native_version':'v176','test_log_sha256':sha(log),'tests':{'controller_colcon_reexecuted':True,'terminal_capture_recorded_fixture':True,'generated_profile_cases':2},'claim':'Command counterfactual and profile configuration; physical recovery not established.'}
f=t/'evidence/v184_native_receipt.json';f.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'passed':True,'files':len(files),'receipt_sha256':sha(f)}))
