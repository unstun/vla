"""Freeze the Linux display source without promoting navigation."""
from pathlib import Path
import argparse,hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 m=json.loads((H/'manifest.json').read_text())
 for n,e in m['source_files'].items():assert sha(R/n)==e and sha(R/m['snapshot_locations'][n])==e,n
 assert sha(H/'quality.json')==m['quality_sha256'] and sha(B/'versions/v144/manifest.json')==m['parent_manifest_sha256']
 assert sha(B/'versions/v143/manifest.json')==m['display_parent_manifest_sha256']
 print(json.dumps({'passed':True,'version':'v145','source_pairs':len(m['source_files']),'display_only':True}))
def freeze():
 assert not (H/'manifest.json').exists();p=json.loads((B/'versions/v144/manifest.json').read_text());files=dict(p['source_files']);locations=dict(p['snapshot_locations']);q=json.loads((H/'quality.json').read_text());assert q['passed'] and q['display_accepted']
 for path in H.iterdir():
  if path.is_file() and (path.suffix in ['.py','.md'] or path.name=='source_identity.json'):
   n=str(path.relative_to(R));e=sha(path);s=H/'source'/n;s.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,s);files[n]=e;locations[n]=str(s.relative_to(R))
 m={'version':'v145','parent':'v144','display_parent':'v143','physical_source':'v144','parent_manifest_sha256':sha(B/'versions/v144/manifest.json'),'display_parent_manifest_sha256':sha(B/'versions/v143/manifest.json'),'status':'frozen_display_validated_navigation_source_v139_unchanged','platform':'gpu5070ti Linux EGL replay, CPU model construction, no physics steps','source_files':files,'snapshot_locations':locations,'quality_sha256':sha(H/'quality.json')}
 (H/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');verify()
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=['freeze','verify']);args=a.parse_args();(freeze if args.action=='freeze' else verify)()
