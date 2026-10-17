from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil

H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
parent = load(H.parent / 'v30/manifest.json')
prepared = load(H / 'prepared.json')
N = R / prepared['native_build']
assert not (H / 'manifest.json').exists()
assert load(H / 'input_refresh_contract/summary.json')['passed']
assert load(B / 'runs/v31_saved_states02/review.json')['component_scope_passed']
assert load(B / 'runs/v31_native_regression03/review.json')['component_scope_passed']
# The paired A* wall-time control, run on the first candidate: every run exits 0 and v31 reproduces v30's
# outputs in every repetition. dyn_a_star.cpp and libpath_searching.a are unchanged in scan64.
control = load(B / 'runs/v31_regression_timing_control01/summary.json')
assert control['all_exit_zero'] and all(entry['equal'] == entry['runs'] for entry in control['by_build']['v31'].values())
assert load(H / 'independent_review.json')['passed']
changed = set(prepared['changed_files'])
for name, digest in parent['source_files'].items():
    if name not in changed:
        assert sha(R / name) == digest, name
for name, digest in load(N / 'source_sha256.json').items():
    assert sha(N / name) == digest, name
# Byte-exact record: parent_source/ holds v30's bytes of every edited file.
native_parent = load(R / prepared['native_parent'] / 'source_sha256.json')
preimages = [p for p in (H / 'parent_source').rglob('*') if p.is_file()]
assert len(preimages) == 5
for p in preimages:
    assert sha(p) == native_parent[str(p.relative_to(H / 'parent_source'))], p
assert load(N / 'build_result.json')['passed']
shutil.copyfile(N / 'build_result.json', H / 'build_result.json')
shutil.copyfile(N / 'install_sha256.json', H / 'install_sha256.json')
selected = {R / name for name in parent['source_files']} | {R / name for name in changed}
selected.update(p for p in (N / 'src').rglob('*') if p.is_file())
selected.add(N / 'source_sha256.json')
# Version files, excluding CMake build trees (both contracts) and the local-only pending inputs.
for p in H.rglob('*'):
    parts = p.relative_to(H).parts
    if p.is_file() and '__pycache__' not in parts and 'probe_build' not in parts and parts[0] != 'source' and \
            parts[:2] != ('input_refresh_contract', 'pending'):
        selected.add(p)
selected.add(H / 'input_refresh_contract/pending/pending_manifest.json')
# The stop diagnosis the contract judges against, and the probe source it derives from.
A = B / 'audits/2026-09-28_v30_stop_classes'
selected.update({A / 'RESULT.md', A / 'timeline.json', A / 'scan_age_bounds.json', A / 'summary.json',
                 A / 'LOCAL_ONLY_BYTES.json', B / 'audits/2026-09-27_dense_static_sampling/raw_ground.f32'})
for state in ('stairs_replan', 'stairs_hold', 'corridor_entry_replan', 'upper_corridor_hold'):
    selected.update({A / state / 'result.json', A / state / 'result_fresh_pose.json'})
selected.update(p for p in (A / 'probe_source').rglob('*') if p.is_file())
T = B / 'runs/v31_regression_timing_control01'
selected.update({T / 'summary.json', T / 'execution.json', T / 'analyze.py', T / 'execute.py', T / 'inside.sh'})
# Steps 3 and 4: every file of the two runs except their CMake build trees (outputs, logs, reviews,
# explanations, requests, scripts and the alone checks).
for run in ('v31_saved_states02', 'v31_native_regression03'):
    selected.update(p for p in (B / 'runs' / run).rglob('*') if p.is_file() and not
                    {'probe_build', 'breakdown_build', '__pycache__'} & set(p.relative_to(B / 'runs' / run).parts))
records = {}
for p in sorted(selected):
    name = str(p.relative_to(R))
    records[name] = sha(p)
    dest = H / 'source' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
(H / 'manifest.json').write_text(json.dumps({
    'version': 'v31', 'parent': 'v30', 'status': 'frozen_unvalidated', 'frozen_utc': datetime.now(timezone.utc).isoformat(),
    'change': 'GridMap::refreshSensorInputs takes pending cloud, sensor_pose and body_pose messages from their '
              'subscriptions and applies them in stamp order through the unchanged callbacks; the FSM applies its own '
              'pending body_pose messages at its two timers. Sites: the start of the planning and safety timers, of '
              'the global-target check, of each replan attempt and rebound round, and the final full-curve check. '
              'Single-threaded executor, input-age gates, QoS and all planner gates retained. Second candidate '
              '(scan64), materialized byte-exactly; the first (scan63) is kept in attempt01/',
    'decisions': 'Option 1 (Dr Sun, 2026-09-28); the narrower take-and-apply means kept by Dr Sun after the first '
                 'independent review, with bounded planning left to a later version (PLAN.md)',
    'source_files': records, 'changed_files': sorted(changed), 'native_build': prepared['native_build'],
    'source_snapshot_prefix': 'source/', 'acceptance_plan': 'PLAN.md',
    'freeze_boundary': 'Native source manifest captured before build. Complete snapshot after build, red/green '
                       'input-refresh contract, saved-state replays, native regression (judged with the paired A* '
                       'timing control) and independent re-review, before any physical episode.'},
    indent=2) + '\n')
print(json.dumps({'version': 'v31', 'source_files': len(records)}))
