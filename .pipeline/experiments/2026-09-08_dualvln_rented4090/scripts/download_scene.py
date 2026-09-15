import hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
meta=json.loads((root/'setup/habitat_scene_source.json').read_text())
dest=root/'data/habitat_test_scenes';dest.mkdir(parents=True,exist_ok=True)
rows=[]
for item in meta['files']:
 if item['type']!='file' or item['path'] not in ['apartment_1.glb','apartment_1.navmesh','README.md']:continue
 p=dest/item['path']
 url=f'https://huggingface.co/datasets/{meta["repo"]}/resolve/{meta["revision"]}/{item["path"]}'
 subprocess.run(['curl','-fL','--retry','3','--connect-timeout','15','--max-time','600','-C','-','-o',str(p),url],check=True)
 assert p.stat().st_size==item['size'],p
 sha=hashlib.sha256(p.read_bytes()).hexdigest()
 expected=item.get('lfs',{}).get('oid')
 assert not expected or sha==expected,p
 rows.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha,'upstream_lfs_sha256':expected})
(root/'setup/scene_manifest.json').write_text(json.dumps({'repo':meta['repo'],'revision':meta['revision'],'files':rows},indent=2)+'\n')
print('SCENE_VERIFIED')
