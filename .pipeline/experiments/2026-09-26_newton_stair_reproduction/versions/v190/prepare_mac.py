"""Bind the recorded v189_mac_full_attempt01 episode to a full causal review video."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
TASK = Path('/private/tmp/vla_stop_audit_20261012')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(4 * 1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    tag = 'v189_mac_full_attempt01'
    source = TASK / tag / 'runs' / tag
    analysis = BASE / 'versions/v189/results' / tag
    outcome = analysis / 'outcome.json'
    route = analysis / 'full_route_verification.json'
    pose_audit = analysis / 'final_pose_audit.json'
    outcome_data = json.loads(outcome.read_text())
    route_data = json.loads(route.read_text())
    pose_data = json.loads(pose_audit.read_text())
    assert outcome_data['run'] == tag
    assert outcome_data['arrived'] is False and outcome_data['full_qualification'] is False
    assert outcome_data['replacement_owners'] == 20 and outcome_data['all_replacements_have_recorded_proof'] is True
    assert route_data['passed'] is False and 'Final held body outside requested yaw tolerance' in route_data['error']
    assert pose_data['nav2_reported_arrival'] is True and pose_data['full_route_gate_passed'] is False
    proof = json.loads((source / 'initial_state.json').read_text())
    assert proof['passed'] and proof['physics_time_s'] == 0.0 and proof['physics_steps'] == 0
    assert json.loads((source / 'video_states.json').read_text())[0] == proof['frame']
    metrics = json.loads((analysis / 'metrics.json').read_text())
    assert metrics['terminal']['backend_terminal_status'] == 'FINISHED'
    assert not metrics['fallen'] and metrics['state_copyback_verified']
    root = TASK / 'video_v190'
    root.mkdir(exist_ok=False)
    (root / 'runs').mkdir()
    (root / 'cache').mkdir()
    for name in ('test_overlay.py', 'test_timeline.py'):
        subprocess.run([sys.executable, str(HERE / name)], check=True)
    inputs = [route, outcome, pose_audit, analysis / 'metrics.json', analysis / 'latency.csv']
    inputs += [source / name for name in (
        'initial_state.json', 'video_states.json', 'factory_video_states.json',
        'startup_pacing.json', 'raw_capture.zip', 'clock_samples.jsonl',
        'backend_states.jsonl', 'episode_request.json', 'inputs/stair_scenario.json')]
    identity = json.loads((HERE / 'source_identity.json').read_text())
    for name, expected in identity['files'].items():
        assert sha(HERE / name) == expected, name
    contract = {
        'physical_source_root': str(source),
        'physical_source_run': tag,
        'route_verification': str(route),
        'final_pose_audit': str(pose_audit),
        'analysis_metrics': str(analysis / 'metrics.json'),
        'latency_csv': str(analysis / 'latency.csv'),
        'parent_manifests': {v: sha(BASE / 'versions' / v / 'manifest.json') for v in ('v178', 'v189')},
        'input_files': {str(p): sha(p) for p in inputs},
        'display_source_identity_sha256': sha(HERE / 'source_identity.json'),
        'source_outcome_sha256': sha(outcome),
        'claim': ('Display only. Complete original-start v189_mac_full_attempt01 episode, all pauses and '
                  'recoveries retained. Nav2 reported arrival, but final held yaw error (0.377481 rad) '
                  'exceeded 0.25 rad so full_route_verification.passed=false is preserved. No physics steps.'),
    }
    (root / 'display_contract.json').write_text(json.dumps(contract, indent=2) + '\n')
    print(json.dumps({
        'prepared': True,
        'root': str(root),
        'source': tag,
        'inputs': len(inputs),
        'contract_sha256': sha(root / 'display_contract.json'),
    }))


if __name__ == '__main__':
    main()
