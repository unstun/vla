"""Bind the changed controller overlay to its verified unchanged v158 underlay."""
from pathlib import Path
import argparse,hashlib,json,platform
from ament_index_python.packages import get_package_prefix
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--image-id',required=True);a=p.parse_args()
assert platform.machine()=='aarch64'
task=Path('/task');workspace=task/'recovery_v159';parent_path=task/'evidence/v158_native_receipt.json'
parent=json.loads(parent_path.read_text());assert parent['native_version']=='v158' and parent['image_id']==a.image_id
for n,h in parent['files'].items():assert sha(Path(n))==h,n
source=json.loads((workspace/'source_identity.json').read_text());assert source['version']=='v159'
for n,h in source['files'].items():assert sha(workspace/n)==h,n
log=task/'evidence/v159_native_build02.log';assert '39 tests, 0 errors, 0 failures' in log.read_text()
prefix=get_package_prefix('scan_nav2_controller');planner=get_package_prefix('scan_planner')
assert prefix=='/task/recovery_v159/install/scan_nav2_controller',prefix
assert planner=='/task/recovery_v158/install/scan_planner',planner
files=dict(parent['files'])
for directory in ['src','install']:
 for f in (workspace/directory).rglob('*'):
  if f.is_file() and '__pycache__' not in f.parts:files[str(f)]=sha(f)
files[str(workspace/'source_identity.json')]=sha(workspace/'source_identity.json')
receipt={'passed':True,'platform':'linux/arm64','ros_distro':'foxy','variant':'candidate','native_version':'v159','image_id':a.image_id,'files':files,'source_identity_sha256':sha(workspace/'source_identity.json'),'test_log_sha256':sha(log),'underlay_receipt_sha256':sha(parent_path),'underlay_native_version':'v158','selected_controller_prefix':prefix,'selected_planner_prefix':planner,'tests':{'new_controller_overlay':39,'unchanged_underlay_terrain':2}}
out=task/'evidence/v159_native_receipt.json';out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'files':len(files),'receipt_sha256':sha(out),'controller':prefix,'planner':planner}))
