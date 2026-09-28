from pathlib import Path
from datetime import datetime,timezone
import difflib,hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parent=json.loads((HERE.parent/'v17/manifest.json').read_text())
 if (HERE/'manifest.json').exists():raise FileExistsError('v18 frozen')
 for name,digest in parent['source_files'].items():
  if sha(ROOT/name)!=digest:raise ValueError('Parent source changed: '+name)
 path=BASE/'scripts/clock_sync.py';candidate=BASE/'audits/2026-09-27_clock_cache/clock_candidate.py'
 before=path.read_bytes();after=candidate.read_bytes()
 preimage=HERE/'parent_source/scripts/clock_sync.py';preimage.parent.mkdir(parents=True);preimage.write_bytes(before)
 path.write_bytes(after)
 (HERE/'changes.patch').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='v17/scripts/clock_sync.py',tofile='v18/scripts/clock_sync.py')))
 for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(HERE.parent/'v17'/name,HERE/name)
 trace=BASE/'runs/v17_building_route01/clock_samples.jsonl'
 (HERE/'recorded_input.json').write_text(json.dumps({'path':str(trace.relative_to(ROOT)),'sha256':sha(trace),'regeneration':'Version v17 production Building run; test uses its uninterrupted connection prefix'},indent=2)+'\n')
 selected={ROOT/name for name in parent['source_files']};selected.add(preimage);selected.update(p for p in HERE.iterdir() if p.is_file());records={}
 for p in sorted(selected):
  name=str(p.relative_to(ROOT));records[name]=sha(p);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 (HERE/'manifest.json').write_text(json.dumps({'version':'v18','parent':'v17','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Retain unexpired converged estimate on ordinary clock-sample rejection; invalidate on reset/transport failure','source_files':records,'changed_files':[str(path.relative_to(ROOT))],'native_build':parent['native_build'],'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
 print(json.dumps({'version':'v18','source_files':len(records)}))
if __name__=='__main__':main()
