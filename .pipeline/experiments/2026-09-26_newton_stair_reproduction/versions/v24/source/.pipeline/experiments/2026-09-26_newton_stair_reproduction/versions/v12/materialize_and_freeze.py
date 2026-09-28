"""Use one planned segment heading at reference target admission and search."""
from datetime import datetime, timezone
from pathlib import Path
import difflib, hashlib, json, shutil
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
PARENT=BASE/'runtime/scan49_failure_notice_v11'
TARGET=BASE/'runtime/scan50_heading_v12'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parent=json.loads((HERE.parent/'v11/manifest.json').read_text())
    if TARGET.exists() or (HERE/'manifest.json').exists():raise FileExistsError('v12 already exists')
    for name,digest in parent['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Parent changed: '+name)
    for manifest in ['source_sha256.json','install_sha256.json']:
        for name,digest in json.loads((PARENT/manifest).read_text()).items():
            if sha(PARENT/name)!=digest:raise ValueError('Native parent changed: '+name)
    TARGET.mkdir();shutil.copytree(PARENT/'src',TARGET/'src')
    relative=Path('src/plan_manage/src/scan_replan_fsm.cpp');p=TARGET/relative
    before=p.read_text();after=before
    for old,new in [
        ('estimateYawFromSegment(odom_pos_, candidate)','estimateYawFromSegment(start_pt_, candidate)'),
        ('estimateYawFromSegment(odom_pos_, pt)','estimateYawFromSegment(reference ? start_pt_ : odom_pos_, pt)')]:
        if after.count(old)!=1:raise ValueError('Pinned heading anchor changed')
        after=after.replace(old,new)
    p.write_text(after)
    native={str(p.relative_to(TARGET)):sha(p) for p in sorted((TARGET/'src').rglob('*')) if p.is_file()}
    (TARGET/'source_sha256.json').write_text(json.dumps(native,indent=2)+'\n')
    (HERE/'changes.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v11/'+str(relative),tofile='v12/'+str(relative))))
    for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(HERE.parent/'v11'/name,HERE/name)
    selected={ROOT/name for name in parent['source_files']};selected.update(p for p in (TARGET/'src').rglob('*') if p.is_file());selected.add(TARGET/'source_sha256.json');selected.update(p for p in HERE.iterdir() if p.is_file())
    records={}
    for p in sorted(selected):
        name=str(p.relative_to(ROOT));records[name]=sha(p);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (HERE/'manifest.json').write_text(json.dumps({'version':'v12','parent':'v11','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Use planned segment start for reference target collision heading, matching native search','source_files':records,'changed_files':[str((TARGET/relative).relative_to(ROOT))],'native_build':str(TARGET.relative_to(ROOT)),'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
    for folder in ['build','install']:shutil.copytree(PARENT/folder,TARGET/folder)
    print(json.dumps({'version':'v12','source_files':len(records)}))
if __name__=='__main__':main()
