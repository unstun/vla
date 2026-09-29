"""Remove an unused legacy initializer before the existing mandatory AStar seed."""
from datetime import datetime, timezone
from pathlib import Path
import difflib, hashlib, json, shutil
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
PARENT=BASE/'runtime/scan50_heading_v12'
TARGET=BASE/'runtime/scan51_seed_init_v13'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parent=json.loads((HERE.parent/'v12/manifest.json').read_text())
    if TARGET.exists() or (HERE/'manifest.json').exists():raise FileExistsError('v13 already exists')
    for name,digest in parent['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Parent changed: '+name)
    for manifest in ['source_sha256.json','install_sha256.json']:
        for name,digest in json.loads((PARENT/manifest).read_text()).items():
            if sha(PARENT/name)!=digest:raise ValueError('Native parent changed: '+name)
    TARGET.mkdir();shutil.copytree(PARENT/'src',TARGET/'src')
    relative=Path('src/plan_manage/src/planner_manager.cpp');p=TARGET/relative;before=p.read_bytes()
    first=b'    static bool flag_first_call = true, flag_force_polynomial = false;'
    last=b'    // A stair seed must come from the same current collision model as its'
    if before.count(first)!=1 or before.count(last)!=1:raise ValueError('Pinned initialization anchors changed')
    start,end=before.index(first),before.index(last)
    after=before[:start]+b'    // Native graph initialization below owns the points, interval and PVA.\n    // Do not evaluate a discarded legacy seed from an expired local curve.\n\n'+before[end:]
    p.write_bytes(after)
    native={str(p.relative_to(TARGET)):sha(p) for p in sorted((TARGET/'src').rglob('*')) if p.is_file()}
    (TARGET/'source_sha256.json').write_text(json.dumps(native,indent=2)+'\n')
    (HERE/'changes.patch').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='v12/'+str(relative),tofile='v13/'+str(relative))))
    for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(HERE.parent/'v12'/name,HERE/name)
    selected={ROOT/name for name in parent['source_files']};selected.update(p for p in (TARGET/'src').rglob('*') if p.is_file());selected.add(TARGET/'source_sha256.json');selected.update(p for p in HERE.iterdir() if p.is_file())
    records={}
    for p in sorted(selected):
        name=str(p.relative_to(ROOT));records[name]=sha(p);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (HERE/'manifest.json').write_text(json.dumps({'version':'v13','parent':'v12','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Remove discarded legacy seed initialization; retain mandatory native AStar/PVA/optimizer pipeline','source_files':records,'changed_files':[str((TARGET/relative).relative_to(ROOT))],'native_build':str(TARGET.relative_to(ROOT)),'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
    for folder in ['build','install']:shutil.copytree(PARENT/folder,TARGET/folder)
    print(json.dumps({'version':'v13','source_files':len(records),'removed_bytes':len(before)-len(after)}))
if __name__=='__main__':main()
