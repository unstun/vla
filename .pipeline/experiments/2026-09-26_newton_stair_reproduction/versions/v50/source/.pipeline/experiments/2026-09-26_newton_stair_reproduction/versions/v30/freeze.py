from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
parent=load(H.parent/'v29/manifest.json');prepared=load(H/'prepared.json');N=R/prepared['native_build']
assert not (H/'manifest.json').exists()
assert load(B/'runs/v30_native_regression01/review.json')['component_scope_passed']
assert load(B/'runs/v30_native_regression01/independent_review.json')['passed']
assert load(H/'support_contract/contract_results.json')['passed']
assert load(H/'support_contract/mutation_results.json')['passed']
assert load(H/'support_contract/runtime_input_identity.json')['passed']
assert load(B/'runs/v30_saved_states01/review.json')['passed']
changed=set(prepared['changed_files'])
for name,digest in parent['source_files'].items():
 if name not in changed:assert sha(R/name)==digest,name
for name,digest in load(N/'source_sha256.json').items():assert sha(N/name)==digest,name
assert load(N/'build_result.json')['passed']
shutil.copyfile(N/'build_result.json',H/'build_result.json')
shutil.copyfile(N/'install_sha256.json',H/'install_sha256.json')
selected={R/name for name in parent['source_files']}|{R/name for name in changed}
selected.update(p for p in (N/'src').rglob('*') if p.is_file());selected.add(N/'source_sha256.json')
# Version files, excluding the contract's CMake build trees and its local-only full-map label dumps.
selected.update(p for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'build' not in p.relative_to(H).parts[:-1]
                and p.name!='map_labels.csv')
A=B/'audits/2026-09-28_v29_landing_stall'
selected.update({A/'RESULT.md',A/'support_map/validation.json',A/'support_map/evidence_fallback_estimate.json',
                 A/'landing_oracle/result.json',A/'onset_oracle/result.json',
                 B/'audits/2026-09-27_pct_precision/ground_precise.f32',B/'audits/2026-09-27_dense_static_sampling/raw_ground.f32'})
records={}
for p in sorted(selected):
 name=str(p.relative_to(R));records[name]=sha(p);dest=H/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
(H/'manifest.json').write_text(json.dumps({'version':'v30','parent':'v29','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'ETH-style step score: a present navigation neighbour without this level is a possible drop only if the pinned surface evidence also lacks an unambiguous surface within the step capability there (evidence height in pass 1, skipped in pass 2, never adds a scored cell); GridMap passes the evidence and rescores on its arrival; all planner gates retained','source_files':records,'changed_files':sorted(changed),'native_build':prepared['native_build'],'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md','freeze_boundary':'Native source manifest captured before build. Complete snapshot after build, red/green support contract, saved-state replays, native regression and independent review, before any physical episode.'},indent=2)+'\n')
print(json.dumps({'version':'v30','source_files':len(records)}))
