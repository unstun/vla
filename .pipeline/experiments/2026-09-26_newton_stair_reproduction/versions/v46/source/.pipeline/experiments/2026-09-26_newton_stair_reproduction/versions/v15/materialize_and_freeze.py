"""Classify measured risers bounded by neighboring mapped ground elevations."""
from datetime import datetime, timezone
from pathlib import Path
import difflib, hashlib, json, shutil
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
PARENT=BASE/'runtime/scan51_seed_init_v13'
TARGET=BASE/'runtime/scan52_riser_ground_v15'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parent=json.loads((HERE.parent/'v14/manifest.json').read_text())
    if TARGET.exists() or (HERE/'manifest.json').exists():raise FileExistsError('v15 already exists')
    for name,digest in parent['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Parent changed: '+name)
    for manifest in ['source_sha256.json','install_sha256.json']:
        for name,digest in json.loads((PARENT/manifest).read_text()).items():
            if sha(PARENT/name)!=digest:raise ValueError('Native parent changed: '+name)
    TARGET.mkdir();shutil.copytree(PARENT/'src',TARGET/'src')
    relative=Path('src/plan_env/include/plan_env/raw_return_classification.h');p=TARGET/relative;before=p.read_bytes()
    after=before.replace(b'#include "reactive_collision.h"',b'#include "eth_step_score_adaptation.h"')
    anchor=b'  return false;\n}\n\ninline bool mayWaiveRawContributor'
    replacement=b'  // Ground-relative height is signed. A mapped riser lies below its upper\n  // tread and above an associated lower neighbor; it is not an object above\n  // that floor. Reuse the existing ETH layer association and step capability.\n  const StepScoreParameters parameters;\n  if (std::abs(terrain.resolution_m - parameters.expected_resolution_m) > 1e-6 ||\n      ix <= std::numeric_limits<int>::min() || ix >= std::numeric_limits<int>::max() ||\n      iy <= std::numeric_limits<int>::min() || iy >= std::numeric_limits<int>::max()) return false;\n  const int layer = nearestSurface(found->second, z_m, parameters.critical_height_m);\n  if (layer < 0) return false;\n  const double upper = found->second[layer].elevation_m;\n  if (z_m >= upper) return false; // Above-ground obstacles never use this extension.\n  double lower = upper;\n  for (int dx = -1; dx <= 1; ++dx) {\n    for (int dy = -1; dy <= 1; ++dy) {\n      if ((dx * dx + dy * dy) * terrain.resolution_m * terrain.resolution_m >\n          parameters.first_radius_m * parameters.first_radius_m) continue;\n      const auto neighbor = terrain.cells.find({static_cast<int>(ix) + dx, static_cast<int>(iy) + dy});\n      if (neighbor == terrain.cells.end()) continue;\n      const int associated = nearestSurface(neighbor->second, upper, parameters.critical_height_m);\n      if (associated >= 0) lower = std::min(lower, neighbor->second[associated].elevation_m);\n    }\n  }\n  return upper - lower < parameters.critical_height_m && z_m >= lower - band_m;\n}\n\ninline bool mayWaiveRawContributor'
    if after.count(anchor)!=1:raise ValueError('Pinned endpoint anchor changed')
    after=after.replace(anchor,replacement)
    p.write_bytes(after)
    native={str(p.relative_to(TARGET)):sha(p) for p in sorted((TARGET/'src').rglob('*')) if p.is_file()}
    (TARGET/'source_sha256.json').write_text(json.dumps(native,indent=2)+'\n')
    (HERE/'changes.patch').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='v14/'+str(relative),tofile='v15/'+str(relative))))
    for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(HERE.parent/'v14'/name,HERE/name)
    selected={ROOT/name for name in parent['source_files']};selected.update(p for p in (TARGET/'src').rglob('*') if p.is_file());selected.add(TARGET/'source_sha256.json');selected.update(p for p in HERE.iterdir() if p.is_file())
    records={}
    for p in sorted(selected):
        name=str(p.relative_to(ROOT));records[name]=sha(p);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (HERE/'manifest.json').write_text(json.dumps({'version':'v15','parent':'v14','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Classify measured risers using signed height bounded by associated mapped treads','source_files':records,'changed_files':[str((TARGET/relative).relative_to(ROOT))],'native_build':str(TARGET.relative_to(ROOT)),'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
    for folder in ['build','install']:shutil.copytree(PARENT/folder,TARGET/folder)
    print(json.dumps({'version':'v15','source_files':len(records),'added_bytes':len(after)-len(before)}))
if __name__=='__main__':main()
