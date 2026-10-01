from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent=json.loads((H.parent/'v23/manifest.json').read_text());prepared=json.loads((H/'prepared.json').read_text());N=R/prepared['native_build']
assert not (H/'manifest.json').exists()
changed=set(prepared['changed_files'])
for name,digest in parent['source_files'].items():
 if name not in changed:assert sha(R/name)==digest,name
for name,digest in json.loads((N/'source_sha256.json').read_text()).items():assert sha(N/name)==digest,name
assert json.loads((N/'build_result.json').read_text())['passed']
shutil.copyfile(N/'build_result.json',H/'build_result.json')
shutil.copyfile(N/'install_sha256.json',H/'install_sha256.json')
selected={R/name for name in parent['source_files']}|{R/name for name in changed}
selected.update(p for p in (N/'src').rglob('*') if p.is_file());selected.add(N/'source_sha256.json')
selected.update(p for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
selected.update(p for p in (R/'references/upstream/2026-09-27_eth_footprint_support').rglob('*') if p.is_file())
records={}
for p in sorted(selected):
 name=str(p.relative_to(R));records[name]=sha(p);dest=H/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
(H/'manifest.json').write_text(json.dumps({'version':'v24','parent':'v23','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Separate body-reference height from associated footprint terrain support; preserve raw geometry and all thresholds','source_files':records,'changed_files':sorted(changed),'native_build':prepared['native_build'],'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md','freeze_boundary':'Native source manifest captured before build. Complete snapshot after source review and build, during component smoke, before any physical episode.'},indent=2)+'\n')
print(json.dumps({'version':'v24','source_files':len(records)}))
