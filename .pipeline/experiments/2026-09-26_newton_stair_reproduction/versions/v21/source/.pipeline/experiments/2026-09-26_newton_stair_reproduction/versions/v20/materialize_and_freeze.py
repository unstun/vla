from pathlib import Path
from datetime import datetime,timezone
import difflib,hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent=json.loads((H.parent/'v19/manifest.json').read_text())
assert not (H/'manifest.json').exists()
for name,digest in parent['source_files'].items():
 assert sha(R/name)==digest, name
p=B/'scripts/render_episode.py';before=p.read_text();q=H/'parent_source/scripts/render_episode.py';q.parent.mkdir(parents=True);q.write_text(before)
s=before.replace('position = base_position - 2. * forward + .9 * right + np.array([0., 0., 1.1])','position = base_position - 2. * forward + .1 * right + np.array([0., 0., 1.1])').replace('if args.view == "rear-right":','if args.view == "rear-right" and not full_building:')
assert s!=before and s.count('position = base_position - 2. * forward + .1 * right')==1
p.write_text(s)
(H/'changes.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='v19/scripts/render_episode.py',tofile='v20/scripts/render_episode.py')))
for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(H.parent/'v19'/name,H/name)
selected={R/name for name in parent['source_files']};selected.add(p);selected.add(q);selected.update(x for x in H.iterdir() if x.is_file());records={}
for x in sorted(selected):
 name=str(x.relative_to(R));records[name]=sha(x);dest=H/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,dest)
(H/'manifest.json').write_text(json.dumps({'version':'v20','parent':'v19','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Keep recorded Building camera in the stair corridor; exclude standalone origin override','source_files':records,'changed_files':[str(p.relative_to(R))],'native_build':parent['native_build'],'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
print(json.dumps({'version':'v20','source_files':len(records)}))
