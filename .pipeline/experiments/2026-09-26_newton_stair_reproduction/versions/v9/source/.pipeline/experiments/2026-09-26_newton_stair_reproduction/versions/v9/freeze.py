"""Freeze the single Building envelope parameter on v8."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, difflib

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if (HERE/'manifest.json').exists(): raise FileExistsError('v9 already frozen')
    parent=json.loads((HERE.parent/'v8/manifest.json').read_text())
    for name,expected in parent['source_files'].items():
        if sha(ROOT/name)!=expected: raise ValueError('Parent source changed: '+name)
    before=(HERE.parent/'v8/building_planner.yaml').read_text()
    anchor='grid_map.obstacles_inflation_z_up: 0.55'
    if before.count(anchor)!=1: raise ValueError('Envelope anchor mismatch')
    after=before.replace(anchor,'grid_map.obstacles_inflation_z_up: 0.1')
    (HERE/'building_planner.yaml').write_text(after)
    shutil.copyfile(HERE.parent/'v8/flat_planner.yaml',HERE/'flat_planner.yaml')
    (HERE/'changes.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v8/building_planner.yaml',tofile='v9/building_planner.yaml')))
    selected={ROOT/name for name in parent['source_files']}
    selected.update(p for p in HERE.iterdir() if p.is_file())
    records={}
    for p in sorted(selected):
        name=str(p.relative_to(ROOT)); records[name]=sha(p)
        dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (HERE/'manifest.json').write_text(json.dumps({'version':'v9','parent':'v8','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Restore Building positive obstacle Z inflation from 0.55 to historical 0.10 m; other geometry and guards unchanged','source_files':records,'changed_files':[str((HERE/'building_planner.yaml').relative_to(ROOT))],'native_build':parent['native_build'],'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
    print(json.dumps({'version':'v9','source_files':len(records)}))
if __name__=='__main__':main()
