"""Freeze physical-ground/source separation while retaining obstacle guards."""
from datetime import datetime, timezone
from pathlib import Path
import difflib, hashlib, json, shutil

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
PARENT=BASE/'runtime/scan47_sparse_terrain_v8'
TARGET=BASE/'runtime/scan48_ground_evidence_v10'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Pinned anchor mismatch: '+old)
    return text.replace(old,new)

def main():
    parent=json.loads((HERE.parent/'v8/manifest.json').read_text())
    if TARGET.exists() or (HERE/'manifest.json').exists():raise FileExistsError('Candidate already exists')
    for name,digest in parent['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Parent changed: '+name)
    for manifest in ['source_sha256.json','install_sha256.json']:
        for name,digest in json.loads((PARENT/manifest).read_text()).items():
            if sha(PARENT/name)!=digest:raise ValueError('Native parent changed: '+name)
    TARGET.mkdir();shutil.copytree(PARENT/'src',TARGET/'src')
    header=Path('src/plan_env/include/plan_env/grid_map.h')
    methods=Path('src/plan_env/include/plan_env/scan_reactive_grid_methods.inc')
    p=TARGET/header;s=p.read_bytes();s=once(s,b'  reactive_stair::TerrainSnapshot reactive_terrain_;',b'  reactive_stair::TerrainSnapshot reactive_terrain_;\n  reactive_stair::TerrainSnapshot reactive_ground_; // Unscored positive ground evidence.');p.write_bytes(s)
    p=TARGET/methods;s=p.read_text()
    anchor='void GridMap::reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {'
    s=once(s,anchor,anchor+'\n  reactive_ground_ = reactive_stair::TerrainSnapshot{};')
    anchor='  if (reactive_decision_.acceptTerrain(scored.support)) {'
    s=once(s,anchor,anchor+'\n    reactive_ground_ = terrain; // Preserve source elevations independently of step scores.')
    s=once(s,'      reactive_terrain_, point.x(), point.y(), point.z(), reactive_terrain_band_m_);','      reactive_ground_, point.x(), point.y(), point.z(), reactive_terrain_band_m_);')
    p.write_text(s)
    files={str(p.relative_to(TARGET)):sha(p) for p in sorted((TARGET/'src').rglob('*')) if p.is_file()}
    (TARGET/'source_sha256.json').write_text(json.dumps(files,indent=2)+'\n')
    patch=''
    for rel in [header,methods]:patch+=''.join(difflib.unified_diff((PARENT/rel).read_text().splitlines(True),(TARGET/rel).read_text().splitlines(True),fromfile='v8/'+str(rel),tofile='v10/'+str(rel)))
    (HERE/'changes.patch').write_text(patch)
    for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(HERE.parent/'v8'/name,HERE/name)
    selected={ROOT/name for name in parent['source_files']}
    selected.update(p for p in (TARGET/'src').rglob('*') if p.is_file());selected.add(TARGET/'source_sha256.json')
    selected.update(p for p in HERE.iterdir() if p.is_file())
    records={}
    for p in sorted(selected):
        name=str(p.relative_to(ROOT));records[name]=sha(p);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (HERE/'manifest.json').write_text(json.dumps({'version':'v10','parent':'v8','superseded_rejected_configuration':'v9','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Classify measured ground from source elevations independently of traversability scores','source_files':records,'changed_files':[str((TARGET/x).relative_to(ROOT)) for x in [header,methods]],'native_build':str(TARGET.relative_to(ROOT)),'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
    for folder in ['build','install']:shutil.copytree(PARENT/folder,TARGET/folder)
    print(json.dumps({'version':'v10','source_files':len(records),'native_source_files':len(files)}))
if __name__=='__main__':main()
