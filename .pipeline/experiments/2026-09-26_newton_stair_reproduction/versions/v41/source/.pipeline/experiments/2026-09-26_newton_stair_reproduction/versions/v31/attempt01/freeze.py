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
assert load(B / 'runs/v31_saved_states01/review.json')['component_scope_passed']
assert load(B / 'runs/v31_native_regression01/review.json')['component_scope_passed']
# The timing control: the same suite rerun with no other container on the Docker VM.
assert load(B / 'runs/v31_native_regression02/review.json')['component_scope_passed']
assert load(H / 'independent_review.json')['passed']
changed = set(prepared['changed_files'])
for name, digest in parent['source_files'].items():
    if name not in changed:
        assert sha(R / name) == digest, name
for name, digest in load(N / 'source_sha256.json').items():
    assert sha(N / name) == digest, name
assert load(N / 'build_result.json')['passed']
shutil.copyfile(N / 'build_result.json', H / 'build_result.json')
shutil.copyfile(N / 'install_sha256.json', H / 'install_sha256.json')
selected = {R / name for name in parent['source_files']} | {R / name for name in changed}
selected.update(p for p in (N / 'src').rglob('*') if p.is_file())
selected.add(N / 'source_sha256.json')
# Version files, excluding the contract's CMake build trees and its local-only pending inputs.
selected.update(p for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and
                'probe_build' not in p.relative_to(H).parts and 'pending' not in p.relative_to(H).parts[:2] and
                'source' != p.relative_to(H).parts[0])
selected.add(H / 'input_refresh_contract/pending/pending_manifest.json')
A = B / 'audits/2026-09-28_v30_stop_classes'
selected.update({A / 'RESULT.md', A / 'timeline.json', A / 'scan_age_bounds.json', A / 'summary.json'})
records = {}
for p in sorted(selected):
    name = str(p.relative_to(R))
    records[name] = sha(p)
    dest = H / 'source' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
(H / 'manifest.json').write_text(json.dumps({
    'version': 'v31', 'parent': 'v30', 'status': 'frozen_unvalidated', 'frozen_utc': datetime.now(timezone.utc).isoformat(),
    'change': 'GridMap::refreshSensorInputs takes pending sensor_pose, cloud and body_pose messages from their subscriptions '
              'and applies them in stamp order through the unchanged callbacks, at the start of the planning and safety '
              'timers, before the route walk, at the start of each replan attempt and rebound round, and before the final '
              'full-curve check; single-threaded executor, input-age gates, QoS and all planner gates retained',
    'source_files': records, 'changed_files': sorted(changed), 'native_build': prepared['native_build'],
    'source_snapshot_prefix': 'source/', 'acceptance_plan': 'PLAN.md',
    'freeze_boundary': 'Native source manifest captured before build. Complete snapshot after build, red/green input-refresh '
                       'contract, saved-state replays, native regression (with its timing control) and independent review, '
                       'before any physical episode.'},
    indent=2) + '\n')
print(json.dumps({'version': 'v31', 'source_files': len(records)}))
