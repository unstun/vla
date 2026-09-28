from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
parent=load(H.parent/'v27/manifest.json');prepared=load(H/'prepared.json');N=R/prepared['native_build']
assert not (H/'manifest.json').exists()
assert load(B/'runs/v28_native_regression01/review.json')['component_scope_passed']
assert load(B/'runs/v28_native_regression01/independent_review.json')['passed']
red=load(H/'constraint_red_v27/case_results.json');green=load(H/'constraint_green_v28/case_results.json')
assert len(red)==len(green)==13 and sum(v['exit_code']!=0 for v in red.values())==10 and all(v['exit_code']==0 for v in green.values())
seed=load(B/'runs/v28_seed_replay01/stack.json');assert seed['exit_code']==0 and not seed['frames'] and not seed['assertion']
changed=set(prepared['changed_files'])
for name,digest in parent['source_files'].items():
 if name not in changed:assert sha(R/name)==digest,name
for name,digest in load(N/'source_sha256.json').items():assert sha(N/name)==digest,name
assert load(N/'build_result.json')['passed']
shutil.copyfile(N/'build_result.json',H/'build_result.json')
shutil.copyfile(N/'install_sha256.json',H/'install_sha256.json')
selected={R/name for name in parent['source_files']}|{R/name for name in changed}
selected.update(p for p in (N/'src').rglob('*') if p.is_file());selected.add(N/'source_sha256.json')
# Version files, excluding the constraint harness's CMake build trees.
selected.update(p for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'build' not in p.relative_to(H).parts[1:2])
P2B=B.parent/'2026-09-16_pi_cortex_harnessvln/p2b_execution'
for name in ('reactive_stair/materialize_scan_27.py','reactive_stair/materialize_scan_20.py','builds/scan_27/rebound_validity_manifest.json',
             'builds/scan_26/src/bspline_opt/src/bspline_optimizer.cpp','builds/scan_27/src/bspline_opt/src/bspline_optimizer.cpp',
             'builds/scan_27/src/bspline_opt/include/bspline_opt/rebound_constraint_utils.h'):
 selected.add(P2B/name)
A=B/'audits/2026-09-27_v27_optimizer_crash'
selected.update({A/'RESULT.md',A/'attempt04_stack/stack.json',A/'attempt04_stack/stack.txt',A/'attempt05_trace/make_trace_source.py',
                 A/'attempt05_trace/diagnostic_source.json',A/'attempt05_trace/stack.json'})
records={}
for p in sorted(selected):
 name=str(p.relative_to(R));records[name]=sha(p);dest=H/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
(H/'manifest.json').write_text(json.dumps({'version':'v28','parent':'v27','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Restore scan_27 finite paired rebound-constraint handling in the native optimizer; search, costs, thresholds and all final curve gates retained','source_files':records,'changed_files':sorted(changed),'native_build':prepared['native_build'],'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md','freeze_boundary':'Native source manifest captured before build. Complete snapshot after build, red/green, saved-input replay, native regression and independent review, before any physical episode.'},indent=2)+'\n')
print(json.dumps({'version':'v28','source_files':len(records)}))
