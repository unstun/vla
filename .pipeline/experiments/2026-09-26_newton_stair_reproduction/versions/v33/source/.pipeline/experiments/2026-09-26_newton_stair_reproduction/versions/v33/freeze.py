"""Freeze v33 after K1-K6 (PLAN.md), before any v33 physics."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil

H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
parent = load(H.parent / 'v32/manifest.json')
prepared = load(H / 'prepared.json')
N = R / prepared['native_build']
assert not (H / 'manifest.json').exists()
assert load(H / 'check_change.json')['passed']                                           # K1, K2
assert load(H / 'record_check.json')['passed']                                           # K1b (review round 1, B1)
assert load(H / 'gate_contract_mac.json')['all_passed']                                  # K3 (Python 3.12)
assert load(H / 'gate_contract_container.json')['all_passed']                            # K3 (pinned image, 3.10)
assert load(H / 'replay_gate.json')['summary']['passed']                                 # K4
assert load(H / 'ros_smoke_trial_attempt03.json')['all_passed']                          # K5, the trial path
assert load(H / 'independent_review.json')['passed']                                     # K6: the rounds' summary
changed = set(prepared['changed_files'])
for name, digest in parent['source_files'].items():
    if name not in changed:
        assert sha(R / name) == digest, name
for name, digest in prepared['after_sha256'].items():
    assert sha(R / name) == digest, name
for name, digest in load(N / 'source_sha256.json').items():
    assert sha(N / name) == digest, name
assert load(N / 'build_result.json')['passed']
preimages = {str(p.relative_to(H / 'parent_source')): sha(p) for p in (H / 'parent_source').rglob('*') if p.is_file()}
assert preimages == {str((R / name).relative_to(B)): digest for name, digest in prepared['before_sha256'].items()}
shutil.copyfile(N / 'build_result.json', H / 'build_result.json')
shutil.copyfile(N / 'install_sha256.json', H / 'install_sha256.json')
# Parent files, the changed files, the imported provenance the materialization checked, the archived configuration
# the trial loads (review round 2, N9: bridge, controller and backend settings, never pinned before), and this
# version's files (without the snapshot itself).
selected = {R / name for name in parent['source_files']} | {R / name for name in changed} | {B / 'setup/runtime_sources.json'}
selected |= {p for p in (B / 'config_archived').iterdir() if p.is_file()}
for p in H.rglob('*'):
    parts = p.relative_to(H).parts
    if p.is_file() and '__pycache__' not in parts and parts[0] != 'source':
        selected.add(p)
records = {}
for p in sorted(selected):
    name = str(p.relative_to(R))
    records[name] = sha(p)
    dest = H / 'source' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
(H / 'manifest.json').write_text(json.dumps({
    'version': 'v33', 'parent': 'v32', 'status': 'frozen_unvalidated', 'frozen_utc': datetime.now(timezone.utc).isoformat(),
    'change': 'In the simulator, the backend judges body-pose freshness by simulation time: the newest pose is stale '
              'when its simulation-time age against /clock exceeds odom_stale_s (0.25 s) or its wall-time age exceeds '
              'a 2.0 s backstop for a stopped simulator or a stalled pose path (/clock travels with the poses); in '
              'this integration the unchanged applied-evidence check (2.0 s, evaluated first) catches a stopped '
              'simulator before the backstop, so the backstop\'s unique role is a stalled pose path while physics '
              'runs; a missing stamp or clock fails closed. GateConfig gains odom_time_base (default "wall", unchanged '
              'behaviour) and odom_wall_backstop_s (at least odom_stale_s under the simulation base only); '
              'MeasuredState gains stamp_s; CommandGate gains sim_clock and measurement_stale(); the ROS port '
              "subscribes to /clock with the bridge's QoS under the simulation base only; scripts/native_graph.py "
              'sets the simulation base for the simulator; setup/runtime_sources.json records the three runtime '
              "files' new hashes, as v11, v14 and v26 did. No other gate, threshold, native build, planner, bridge or "
              'worker change.',
    'decisions': 'Dr Sun, 2026-09-29: after the v32 trials, the simulation-time pose gate first (v33, simulator only; '
                 'the real-robot wall-time gate unchanged), then the corridor-entry wrong-height cell (v34); trials '
                 "with the other session's machine-dog git load paused; wall-time backstop 2.0 s. After independent "
                 'review round 1: the 2.0 s backstop kept although it is also the only catch for a stalled pose path '
                 'while physics runs; the case documented and flagged in the trial analysis. The heartbeat gate '
                 '(0.20 s wall) is not changed.',
    'source_files': records, 'changed_files': sorted(changed), 'native_build': prepared['native_build'],
    'newly_pinned': sorted(str(p.relative_to(R)) for p in (B / 'config_archived').iterdir() if p.is_file()),
    'source_snapshot_prefix': 'source/', 'acceptance_plan': 'PLAN.md',
    'freeze_boundary': 'After K1 byte-exact edits (source files and the import record), K1b the trial launcher\'s '
                       'record check, K2 scope, K3 gate contract (Mac and pinned image), K4 counterfactual replay of '
                       '48 runs, K5 ROS smoke on the trial path in the pinned image and K6 independent review '
                       '(independent_review.json: round 1 failed; rounds 2-4 passed with non-blocking findings; '
                       'confirmation rounds 3 and 4 reviewed the fixes of rounds 2 and 3; round 4\'s two findings '
                       'were wording only, applied after it and listed there as post_review_edits); before any v33 '
                       'physics (one trial, v33_historical_full01).'},
    indent=2) + '\n')
print(json.dumps({'version': 'v33', 'source_files': len(records)}))
