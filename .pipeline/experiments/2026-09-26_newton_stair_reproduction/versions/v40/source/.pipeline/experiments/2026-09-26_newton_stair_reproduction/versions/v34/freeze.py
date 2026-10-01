"""Freeze v34 after K1-K5 (PLAN.md), before any v34 physics. Adapted from versions/v31/freeze.py and v33/freeze.py."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil

H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
parent = load(H.parent / 'v33/manifest.json')
prepared = load(H / 'prepared.json')
N = R / prepared['native_build']
A = B / 'audits/2026-09-29_corridor_entry'
assert not (H / 'manifest.json').exists()
assert load(H / 'check_build.json')['passed']                                                        # K1
assert load(H / 'fill_contract/contract_results.json')['passed']                                     # K2
for state in ('v33_stand', 'v32_stand'):                                                             # K3
    result = load(H / 'stand_replay' / state / 'result_green.json')
    assert (H / 'stand_replay' / state / 'probe_green_exit_code.txt').read_text().strip() == '0'
    assert result['live']['ok'] and result['live']['committed']['check']['status'] == 0, state
    assert result['circle_mismatches'] == result['support_mismatches'] == result['query_mismatches'] == 0, state
for run in ('v34_saved_states01', 'v34_native_regression01'):                                        # K4
    assert load(B / 'runs' / run / 'review.json')['component_scope_passed'], run
    alone = load(B / 'runs' / run / 'alone_check.json')
    assert alone['samples_with_other_containers'] == 0 and alone['execute_exit_code'] == 0, run
assert load(H / 'independent_review.json')['passed']                                                 # K5
changed = set(prepared['changed_files'])
for name, digest in parent['source_files'].items():
    if name not in changed:
        assert sha(R / name) == digest, name
for name, digest in load(N / 'source_sha256.json').items():
    assert sha(N / name) == digest, name
native_parent = load(R / prepared['native_parent'] / 'source_sha256.json')
preimages = [p for p in (H / 'parent_source').rglob('*') if p.is_file()]
assert len(preimages) == 2
for p in preimages:
    assert sha(p) == native_parent[str(p.relative_to(H / 'parent_source'))], p
assert load(N / 'build_result.json')['passed']
shutil.copyfile(N / 'build_result.json', H / 'build_result.json')
shutil.copyfile(N / 'install_sha256.json', H / 'install_sha256.json')
BUILD_TREES = {'build', 'probe_build', 'breakdown_build', '__pycache__'}
selected = {R / name for name in parent['source_files']} | {R / name for name in changed}
selected.update(p for p in (N / 'src').rglob('*') if p.is_file())
selected.add(N / 'source_sha256.json')
# Version files, without the snapshot itself and the CMake build trees of the contract and the stand replay.
for p in H.rglob('*'):
    parts = p.relative_to(H).parts
    if p.is_file() and parts[0] != 'source' and not BUILD_TREES & set(parts):
        selected.add(p)
# The diagnosis the version rests on: its tracked files (not its local-only frozen inputs, grounds or probe build).
local_only = {f['path'] for group in ('raw_artifacts', 'regenerable_caches') for entry in load(A / 'LOCAL_ONLY_BYTES.json')[group]
              for f in entry['files']}
for p in A.rglob('*'):
    if p.is_file() and str(p.relative_to(R)) not in local_only and not BUILD_TREES & set(p.relative_to(A).parts):
        selected.add(p)
# K4: every file of the two runs except their CMake build trees.
for run in ('v34_saved_states01', 'v34_native_regression01'):
    selected.update(p for p in (B / 'runs' / run).rglob('*') if p.is_file() and not BUILD_TREES & set(p.relative_to(B / 'runs' / run).parts))
# The trial's host files: the derived runner and gate check, and their derivation record.
G = B / 'hosts/2026-09-29_gpu5070ti'
selected.update({G / 'v34_trial_run.sh', G / 'make_v34_files.py', G / 'make_v34_files.json', G / 'checks/p1_gates_v34.py'})
records = {}
for p in sorted(selected):
    name = str(p.relative_to(R))
    records[name] = sha(p)
    dest = H / 'source' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
(H / 'manifest.json').write_text(json.dumps({
    'version': 'v34', 'parent': 'v33', 'status': 'frozen_unvalidated', 'frozen_utc': datetime.now(timezone.utc).isoformat(),
    'change': 'When SCAN accepts its ground inputs, its copy of PCT\'s navigation ground gains each surface-evidence layer '
              'that the navigation cell containing the evidence cell\'s centre lacks within 0.12 m (body_height_tolerance), '
              'unless an evidence cell within 0.35 m (double_cylinder_radius, square to square) of the candidate has no '
              'surface within 0.26 m (the step capability) of the layer and either no surface at all or one more than '
              '0.26 m below it (a drop). New evidence re-augments the navigation ground as decoded. On the pinned grounds '
              'it adds 17,214 layers and rejects 22,785 beside drops. The step score, support query, decision, thresholds, '
              'occupancy and planner are unchanged. Native tree runtime/scan65_evidence_floor_v34 (three files: '
              'evidence_floor_fill.h new, grid_map.h, scan_reactive_grid_methods.inc).',
    'decisions': 'Dr Sun, 2026-09-29, after the corridor-entry diagnosis (audits/2026-09-29_corridor_entry): "Floor fallback '
                 'in SCAN" (over correcting the pinned map, or the wrong-height cells only), and the single trial on '
                 'gpu5070ti as for v33. The drop guard is the author\'s stricter refinement, disclosed in PLAN.md.',
    'source_files': records, 'changed_files': sorted(changed), 'native_build': prepared['native_build'],
    'source_snapshot_prefix': 'source/', 'acceptance_plan': 'PLAN.md',
    'freeze_boundary': 'After K1 byte-exact materialization and build, K2 the red/green fill contract (cases, real map, node '
                       'orders), K3 the two frozen corridor-entry stands, K4 the saved-state and native-regression suites '
                       'with every difference explained, and K5 independent review (independent_review.json); before any '
                       'v34 physics (one trial, v34_historical_full01, on gpu5070ti).'},
    indent=2) + '\n')
print(json.dumps({'version': 'v34', 'source_files': len(records)}))
