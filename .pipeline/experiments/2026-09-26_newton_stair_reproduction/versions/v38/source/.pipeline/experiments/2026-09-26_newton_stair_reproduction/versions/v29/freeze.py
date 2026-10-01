from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
parent=load(H.parent/'v28/manifest.json');prepared=load(H/'prepared.json');N=R/prepared['native_build']
assert not (H/'manifest.json').exists()
assert load(B/'runs/v29_native_regression01/review.json')['component_scope_passed']
assert load(B/'runs/v29_native_regression01/independent_review.json')['passed']
assert load(H/'waiver_contract/contract_results.json')['passed']
S=B/'runs/v29_start_states01';assert load(S/'execution.json')['exit_code']==0
for state in ('stopped','z_0p35490','z_0p3600','z_0p3650','z_0p3700','z_0p3800','control'):
 r=load(S/state/'result.json');assert r['continued'] and r['boundary_pass'] and r['full_clear'] and all(load(S/state/'result_negatives.json').values()),state
changed=set(prepared['changed_files'])
for name,digest in parent['source_files'].items():
 if name not in changed:assert sha(R/name)==digest,name
for name,digest in load(N/'source_sha256.json').items():assert sha(N/name)==digest,name
assert load(N/'build_result.json')['passed']
shutil.copyfile(N/'build_result.json',H/'build_result.json')
shutil.copyfile(N/'install_sha256.json',H/'install_sha256.json')
selected={R/name for name in parent['source_files']}|{R/name for name in changed}
selected.update(p for p in (N/'src').rglob('*') if p.is_file());selected.add(N/'source_sha256.json')
# Version files, excluding the contract's CMake build trees.
selected.update(p for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'build' not in p.relative_to(H).parts[:-1])
A=B/'audits/2026-09-28_v28_start_thrash'
selected.update({A/'RESULT.md',A/'optimizer_trace/voxel_dump/blind_zone.json',A/'optimizer_trace/trace_summary.json',
                 A/'column_waiver_probe/diagnostic_change.json',A/'column_waiver_probe/trace_summary.json',
                 B/'inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface_isaac.urdf'})
records={}
for p in sorted(selected):
 name=str(p.relative_to(R));records[name]=sha(p);dest=H/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
(H/'manifest.json').write_text(json.dumps({'version':'v29','parent':'v28','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Known-footprint waiver tested at the queried point with vertical extent -0.05..+0.10854 m (trunk bottom to the pinned-URDF Mid-360 scan origin); footprint circles, pose freshness, Unknown-only rule and all planner gates retained','source_files':records,'changed_files':sorted(changed),'native_build':prepared['native_build'],'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md','freeze_boundary':'Native source manifest captured before build. Complete snapshot after build, red/green waiver contract, saved start-state replays, native regression and independent review, before any physical episode.'},indent=2)+'\n')
print(json.dumps({'version':'v29','source_files':len(records)}))
