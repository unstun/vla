"""Correct the frozen v16 accessor placement without altering its snapshot."""
from datetime import datetime, timezone
from pathlib import Path
import difflib,hashlib,json,shutil
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1];ROOT=BASE.parents[2]
PARENT=BASE/'runtime/scan53_height_retry_v16'
CACHE=BASE/'runtime/scan52_riser_ground_v15'
TARGET=BASE/'runtime/scan54_height_retry_v17'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parent=json.loads((HERE.parent/'v16/manifest.json').read_text())
    if TARGET.exists() or (HERE/'manifest.json').exists():raise FileExistsError('v17 is frozen')
    for name,digest in parent['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Parent changed: '+name)
    for name,digest in json.loads((PARENT/'source_sha256.json').read_text()).items():
        if sha(PARENT/name)!=digest:raise ValueError('Native source changed: '+name)
    for name,digest in json.loads((CACHE/'install_sha256.json').read_text()).items():
        if sha(CACHE/name)!=digest:raise ValueError('Native cache changed: '+name)
    TARGET.mkdir();shutil.copytree(PARENT/'src',TARGET/'src')
    rel=Path('src/bspline_opt/include/bspline_opt/bspline_optimizer.h');p=TARGET/rel
    before=p.read_text();accessors='    bool optimizesHeight() const { return optimize_height_; }\n    void setOptimizeHeight(bool enabled) { optimize_height_ = enabled; }\n'
    assert before.count(accessors)==1
    after=before.replace(accessors,'')
    anchor='  class BsplineOptimizer\n  {\n\n  public:\n';assert after.count(anchor)==1
    after=after.replace(anchor,anchor+accessors);p.write_text(after)
    (HERE/'changes.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v16/'+str(rel),tofile='v17/'+str(rel))))
    native={str(p.relative_to(TARGET)):sha(p) for p in sorted((TARGET/'src').rglob('*')) if p.is_file()}
    (TARGET/'source_sha256.json').write_text(json.dumps(native,indent=2)+'\n')
    for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(HERE.parent/'v16'/name,HERE/name)
    selected={ROOT/name for name in parent['source_files']};selected.update(p for p in (TARGET/'src').rglob('*') if p.is_file());selected.add(TARGET/'source_sha256.json');selected.update(p for p in HERE.iterdir() if p.is_file())
    records={}
    for p in sorted(selected):
        name=str(p.relative_to(ROOT));records[name]=sha(p);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (HERE/'manifest.json').write_text(json.dumps({'version':'v17','parent':'v16','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Move height-mode accessors to BsplineOptimizer after v16 compilation rejection','source_files':records,'changed_files':[str((TARGET/rel).relative_to(ROOT))],'native_build':str(TARGET.relative_to(ROOT)),'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
    for folder in ['build','install']:shutil.copytree(CACHE/folder,TARGET/folder)
    print(json.dumps({'version':'v17','source_files':len(records)}))
if __name__=='__main__':main()
